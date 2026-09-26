#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, platform, subprocess, tempfile, time
from pathlib import Path
MODULES={
 'vector':'vector<int> x;','deque':'deque<int> x;','list':'list<int> x;','map':'map<int,int> x;','set':'set<int> x;',
 'ordered_map':'ordered_map<int,int> x;','ordered_set':'ordered_set<int> x;','queue':'queue<int> x;','stack':'stack<int> x;',
 'priority_queue':'priority_queue<int> x;','tuple':'tuple<int,double> x := (1,2.0);','filesystem':'bool x := exists(".");'
}
def timed(cmd):
 t=time.perf_counter_ns(); p=subprocess.run(cmd,text=True,capture_output=True); return p,(time.perf_counter_ns()-t)/1e6
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--strut',default='../strut/build/strut');ap.add_argument('--runs',type=int,default=5);ap.add_argument('--output',default='profiles/results/module-profile.json');a=ap.parse_args();root=Path(__file__).resolve().parents[1];st=Path(a.strut);st=st if st.is_absolute() else (root/st).resolve();out={"hostname":platform.node(),"modules":{}}
 with tempfile.TemporaryDirectory(prefix='strut-modules-') as td:
  td=Path(td)
  for m,body in MODULES.items():
   src=td/f'{m}.p';cpp=td/f'{m}.cpp';exe=td/m
   sig='function main() -> void : FilesystemError' if m=='filesystem' else 'function main() -> void'
   src.write_text(f'include <{m}>;\n{sig} {{ {body} }}\n')
   runs=[]
   for _ in range(a.runs):
    p,ms=timed([str(st),str(src),'--release','-o',str(exe)]); assert p.returncode==0,p.stderr; runs.append(ms)
   p=subprocess.run([str(st),str(src),'--release','--emit-cpp',str(cpp)],text=True,capture_output=True);assert p.returncode==0,p.stderr
   text=cpp.read_text();out['modules'][m]={"compile_ms_runs":runs,"compile_ms_median":sorted(runs)[len(runs)//2],"generated_cpp_bytes":len(text.encode()),"generated_cpp_lines":len(text.splitlines())}
 path=root/a.output;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2)+'\n');print(path)
if __name__=='__main__':main()
