"""Bootstrap selection/configuration tests; no fetch, compiler, or hardware."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bootstrap_under_test', ROOT/'tools/bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def check_t48_only(self, existing):
        lock = json.loads((ROOT/'dependencies.lock.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'dependencies.lock.json').write_text(json.dumps(lock))
            mini = root/'.tools/minipro'
            mini.mkdir(parents=True)
            (mini/'rf2-direct').write_bytes(b'tested-rf2-tool')
            if existing:
                (root/'bench.json').write_text('preserve existing bench\n')
            def output(*args, **kwargs):
                self.assertEqual(kwargs['cwd'], mini)
                if args[:3] == ('git', 'remote', 'get-url'):
                    return lock['minipro']['url']
                if args[:2] == ('git', 'status'):
                    return ''
                self.fail(f'unexpected query: {args}')
            with patch.object(bootstrap, 'ROOT', root), patch.object(bootstrap, 'output', side_effect=output), \
                 patch.object(bootstrap, 'run') as run, \
                 patch.object(bootstrap.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout=lock['minipro']['revision']+'\n')), \
                 patch('sys.argv', ['bootstrap.py', '--build', '--backend', 't48', '--t48-serial', 'TEST']), \
                 contextlib.redirect_stdout(io.StringIO()):
                bootstrap.main()
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[:5], ('make', '-j2', 'minipro', 'rf2-direct', 'test-bench'))
            self.assertEqual(run.call_args.kwargs['cwd'], mini)
            generated = root/('.tools/bench.generated.json' if existing else 'bench.json')
            config = json.loads(generated.read_text())
            self.assertEqual(set(config), {'t48'})
            self.assertEqual(config['t48']['serial'], 'TEST')
            self.assertEqual(config['t48']['source_revision'], lock['minipro']['revision'])
            self.assertIn('rf2', config['t48']['sha256'])
            if existing:
                self.assertEqual((root/'bench.json').read_text(), 'preserve existing bench\n')

    def test_t48_build_does_not_require_willem_or_dosravi(self):
        self.check_t48_only(False)

    def test_t48_build_preserves_existing_configuration(self):
        self.check_t48_only(True)
