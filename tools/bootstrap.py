#!/usr/bin/env python3
"""Fetch pinned sources, optionally build tools and generate local bench config."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def run(*args, cwd=None):
    subprocess.run(list(map(str, args)), cwd=cwd, check=True)

def output(*args, cwd=None):
    return subprocess.check_output(list(map(str, args)), cwd=cwd, text=True).strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--t48-serial')
    parser.add_argument('--dos-port')
    args = parser.parse_args()
    lock = json.loads((ROOT / 'dependencies.lock.json').read_text())
    dest = ROOT / '.tools'
    dest.mkdir(exist_ok=True)
    for name, dep in lock.items():
        path = dest / name
        if not path.exists():
            run('git', 'init', path)
            run('git', 'remote', 'add', 'origin', dep['url'], cwd=path)
        if output('git', 'remote', 'get-url', 'origin', cwd=path) != dep['url']:
            raise RuntimeError(f'{path}: unexpected origin')
        if output('git', 'status', '--porcelain', '--untracked-files=no', cwd=path):
            raise RuntimeError(f'{path}: tracked changes; refusing checkout')
        current = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=path, capture_output=True, text=True)
        if current.returncode or current.stdout.strip() != dep['revision']:
            run('git', 'fetch', '--depth=1', 'origin', dep['revision'], cwd=path)
            run('git', 'checkout', '--detach', dep['revision'], cwd=path)
    # DOSRAVI imports the pinned RAVI submodule directly even when installed.
    run('git', 'submodule', 'update', '--init', '--depth=1', 'third_party/ravi', cwd=dest / 'dosravi')
    for name, dep in lock.items():
        for relative, expected in dep.get('submodules', {}).items():
            if output('git', 'rev-parse', 'HEAD', cwd=dest / name / relative) != expected:
                raise RuntimeError(f'{name}/{relative}: unexpected submodule revision')
    if not args.build:
        return
    mini = dest / 'minipro'
    make_options = [f'SHARE_INSTDIR={mini}']
    # Optional locally extracted development headers; no sudo/system changes.
    if os.environ.get('MINIPRO_LIBUSB_INCLUDE'):
        make_options += ['libusb_CFLAGS=-I' + os.environ['MINIPRO_LIBUSB_INCLUDE'],
                         'libusb_LIBS=-l:libusb-1.0.so.0']
    run('make', '-j2', 'minipro', 'rf2-direct', 'test-bench', *make_options, cwd=mini)
    run('make', '-j2', 'dos', 'build/dos/PG2732A.COM', cwd=dest / 'willem')
    venv = dest / 'venv'
    if not (venv / 'bin/python').exists():
        run(sys.executable, '-m', 'venv', venv)
    run(venv / 'bin/python', '-m', 'pip', 'install', '-e', dest / 'dosravi')
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    config = {
        't48': {'serial': args.t48_serial or 'SET_T48_SERIAL', 'rf2': str(mini / 'rf2-direct'),
                'program_vpp': 25, 'source_revision': lock['minipro']['revision'],
                'sha256': {'rf2': sha(mini / 'rf2-direct')}},
        'willem': {'port': args.dos_port or '/dev/serial/by-id/SET_ADAPTER', 'baud': 57600, 'lpt': '378',
                   'program_vpp': 21, 'exec_timeout': 1800,
                   'dosravi': [str(venv / 'bin/python'), '-m', 'dosravi.cli'],
                   'cwd': str(dest / 'dosravi'),
                   'reader': str(dest / 'willem/build/dos/WILLEM.COM'),
                   'writer': str(dest / 'willem/build/dos/PG2732A.COM'),
                   'source_revisions': {k: v['revision'] for k, v in lock.items() if k != 'minipro'},
                   'sha256': {'reader': sha(dest / 'willem/build/dos/WILLEM.COM'),
                              'writer': sha(dest / 'willem/build/dos/PG2732A.COM')}}}
    path = ROOT / 'bench.json'
    if path.exists():
        path = ROOT / '.tools/bench.generated.json'
    path.write_text(json.dumps(config, indent=2) + '\n')
    print(f'Built tools. Bench configuration: {path}. Confirm physical settings before programming.')

if __name__ == '__main__':
    main()
