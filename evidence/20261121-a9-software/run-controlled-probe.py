from pathlib import Path
import sys
from rom_programmers.session import Session,BenchLock,digest
from rom_programmers.cli import load_config
base=Path('sessions/20261121-a9-software');a=int(sys.argv[1],16);v=int(sys.argv[2],16);exe=(base/('writer-'+sys.argv[1])).resolve();reader=(base/'combined-writer').resolve();c=load_config('bench-pc003-read.json','t48')
with BenchLock('t48:'+c['serial']):
 s=Session(base/('independent-'+sys.argv[1]),{'action':'one pulse explicit address, preserved combined-mode baseline','address':a,'value':v,'binary_sha256':digest(exe)})
 bs=[]
 for n in ['before-1','before-2']:
  dest=s.path/(n+'.bin');s.run(n,[reader,'--serial',c['serial'],'read',dest],outputs=[dest]);bs.append(dest.read_bytes())
 assert bs[0]==bs[1];before=bs[0];target=bytearray(before);assert target[a]==255;target[a]=v
 inp=s.path/'target.bin';inp.write_bytes(target);out=s.path/'writer-readback.bin'
 try:s.run('program',[exe,'--serial',c['serial'],'write',inp,out,'1'],writing=True,outputs=[out])
 except RuntimeError:pass
 log=(s.path/'program.log').read_text();print(log,flush=True)
 reads=[]
 for n in ['after-1','after-2']:
  dest=s.path/(n+'.bin');s.run(n,[reader,'--serial',c['serial'],'read',dest],outputs=[dest]);b=dest.read_bytes();reads.append(b);print(n,[(f'{i:04X}',f'{x:02X}',f'{y:02X}') for i,(x,y) in enumerate(zip(before,b)) if x!=y],flush=True)
 ok=all(b==target for b in reads) and out.exists() and out.read_bytes()==target
 s.finish('verified' if ok else 'observed',shutdown='reported-off',write_completed='changed=1' in log,combined_reads_match=reads[0]==reads[1],matches_target=ok,sha256=digest(s.path/'after-2.bin'))
 assert ok
