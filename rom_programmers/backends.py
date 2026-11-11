"""Subprocess adapters. Never select a native T48 RF2 read algorithm."""
from pathlib import Path
import re


class T48:
    def __init__(self, config, profile, session):
        self.config, self.profile, self.session = config, profile, session

    def command(self):
        return [self.config['rf2'], '--serial', self.config['serial']]

    def read(self, name):
        out = self.session.path / (name + '.bin')
        log = self.session.run(name, self.command() + [self.profile.get('read_command') or 'read', out], outputs=[out])
        if 'Reset pin drivers: OK' not in log.read_text(errors='replace'):
            raise RuntimeError('T48 read lacks a successful pin-driver reset report')
        self.session.record['shutdown'] = 'reported-off'
        return out

    def program(self, image):
        out = self.session.path / 'writer-readback.bin'
        log = self.session.run('program', self.command() + ['write', image, out, '2048'], writing=True, outputs=[out])
        text = log.read_text(errors='replace')
        if not re.search(r'Reset pin drivers: OK; changed=\d+ remaining=0', text):
            raise RuntimeError('T48 writer did not report full completion and reset')
        self.session.record['shutdown'] = 'reported-off'
        return out


class Willem:
    def __init__(self, config, profile, session):
        self.config, self.profile, self.session = config, profile, session
        if str(config.get('lpt', '378')).lower() != '378':
            raise ValueError('The qualified 2732 writer is fixed to LPT 378h')

    def run(self, name, execution, uploads, downloads=(), writing=False):
        folder = self.session.path / name
        args = self.config['dosravi'] + [
            '--serial', self.config['port'], '--baud', str(self.config.get('baud', 57600)),
            '--timeout', '20', '--retries', '2', '--exec-timeout', str(self.config.get('exec_timeout', 1800)),
            '--session-dir', str(folder), 'run', '--exec', execution,
            '--note', 'machine=Pocket8086', '--note', 'cable-adapter=CP2102; Willem PCB5.0E LPT']
        for local, remote in uploads:
            args += ['--put', f'{local}:{remote}']
        for remote in downloads:
            args += ['--get', remote]
        self.session.run(name, args, cwd=self.config.get('cwd'), recoverable=True, writing=writing,
                         outputs=[folder / 'STDOUT.TXT', *(folder / x for x in downloads)])
        text = (folder / 'STDOUT.TXT').read_text(errors='replace')
        marker = 'SAFE OFF: VPP off, VCC off' if writing else 'Safe shutdown complete: VCC off, VPP off'
        if marker not in text:
            raise RuntimeError(f'{name}: current execution lacks a shutdown marker')
        self.session.record['shutdown'] = 'reported-off'
        return folder, text

    def read(self, name):
        filename = 'READ.BIN'
        command = f'READER.COM {self.profile["read_command"]} {filename} 378 /PROFILE:conservative'
        folder, _ = self.run(name, command, [(self.config['reader'], 'READER.COM')], [filename])
        return folder / filename

    def program(self, image):
        gate = self.session.path / '2732A.OK'
        gate.write_bytes(b'D2732A-5V-21V-50MS\n')
        _, text = self.run('program', 'WRITER.COM IMAGE.BIN /WRITE21',
                           [(self.config['writer'], 'WRITER.COM'), (image, 'IMAGE.BIN'), (gate, '2732A.OK')],
                           writing=True)
        if 'WRITE PASSED: all 4096 bytes verified after power cycle' not in text:
            raise RuntimeError('Willem did not report full power-cycle verification')
        return None


def backend(config, profile, session):
    return {'t48': T48, 'willem': Willem}[profile['backend']](config, profile, session)
