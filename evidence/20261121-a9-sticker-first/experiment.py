import sys,json
from pathlib import Path
from rom_programmers.cli import load_config,profiles,tool_identity
from rom_programmers.session import Session,BenchLock,digest
from rom_programmers.backends import T48
base=Path('sessions/20261121-a9-sticker-first')
name=sys.argv[1]; addr=int(sys.argv[2],16); value=int(sys.argv[3],16)
c=load_config('bench-pc003-read.json','t48'); c['program_vpp']=25
with BenchLock('t48:'+c['serial']):
 s=Session(base/name,{'action':'one-pulse address-alias experiment','specimen':'first A9-sticker RF2','address':addr,'value':value,'config':c,'tools':tool_identity(c,'t48',True),'setup_confirmed':True})
 try:
  d=T48(c,profiles()['t48-rf2'],s)
  before=d.read('before').read_bytes()
  assert len(before)==2048 and (before[addr]&value)==value and before[addr]!=value
  target=bytearray(before); target[addr]=value
  inp=s.path/'target.bin'; inp.write_bytes(target); out=s.path/'writer-readback.bin'
  try: s.run('program',d.command()+['write',inp,out,'1'],writing=True,outputs=[out])
  except RuntimeError:
   assert s.record['steps'][-1]['exit_code']==3 and out.exists()
  log=(s.path/'program.log').read_text()
  assert 'Reset pin drivers: OK; changed=1 ' in log
  s.record['write_completed']=True; s.save()
  a=d.read('after-1').read_bytes(); b=d.read('after-2').read_bytes()
  assert a==b==out.read_bytes()
  changes=[{'address':f'{i:04X}','before':f'{x:02X}','after':f'{y:02X}'} for i,(x,y) in enumerate(zip(before,a)) if x!=y]
  unexpected=[i for i,(x,y) in enumerate(zip(before,a)) if x!=y and i not in [addr,addr^0x200]]
  s.finish('observed',readbacks_verified=True,matches_target=a==target,changes=changes,unexpected_addresses=unexpected,sha256=digest(out))
  print(json.dumps({'experiment':name,'changes':changes,'unexpected_addresses':unexpected,'shutdown':s.record['shutdown']}))
  assert not unexpected and a[addr]==value
 except BaseException as e:
  s.finish('failed',error=str(e)); raise
