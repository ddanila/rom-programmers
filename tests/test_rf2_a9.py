"""Recorded hardware contracts and host-only execution of the experimental C code.

Never links USB or opens a programmer. Electrical behavior remains bench-qualified;
the model only makes the observed A9 alias injectable for regression testing.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIRST = ROOT / 'evidence/20261121-a9-software'
SECOND = ROOT / 'evidence/20261121-a9-sticker-second'
SERIAL = '6MNNWV7B0LLRDYCAA5PF5744'


def blob(path):
    data = path.read_bytes()
    if len(data) != 2048:
        raise AssertionError(f'{path}: not a complete RF2 image')
    return data


class RecordedRF2Tests(unittest.TestCase):
    def test_both_specimens_preserve_partner_and_every_other_byte(self):
        for folder in (FIRST, SECOND):
            for stage in sorted(folder.glob('independent-*')):
                with self.subTest(stage=stage):
                    record = json.loads((stage/'session.json').read_text())
                    address, value = record['request']['address'], record['request']['value']
                    before = blob(stage/'before-1.bin')
                    self.assertEqual(before, blob(stage/'before-2.bin'))
                    expected = bytearray(before)
                    self.assertEqual(expected[address], 255)
                    expected[address] = value
                    for name in ('target.bin', 'writer-readback.bin', 'after-1.bin', 'after-2.bin'):
                        self.assertEqual(expected, blob(stage/name), name)
                    self.assertEqual(record['status'], 'verified')
                    self.assertTrue(record['write_completed'])
                    self.assertEqual(record['shutdown'], 'reported-off')
                    for name, details in record['artifacts'].items():
                        self.assertEqual(hashlib.sha256((stage/name).read_bytes()).hexdigest(), details['sha256'])

    def test_normal_reader_hides_distinct_cells_on_both_chips(self):
        cases = [
            (FIRST/'final-alternating-reads', 'read-0-mode-0.bin', 'read-1-mode-14.bin'),
            (SECOND/'final-alternating', 'normal-1.bin', 'workaround-1.bin'),
        ]
        for folder, normal_name, fixed_name in cases:
            with self.subTest(folder=folder):
                normal, fixed = blob(folder/normal_name), blob(folder/fixed_name)
                self.assertEqual([fixed[a] for a in (0x70, 0x270, 0x470, 0x670)], [0xfe, 0xfd, 0xfb, 0xf7])
                self.assertEqual([normal[a] for a in (0x70, 0x270, 0x470, 0x670)], [0xfe, 0xfe, 0xfb, 0xfb])

    def test_second_chip_original_mirror_is_not_two_programmed_cells(self):
        folder = SECOND/'baseline'
        normal, fixed = blob(folder/'normal-1.bin'), blob(folder/'workaround-1.bin')
        self.assertEqual((normal[1], normal[0x201]), (0x4f, 0x4f))
        self.assertEqual((fixed[1], fixed[0x201]), (0x4f, 0xff))

    def test_recorded_ablation_requires_both_rail_drive_and_supply_setting(self):
        expected = blob(FIRST/'independent-0470/after-2.bin')
        for mode in (0, 1, 5, 6, 12, 14, 15):
            with self.subTest(mode=mode):
                a = blob(FIRST/f'ablation-{mode}/read-1.bin')
                self.assertEqual(a, blob(FIRST/f'ablation-{mode}/read-2.bin'))
                self.assertEqual(a == expected, mode in (12, 14))


class RF2ExecutableRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mini = Path(os.environ.get('MINIPRO_TEST_SOURCE', ROOT/'.tools/minipro'))
        if not shutil.which('cc') or not (cls.mini/'src/minipro.h').exists():
            message = 'C regression tests require cc and pinned MiniPro sources at .tools/minipro (or MINIPRO_TEST_SOURCE)'
            if os.environ.get('RF2_REQUIRE_MOCK') == '1':
                raise RuntimeError(message)
            raise unittest.SkipTest(message)
        lock = json.loads((ROOT/'dependencies.lock.json').read_text())
        revision = subprocess.check_output(['git', '-C', str(cls.mini), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != lock['minipro']['revision']:
            raise RuntimeError('MiniPro test headers/source must match dependencies.lock.json')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.build = Path(cls.tmp.name)
        cls.source = (FIRST/'minimal-writer.c').read_text()
        cls.programs = {}
        for address, value in ((0x70, 0xfe), (0x270, 0xfd), (0x470, 0xfb), (0x670, 0xf7)):
            cls.programs[address] = cls.compile(f'fixed-{address:x}', cls.source, address, value)
        cls.low_supply = cls.compile('low-supply', cls.source.replace('5.18,0.01', '5.0,0.01'))
        start = cls.source.index('static void route_a9(')
        end = cls.source.index('static void configure(', start)
        digital = cls.source[:start] + 'static void route_a9(unsigned a) {(void)a;}\n' + cls.source[end:]
        digital = digital.replace('dir[z(22)]=MP_PIN_DIRECTION_IN;', 'dir[z(22)]=MP_PIN_DIRECTION_OUT;')
        cls.digital = cls.compile('digital-a9', digital)
        cls.legacy = cls.compile('legacy', (cls.mini/'tools/rf2-direct.c').read_text())

    @classmethod
    def compile(cls, name, source, address=0x270, value=0xfd):
        cfile = cls.build/(name+'.c')
        cfile.write_text(source)
        binary = cls.build/name
        subprocess.run(['cc', '-std=c99', '-D_POSIX_C_SOURCE=200809L',
                        f'-DTEST_ADDRESS={address}', f'-DTEST_VALUE={value}',
                        '-I'+str(cls.mini/'src'), str(cfile),
                        str(ROOT/'tests/fixtures/rf2_a9_mock.c'), '-o', str(binary)],
                       check=True, capture_output=True, text=True)
        return binary

    def setUp(self):
        self.tmpcase = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpcase.cleanup)
        self.case = Path(self.tmpcase.name)

    def invoke(self, binary, initial, target=None, flags=None, serial=SERIAL):
        image, output, physical = [self.case/n for n in ('initial.bin', 'output.bin', 'physical.bin')]
        image.write_bytes(initial)
        output.unlink(missing_ok=True)
        physical.unlink(missing_ok=True)
        env = {k: v for k, v in os.environ.items() if not k.startswith('MOCK_')}
        env.update(MOCK_IMAGE=str(image), MOCK_PHYSICAL_OUT=str(physical), MOCK_A9_MARGIN='1')
        env.update(flags or {})
        args = [str(binary), '--serial', serial]
        if target is None:
            args += ['read', str(output)]
        else:
            targetfile = self.case/'target.bin'
            targetfile.write_bytes(target)
            args += ['write', str(targetfile), str(output), '1']
        result = subprocess.run(args, env=env, cwd=self.case, capture_output=True, text=True, timeout=10)
        return result, output.read_bytes() if output.exists() else None, physical.read_bytes() if physical.exists() else None

    def test_workaround_reads_distinct_data_and_each_missing_component_reproduces_alias(self):
        initial = blob(SECOND/'independent-0470/after-2.bin')
        for name, binary in [('fixed', self.programs[0x270]), ('legacy', self.legacy),
                             ('low-supply', self.low_supply), ('digital', self.digital)]:
            with self.subTest(mode=name):
                result, read, physical = self.invoke(binary, initial)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(physical, initial)
                self.assertIn('MOCK pulses=0 cleanup=OK', result.stderr)
                expected = initial if name == 'fixed' else bytes(initial[a & ~0x200] for a in range(2048))
                self.assertEqual(read, expected)

    def test_four_single_pulses_preserve_a9_partner_in_both_a10_regions(self):
        initial = blob(SECOND/'baseline/workaround-1.bin')
        for address, value in ((0x270, 0xfd), (0x70, 0xfe), (0x670, 0xf7), (0x470, 0xfb)):
            with self.subTest(address=address):
                target = bytearray(initial)
                target[address] = value
                result, read, physical = self.invoke(self.programs[address], initial, target)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(read, target)
                self.assertEqual(physical, target)
                self.assertIn('MOCK pulses=1 cleanup=OK', result.stderr)
                initial = bytes(target)

    def test_legacy_write_alias_is_observable_in_full_readback(self):
        initial = bytes([255])*2048
        target = bytearray(initial)
        target[0x270] = 0xfd
        result, read, physical = self.invoke(self.legacy, initial, target)
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual((read[0x70], read[0x270]), (0xfd, 0xfd))
        self.assertEqual((physical[0x70], physical[0x270]), (0xfd, 0xff))
        self.assertIn('MOCK pulses=1 cleanup=OK', result.stderr)

    def test_guards_fail_without_pulses_and_reset_outputs(self):
        initial = blob(SECOND/'baseline/workaround-1.bin')
        good = bytearray(initial)
        good[0x270] = 0xfd
        stale = bytearray(good)
        stale[1] = 0xff
        wrong = bytearray(good)
        wrong[0x270] = 0xfc
        for name, target, flags in [('stale-baseline', stale, {}), ('wrong-value', wrong, {}),
                                    ('contact', good, {'MOCK_CONTACT_FAIL': '1'}),
                                    ('overvoltage', good, {'MOCK_OVERVOLT': '1'})]:
            with self.subTest(case=name):
                result, _, physical = self.invoke(self.programs[0x270], initial, target, flags)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(physical, initial)
                self.assertIn('MOCK pulses=0 cleanup=OK', result.stderr)

    def test_failed_immediate_verify_does_not_retry(self):
        initial = bytes([255])*2048
        target = bytearray(initial)
        target[0x270] = 0xfd
        result, _, physical = self.invoke(self.programs[0x270], initial, target, {'MOCK_VERIFY_FAIL': '1'})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(physical, initial)
        self.assertIn('MOCK pulses=1 cleanup=OK', result.stderr)


if __name__ == '__main__':
    unittest.main()
