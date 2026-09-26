#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,tempfile
from pathlib import Path
CASES={'vector':('vector','vector<int> x;'),'map':('map','map<int,int> x;'),'tuple':('tuple','tuple<int,double> x := (1,2.0);'),'filesystem':('filesystem','bool x := exists(".");')}
# Deliberately broad ceilings: this is an accidental-bloat tripwire, not a micro-optimization gate.
BUDGET={'vector':(12000,180),'map':(14000,220),'tuple':(12000,180),'filesystem':(90000,1100)}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--strut',default='../strut/build/strut');a=ap.parse_args();root=Path(__file__).resolve().parents[1];st=Path(a.strut);st=st if st.is_absolute() else (root/st).resolve();bad=[]
 with tempfile.TemporaryDirectory(prefix='strut-codegen-budget-') as td:
  td=Path(td)
  for name,(mod,body) in CASES.items():
   src=td/f'{name}.p';cpp=td/f'{name}.cpp';sig='function main() -> void : FilesystemError' if mod=='filesystem' else 'function main() -> void';src.write_text(f'include <{mod}>;\n{sig} {{ {body} }}\n');p=subprocess.run([str(st),str(src),'--release','--emit-cpp',str(cpp)],text=True,capture_output=True);assert p.returncode==0,p.stderr
   text=cpp.read_text();actual=(len(text.encode()),len(text.splitlines()));limit=BUDGET[name];print(f'{name}: {actual[0]} bytes/{actual[1]} lines (budget {limit[0]}/{limit[1]})');
   if actual[0]>limit[0] or actual[1]>limit[1]:bad.append(name)
 raise SystemExit(1 if bad else 0)
if __name__=='__main__':main()
