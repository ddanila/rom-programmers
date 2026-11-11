"""Durable sessions and exclusive access; no implicit write retry."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


class BenchLock:
    def __init__(self, identity):
        root = Path(os.environ.get('XDG_RUNTIME_DIR', f'/tmp/rom-programmers-{os.getuid()}'))
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = root / ('rom-programmers-' + hashlib.sha256(identity.encode()).hexdigest() + '.lock')

    def __enter__(self):
        self.stream = self.path.open('a')
        try:
            fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.stream.close()
            raise RuntimeError('Another operation owns this programmer connection') from None
        return self

    def __exit__(self, *unused):
        self.stream.close()


class Session:
    def __init__(self, path, request, resume=False, same_agent_session=False):
        self.same_agent_session = same_agent_session
        self.path = Path(path).resolve()
        if resume:
            self.record = json.loads((self.path / 'session.json').read_text())
            if self.record['request'] != request:
                raise ValueError('Resume request/configuration/tool/image differs from the recorded session')
            if self.record['status'] == 'verified':
                raise ValueError('Session already verified; use a new session for a fresh check')
        else:
            self.path.mkdir(parents=True, exist_ok=False)
            self.record = {'schema': 1, 'started_utc': datetime.now(timezone.utc).isoformat(),
                           'request': request, 'status': 'running', 'steps': [],
                           'shutdown': 'unknown', 'artifacts': {}}
            self.save()

    def save(self):
        atomic_json(self.path / 'session.json', self.record)

    def run(self, name, command, *, cwd=None, recoverable=False, writing=False, outputs=()):
        command = list(map(str, command))
        step = next((x for x in self.record['steps'] if x['name'] == name), None)
        if step:
            if step['command'] != command or step['cwd'] != str(cwd):
                raise ValueError('Recorded step command changed')
            if step['status'] == 'complete':
                for filename, expected in step.get('outputs', {}).items():
                    artifact = self.path / filename
                    if not artifact.exists() or digest(artifact) != expected:
                        raise RuntimeError('Recorded step output is missing or changed; refusing recovery')
                return self.path / step['log']
            if step['status'] == 'failed':
                raise RuntimeError('Recorded step failed; inspect it before starting a new operation')
            if writing and not recoverable:
                raise RuntimeError('Uncertain T48 write: inspect/read the chip; automatic replay is disabled')
            if writing and recoverable and not self.same_agent_session:
                raise RuntimeError('DOSRAVI cache does not survive agent restart; resume requires --same-agent-session only if the agent has not restarted')
        else:
            step = {'name': name, 'command': command, 'cwd': str(cwd),
                    'status': 'started', 'log': name + '.log'}
            self.record['steps'].append(step)
        step['status'] = 'started'
        self.record['shutdown'] = 'unknown'
        self.save()
        log = self.path / step['log']
        try:
            # No process-killing timeout: a remote EXEC may still be running.
            # DOSRAVI owns its execution timeout and persistent recovery ID.
            with log.open('ab') as output:
                result = subprocess.run(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT)
            step['outputs'] = {str(Path(p).relative_to(self.path)): digest(p)
                               for p in [log, *outputs] if Path(p).exists()}
            step['exit_code'] = result.returncode
            step['status'] = 'complete' if result.returncode == 0 else 'failed'
            if result.returncode and recoverable:
                remote_record = self.path / name / 'session.json'
                remote = json.loads(remote_record.read_text()) if remote_record.exists() else {}
                # Completed child failure is final. A transport/download failure can
                # recover through the same DOSRAVI execution ID without re-running it.
                if remote.get('exit_status') in (None, 0):
                    step['status'] = 'unknown'
            self.save()
            if result.returncode:
                raise RuntimeError(f'{name} exited {result.returncode}; see {log}')
            return log
        except (KeyboardInterrupt, OSError):
            step['status'] = 'unknown'
            self.save()
            raise

    def finish(self, status, **details):
        self.record.update(status=status, **details)
        if status == 'verified':
            self.record.pop('error', None)
        self.record['finished_utc'] = datetime.now(timezone.utc).isoformat()
        self.record['artifacts'] = {
            str(p.relative_to(self.path)): {'size': p.stat().st_size, 'sha256': digest(p)}
            for p in self.path.rglob('*') if p.is_file() and p.name not in ('session.json', 'session.json.tmp')
        }
        self.save()
