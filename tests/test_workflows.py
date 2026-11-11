import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from rom_programmers.cli import main
from rom_programmers.session import BenchLock, Session, digest

FAKE = r'''#!/usr/bin/env python3
import json,sys,pathlib
root=pathlib.Path(__file__).parent
args=sys.argv[1:]
chip=root/'chip.bin'
with (root/'calls.log').open('a') as f:f.write(json.dumps(args)+'\n')
if args[0]=='--serial' and '--session-dir' not in args:
 action=args[2]
 if action=='write':
  image=pathlib.Path(args[3]).read_bytes();chip.write_bytes(image);out=pathlib.Path(args[4])
  print('Reset pin drivers: OK; changed=1 remaining=0')
 else:
  out=pathlib.Path(args[3]);print('Reset pin drivers: OK; changed=0 remaining=0')
 data=chip.read_bytes()
 if (root/'short').exists():data=data[:-1]
 if (root/'disagree').exists() and 'read-2' in out.name:data=bytes([data[0]^1])+data[1:]
 out.write_bytes(data)
 if (root/'no-reset').exists():sys.exit(4)
 sys.exit(0)
folder=pathlib.Path(args[args.index('--session-dir')+1]);folder.mkdir(parents=True,exist_ok=True)
execution=args[args.index('--exec')+1]
remote=root/'remote';remote.mkdir(exist_ok=True)
for i,arg in enumerate(args):
 if arg=='--put':
  local,name=args[i+1].rsplit(':',1);data=pathlib.Path(local).read_bytes();target=remote/name
  if not target.exists() or target.read_bytes()!=data:
   target.write_bytes(data)
   with (root/'uploads.log').open('a') as f:f.write(name+'\n')
marker=folder/'executed'
if execution.startswith('WRITER'):
 if not marker.exists():
  assert (remote/'2732A.OK').read_bytes()==b'D2732A-5V-21V-50MS\n'
  chip.write_bytes((remote/'IMAGE.BIN').read_bytes());marker.touch()
  with (root/'pulses.log').open('a') as f:f.write('program\n')
  if (root/'lose-reply').exists():
   (folder/'session.json').write_text(json.dumps({'exit_status':None}));sys.exit(1)
 text='SAFE OFF: VPP off, VCC off\nWRITE PASSED: all 4096 bytes verified after power cycle\n'
else:
 (folder/'READ.BIN').write_bytes(chip.read_bytes())
 text='' if (root/'missing-marker').exists() else 'Safe shutdown complete: VCC off, VPP off\n'
(folder/'STDOUT.TXT').write_text(text)
(folder/'session.json').write_text(json.dumps({'exit_status':0}))
'''


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.tool = self.root / 'fake'
        self.tool.write_text(FAKE)
        self.tool.chmod(0o755)
        self.image = self.root / 'image.bin'
        self.config = self.root / 'bench.json'
        self.session = self.root / 'session'
        for name in ('reader', 'writer'):
            (self.root / name).write_bytes(b'tool-' + name.encode())
        self.config.write_text(json.dumps({
            't48': {'serial': 'TEST', 'rf2': str(self.tool), 'program_vpp': 25},
            'willem': {'port': str(self.root/'serial'), 'baud': 57600, 'program_vpp': 21,
                       'dosravi': [sys.executable, str(self.tool)], 'reader': str(self.root/'reader'),
                       'writer': str(self.root/'writer')}}))
        self.prepare(2048)

    def prepare(self, size):
        self.image.write_bytes(bytes((i*19)&255 for i in range(size)))
        (self.root/'chip.bin').write_bytes(b'\xff'*size)

    def call(self, action, profile='t48-rf2', resume=False, extra=()):
        argv=[action, '--profile', profile, '--config', str(self.config),
              '--resume' if resume else '--session', str(self.session)]
        if action in ('verify','program'):
            argv += ['--image', str(self.image)]
        argv += list(extra)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(argv)

    def record(self):
        return json.loads((self.session/'session.json').read_text())

    def test_t48_program_verifies_two_fresh_reads(self):
        self.assertEqual(self.call('program',extra=['--setup-confirmed']),0)
        r=self.record()
        self.assertEqual(r['status'],'verified')
        self.assertEqual(r['result_sha256'],digest(self.image))
        self.assertTrue(r['write_completed'])
        self.assertEqual([s['name'] for s in r['steps']],['before','program','read-1','read-2'])
        self.assertEqual(r['shutdown'],'reported-off')

    def test_size_checked_before_hardware(self):
        self.image.write_bytes(b'wrong')
        self.assertEqual(self.call('program',extra=['--setup-confirmed']),1)
        self.assertFalse((self.root/'calls.log').exists())

    def test_blank_read_has_two_captures(self):
        self.assertEqual(self.call('blank-check'),0)
        self.assertTrue(self.record()['all_ff'])

    def test_nonblank_rejected(self):
        (self.root/'chip.bin').write_bytes(self.image.read_bytes())
        self.assertEqual(self.call('blank-check'),1)
        self.assertNotEqual(self.record()['status'],'verified')

    def test_incompatible_image_never_writes(self):
        (self.root/'chip.bin').write_bytes(bytes(2048))
        self.assertEqual(self.call('program',extra=['--setup-confirmed']),1)
        self.assertNotIn('program',[s['name'] for s in self.record()['steps']])

    def test_short_read_fails(self):
        (self.root/'short').touch()
        self.assertEqual(self.call('read'),1)

    def test_disagreeing_reads_fail(self):
        (self.root/'disagree').touch()
        self.assertEqual(self.call('read'),1)
        self.assertIn('disagree',self.record()['error'])

    def test_verify_mismatch_fails(self):
        self.assertEqual(self.call('verify'),1)

    def test_setup_and_voltage_guard(self):
        self.assertEqual(self.call('program'),1)
        c=json.loads(self.config.read_text());c['t48']['program_vpp']=21
        self.config.write_text(json.dumps(c))
        self.assertEqual(self.call('program',extra=['--setup-confirmed']),1)
        self.assertFalse((self.root/'calls.log').exists())

    def test_t48_2716_profile_reads_but_cannot_program(self):
        self.assertEqual(self.call('program','t48-2716-read',extra=['--setup-confirmed']),1)
        self.assertFalse((self.root/'calls.log').exists())
        self.assertEqual(self.call('read','t48-2716-read'),0)
        self.assertEqual(self.record()['request']['profile'],'t48-2716-read')

    def test_t48_2732_read_is_4k_and_never_programs(self):
        self.prepare(4096)
        self.assertEqual(self.call('program','t48-2732-read',extra=['--setup-confirmed']),1)
        self.assertFalse((self.root/'calls.log').exists())
        self.assertEqual(self.call('read','t48-2732-read'),0)
        calls=[json.loads(line) for line in (self.root/'calls.log').read_text().splitlines()]
        self.assertEqual([call[2] for call in calls],['read2732','read2732'])
        self.assertEqual((self.session/'readback.bin').stat().st_size,4096)

    def test_read_only_profile_rejects_program(self):
        self.assertEqual(self.call('program','willem-2716-read',extra=['--setup-confirmed']),1)
        self.assertFalse((self.root/'calls.log').exists())

    def test_tool_hash_guard(self):
        c=json.loads(self.config.read_text());c['t48']['sha256']={'rf2':'wrong'}
        self.config.write_text(json.dumps(c))
        self.assertEqual(self.call('read'),1)
        self.assertFalse((self.root/'calls.log').exists())

    def test_uncertain_t48_write_not_replayed(self):
        s=Session(self.session,{'test':1})
        s.record['steps']=[{'name':'program','command':['fake'],'cwd':'None','status':'unknown','log':'program.log'}]
        s.save()
        with self.assertRaisesRegex(RuntimeError,'automatic replay'):
            s.run('program',['fake'],writing=True)

    def test_willem_write_and_upload_reuse(self):
        self.prepare(4096)
        self.assertEqual(self.call('program','willem-2732a-21v',extra=['--setup-confirmed']),0)
        self.assertEqual((self.root/'uploads.log').read_text().splitlines().count('READER.COM'),1)
        self.assertEqual((self.root/'pulses.log').read_text().splitlines(),['program'])

    def test_willem_lost_reply_recovers_same_execution(self):
        self.prepare(4096);(self.root/'lose-reply').touch()
        self.assertEqual(self.call('program','willem-2732a-21v',extra=['--setup-confirmed']),1)
        self.assertEqual(self.record()['steps'][-1]['status'],'unknown')
        self.assertEqual(self.call('program','willem-2732a-21v',resume=True,extra=['--setup-confirmed','--same-agent-session']),0)
        self.assertEqual((self.root/'pulses.log').read_text().splitlines(),['program'])

    def test_dosravi_uncertain_write_needs_same_agent_assertion(self):
        self.prepare(4096);(self.root/'lose-reply').touch()
        self.call('program','willem-2732a-21v',extra=['--setup-confirmed'])
        self.assertEqual(self.call('program','willem-2732a-21v',resume=True,extra=['--setup-confirmed']),1)
        self.assertIn('agent restart',self.record()['error'])
        self.assertEqual((self.root/'pulses.log').read_text().splitlines(),['program'])

    def test_resume_changed_image_rejected(self):
        self.prepare(4096);(self.root/'lose-reply').touch()
        self.call('program','willem-2732a-21v',extra=['--setup-confirmed'])
        self.image.write_bytes(b'\xfe'*4096)
        self.assertEqual(self.call('program','willem-2732a-21v',resume=True,extra=['--setup-confirmed']),1)
        self.assertEqual((self.root/'pulses.log').read_text().splitlines(),['program'])

    def test_changed_completed_output_blocks_resume(self):
        self.prepare(4096);(self.root/'lose-reply').touch()
        self.call('program','willem-2732a-21v',extra=['--setup-confirmed'])
        (self.session/'before/READ.BIN').write_bytes(bytes(4096))
        self.assertEqual(self.call('program','willem-2732a-21v',resume=True,extra=['--setup-confirmed']),1)
        self.assertIn('changed',self.record()['error'])
        self.assertEqual((self.root/'pulses.log').read_text().splitlines(),['program'])

    def test_missing_shutdown_marker_rejects_success(self):
        self.prepare(4096);(self.root/'missing-marker').touch()
        self.assertEqual(self.call('read','willem-2732a-21v'),1)
        self.assertEqual(self.record()['shutdown'],'unknown')

    def test_interrupted_step_is_uncertain(self):
        from unittest.mock import patch
        s=Session(self.session,{'test':1})
        with patch('rom_programmers.session.subprocess.run',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                s.run('program',['fake'],writing=True)
        self.assertEqual(s.record['steps'][0]['status'],'unknown')
        self.assertEqual(s.record['shutdown'],'unknown')

    def test_lock_blocks_other_process(self):
        with BenchLock('test:'+str(self.root)):
            code='from rom_programmers.session import BenchLock\nwith BenchLock('+repr('test:'+str(self.root))+'): pass'
            r=subprocess.run([sys.executable,'-c',code],capture_output=True)
        self.assertNotEqual(r.returncode,0)

    def test_prepare_image_explicit_transform(self):
        out=self.root/'doubled.bin'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['prepare-image','--image',str(self.image),'--output',str(out),'--repeat','2']),0)
        self.assertEqual(out.read_bytes(),self.image.read_bytes()*2)
        self.assertEqual(json.loads(Path(str(out)+'.json').read_text())['repeat'],2)

if __name__=='__main__':
    unittest.main()
