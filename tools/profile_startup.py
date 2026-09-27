#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,platform,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def timed(command,cwd):
 start=time.perf_counter_ns();result=subprocess.run(command,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);elapsed=(time.perf_counter_ns()-start)/1e6
 if result.returncode:raise RuntimeError(result.stderr)
 return elapsed,result.stdout
def stats(values):return {'median':statistics.median(values),'min':min(values),'max':max(values),'runs':values}
def main():
 ap=argparse.ArgumentParser(description='Measure Strut process startup and trivial compile/run latency.');ap.add_argument('--strut',default='../strut/build/strut');ap.add_argument('--runs',type=int,default=30);ap.add_argument('--output',default='profiles/results/startup.json');a=ap.parse_args()
 compiler=Path(a.strut);compiler=compiler if compiler.is_absolute() else (ROOT/compiler).resolve();samples={k:[] for k in ('version','hello_compile','hello_run')}
 with tempfile.TemporaryDirectory(prefix='strut-startup-profile-') as temporary:
  root=Path(temporary);source=root/'hello.p';binary=root/'hello';source.write_text('function main() -> int { return 0; }\n')
  for _ in range(a.runs):
   elapsed,output=timed([str(compiler),'--version'],root);assert output.strip()=='strut 0.0.2';samples['version'].append(elapsed)
   elapsed,_=timed([str(compiler),str(source),'--release','-o',str(binary)],root);samples['hello_compile'].append(elapsed)
   elapsed,_=timed([str(binary)],root);samples['hello_run'].append(elapsed)
 result={'schema_version':1,'hostname':platform.node(),'runs':a.runs,'latency_ms':{k:stats(v) for k,v in samples.items()}}
 output=ROOT/a.output;output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n');print(output)
if __name__=='__main__':main()
