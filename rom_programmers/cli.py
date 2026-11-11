"""One command surface, explicit profiles, durable independent verification."""
import argparse
import hashlib
from datetime import datetime, timezone
import importlib.resources
import json
from pathlib import Path
import shutil
import sys
import uuid

from . import __version__
from .backends import backend
from .session import BenchLock, Session, atomic_json, digest


def profiles():
    return json.loads(importlib.resources.files('rom_programmers').joinpath('profiles.json').read_text())


def load_config(path, kind):
    path = Path(path).resolve()
    config = json.loads(path.read_text())[kind]
    for key in ('rf2', 'reader', 'writer', 'cwd'):
        if key in config:
            p = Path(config[key]).expanduser()
            config[key] = str((path.parent / p).resolve())
    if 'dosravi' in config:
        command = config['dosravi']
        if not isinstance(command, list) or not command:
            raise ValueError('dosravi must be a nonempty argument list')
        executable = command[0]
        config['dosravi'] = [str((path.parent / executable).resolve()) if '/' in executable
                             else shutil.which(executable) or executable, *command[1:]]
    return config


def tool_identity(config, kind, programming):
    names = ['rf2'] if kind == 't48' else ['reader'] + (['writer'] if programming else [])
    result = {}
    for name in names:
        path = Path(config[name])
        actual = digest(path)
        expected = config.get('sha256', {}).get(name)
        if expected and expected != actual:
            raise ValueError(f'{name} differs from the configured qualified executable hash')
        result[name] = {'path': str(path), 'sha256': actual}
    return result


def checked_read(path, size):
    data = path.read_bytes()
    if len(data) != size:
        raise RuntimeError(f'{path}: expected {size} bytes, got {len(data)}')
    return data


def operate(args):
    profile = profiles()[args.profile]
    writing = args.action == 'program'
    if writing and not profile['program']:
        raise ValueError('This profile supports reads only')
    if writing and not args.setup_confirmed:
        raise ValueError('program requires --setup-confirmed after checking the selected setup/voltages')
    config = load_config(args.config, profile['backend'])
    if writing and config.get('program_vpp') != profile['voltage']:
        raise ValueError('Bench program_vpp must match the selected profile')
    image = Path(args.image).resolve() if args.image else None
    if image:
        checked_read(image, profile['size'])
    workflow_hash = hashlib.sha256()
    package = importlib.resources.files('rom_programmers')
    for entry in sorted(package.iterdir(), key=lambda p: p.name):
        if entry.name.endswith(('.py', '.json')):
            workflow_hash.update(entry.name.encode() + b'\0' + entry.read_bytes())
    request = {'version': __version__, 'workflow_sha256': workflow_hash.hexdigest(), 'action': args.action, 'profile': args.profile,
               'profile_definition': profile, 'config': config,
               'tools': tool_identity(config, profile['backend'], writing),
               'image': {'path': str(image), 'sha256': digest(image)} if image else None,
               'setup_confirmed': args.setup_confirmed}
    # Lock the physical connection, across all profiles and session directories.
    identity = 't48:' + config['serial'] if profile['backend'] == 't48' else 'serial:' + str(Path(config['port']).resolve())
    path = args.resume or args.session or str(Path('sessions') / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8]))
    with BenchLock(identity):
        session = Session(path, request, bool(args.resume), args.same_agent_session)
        try:
            driver = backend(config, profile, session)
            # A stable session-local image is used by every programming/recovery step.
            local_image = session.path / 'image.bin'
            if image:
                if local_image.exists() and digest(local_image) != request['image']['sha256']:
                    raise RuntimeError('Recorded input image changed')
                if not local_image.exists():
                    local_image.write_bytes(image.read_bytes())
            if writing:
                before = checked_read(driver.read('before'), profile['size'])
                target = local_image.read_bytes()
                if any((old & new) != new for old, new in zip(before, target)):
                    raise RuntimeError('Existing contents require UV erasure')
                if profile['backend'] == 'willem' and any(b != 255 for b in before):
                    raise RuntimeError('Qualified Willem writer requires a fully blank chip')
                readback = driver.program(local_image)
                if readback and checked_read(readback, profile['size']) != target:
                    raise RuntimeError('Writer readback differs from target')
                session.record['write_completed'] = True
                session.save()
            one = driver.read('read-1')
            two = driver.read('read-2')
            data = checked_read(one, profile['size'])
            if data != checked_read(two, profile['size']):
                raise RuntimeError('Independent reads disagree')
            if args.action in ('verify', 'program') and data != local_image.read_bytes():
                raise RuntimeError('Independent readback differs from target')
            if args.action == 'blank-check' and any(b != 255 for b in data):
                raise RuntimeError('Chip is not blank')
            result = session.path / 'readback.bin'
            result.write_bytes(data)
            session.finish('verified', comparison='two matching fresh reads', all_ff=all(b == 255 for b in data),
                           result_sha256=digest(result), experimental=profile['experimental'])
            print(json.dumps({'status': 'verified', 'session': str(session.path), 'sha256': digest(result),
                              'all_ff': session.record['all_ff'], 'shutdown': session.record['shutdown']}, indent=2))
            return 0
        except BaseException as error:
            session.finish('interrupted' if isinstance(error, KeyboardInterrupt) else 'failed', error=str(error))
            raise


def prepare_image(args):
    source = Path(args.image).resolve()
    original = source.read_bytes()
    if args.repeat < 1:
        raise ValueError('repeat must be positive')
    data = original * args.repeat
    if args.size is not None:
        if len(data) > args.size or (len(data) < args.size and args.pad is None):
            raise ValueError('Requested size needs an explicit pad byte, or is too small')
        data += bytes([args.pad or 0]) * (args.size - len(data))
    destination = Path(args.output).resolve()
    if Path(str(destination) + '.json').exists():
        raise ValueError('Output provenance already exists')
    with destination.open('xb') as stream:
        stream.write(data)
    atomic_json(str(destination) + '.json', {'source': str(source), 'source_sha256': digest(source),
                'output_sha256': digest(destination), 'size': len(data), 'repeat': args.repeat, 'pad': args.pad})
    print(destination)
    return 0


def parser():
    p = argparse.ArgumentParser(prog='rom-programmers')
    p.add_argument('--version', action='version', version=__version__)
    sub = p.add_subparsers(dest='action', required=True)
    info = sub.add_parser('info', help='show supported profiles and setup without touching hardware')
    info.add_argument('--profile', choices=profiles())
    for action in ('read', 'blank-check', 'verify', 'program'):
        cmd = sub.add_parser(action)
        cmd.add_argument('--config', default='bench.json')
        cmd.add_argument('--profile', choices=profiles(), required=True)
        group = cmd.add_mutually_exclusive_group()
        group.add_argument('--session')
        group.add_argument('--resume', help='recover the exact recorded request; never blindly replay T48 writes')
        cmd.add_argument('--image', required=action in ('verify', 'program'))
        cmd.add_argument('--setup-confirmed', action='store_true')
        cmd.add_argument('--same-agent-session', action='store_true', help='for DOSRAVI recovery only: assert the DOS agent has not restarted')
    prep = sub.add_parser('prepare-image')
    prep.add_argument('--image', required=True)
    prep.add_argument('--output', required=True)
    prep.add_argument('--repeat', type=int, default=1)
    prep.add_argument('--size', type=int)
    prep.add_argument('--pad', type=lambda s: int(s, 16), choices=range(256), metavar='HEX_BYTE')
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        if args.action == 'info':
            print(json.dumps(profiles()[args.profile] if args.profile else profiles(), indent=2))
            return 0
        if args.action == 'prepare-image':
            return prepare_image(args)
        return operate(args)
    except KeyboardInterrupt:
        print('Interrupted; inspect the recorded session before recovery.', file=sys.stderr)
        return 130
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1
