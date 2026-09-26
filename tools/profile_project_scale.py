#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def timed(cmd,cwd):
    t=time.perf_counter_ns(); p=subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE); return p,(time.perf_counter_ns()-t)/1e6
def main():
    ap=argparse.ArgumentParser(description='Measure Strut project build scaling across many included source files.')
    ap.add_argument('--strut',default='../strut/build/strut'); ap.add_argument('--files',default='10,100,500'); ap.add_argument('--output',default='profiles/results/project-scale.json'); a=ap.parse_args(); st=str(Path(a.strut).resolve()); out={}
    for n in map(int,a.files.split(',')):
      with tempfile.TemporaryDirectory(prefix=f'strut-scale-{n}-') as td:
        d=Path(td)
        includes=[]
        for i in range(max(0,n-1)):
            name=f'unit{i}.h'; includes.append(f'include "{name}";')
            (d/name).write_text(f'function value{i}() -> int {{ return {i}; }}\n')
        (d/'main.p').write_text('\n'.join(includes)+('\n' if includes else '')+'function main() -> void { print(42); return; }\n')
        p,_=timed([st,'init'],d)
        if p.returncode: raise SystemExit(p.stderr)
        cold=timed([st,'make','--release'],d); noop=timed([st,'make','--release'],d)
        # Touch the last included file to measure dependency invalidation at this scale.
        touched=None
        if n>1:
            time.sleep(.02); (d/f'unit{n-2}.h').touch(); touched=timed([st,'make','--release'],d)
        out[str(n)]={'source_files':n,'cold_ms':cold[1],'noop_ms':noop[1],'touched_leaf_ms':touched[1] if touched else None,'cold_exit':cold[0].returncode,'noop_exit':noop[0].returncode,'touched_exit':touched[0].returncode if touched else None}
        if cold[0].returncode or noop[0].returncode or (touched and touched[0].returncode): raise SystemExit((cold[0].stderr or noop[0].stderr or (touched[0].stderr if touched else '')))
    op=ROOT/a.output; op.parent.mkdir(parents=True,exist_ok=True); op.write_text(json.dumps(out,indent=2)+'\n'); print(op)
if __name__=='__main__': main()
