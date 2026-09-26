#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,shutil,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def timed(cmd,cwd):
    t=time.perf_counter_ns();p=subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE);return p,(time.perf_counter_ns()-t)/1e6
def main():
    ap=argparse.ArgumentParser(description='Measure cold/warm/header-change Strut project builds.')
    ap.add_argument('--strut',default=os.environ.get('STRUT_BIN','../strut/build/strut'));ap.add_argument('--output',default='profiles/results/incremental-profile.json');ap.add_argument('--release',action='store_true');args=ap.parse_args()
    strut=str(Path(args.strut).resolve());results={}
    with tempfile.TemporaryDirectory(prefix='strut-incremental-') as td:
        d=Path(td);(d/'common.h').write_text('function value() -> int { return 42; }\n');(d/'main.p').write_text('include "common.h";\nfunction main() -> void { print(value()); return; }\n')
        p,_=timed([strut,'init'],d)
        if p.returncode: raise SystemExit(p.stderr)
        # make generated config point at main.p/output if defaults differ; init currently does this.
        cmd=[strut,'make','--verbose']+(['--release'] if args.release else [])
        for label in ('cold','noop'):
            p,ms=timed(cmd,d);results[label]={'ms':ms,'stdout':p.stdout,'stderr':p.stderr,'exit':p.returncode}
            if p.returncode: raise SystemExit(p.stderr)
        time.sleep(.02); os.utime(d/'main.p',None)
        p,ms=timed(cmd,d);results['source_touched']={'ms':ms,'stdout':p.stdout,'stderr':p.stderr,'exit':p.returncode}
        time.sleep(.02); os.utime(d/'common.h',None)
        p,ms=timed(cmd,d);results['header_touched']={'ms':ms,'stdout':p.stdout,'stderr':p.stderr,'exit':p.returncode}
        results['object_files']=[str(x.relative_to(d)) for x in (d/'.strut'/'obj').rglob('*') if x.is_file()]
        results['info_files']=[str(x.relative_to(d)) for x in (d/'.strut'/'info').rglob('*.json')]
    out=ROOT/args.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(results,indent=2)+'\n')
    for k,v in results.items():
        if isinstance(v,dict) and 'ms' in v: print(f'{k:16s} {v["ms"]:9.3f} ms  {v["stdout"].strip().replace(chr(10)," | ")}')
    print(out)
if __name__=='__main__':main()
