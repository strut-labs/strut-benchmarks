#!/usr/bin/env python3
from __future__ import annotations
import argparse,subprocess,tempfile
from pathlib import Path
CASES={
 'vector':('inline','include <vector>;\nfunction main() -> void { vector<int> x; }\n'),
 'map':('inline','include <map>;\nfunction main() -> void { map<int,int> x; }\n'),
 'tuple':('inline','include <tuple>;\nfunction main() -> void { tuple<int,double> x := (1,2.0); }\n'),
 'filesystem':('inline','include <filesystem>;\nfunction main() -> void : FilesystemError { bool x := exists("."); }\n'),
 'json':('fixture','json_parse.p'),
 'async':('fixture','async_tasks.p'),
 'sqlite':('fixture','sqlite_loop.p'),
}
BUDGET={'vector':(12000,180),'map':(14000,220),'tuple':(12000,180),'filesystem':(25000,180),'json':(15000,160),'async':(12000,160),'sqlite':(20000,200)}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--strut',default='../strut/build/strut');a=ap.parse_args();root=Path(__file__).resolve().parents[1];st=Path(a.strut);st=st if st.is_absolute() else (root/st).resolve();bad=[]
 with tempfile.TemporaryDirectory(prefix='strut-codegen-budget-') as td:
  td=Path(td)
  for name,(kind,data) in CASES.items():
   if kind=='inline': src=td/f'{name}.p';src.write_text(data)
   else: src=root/'profiles/fixtures'/data
   cpp=td/f'{name}.cpp';p=subprocess.run([str(st),str(src),'--release','--emit-cpp',str(cpp)],text=True,capture_output=True);assert p.returncode==0,p.stderr
   text=cpp.read_text();actual=(len(text.encode()),len(text.splitlines()));limit=BUDGET[name];print(f'{name}: {actual[0]} bytes/{actual[1]} lines (budget {limit[0]}/{limit[1]})')
   if actual[0]>limit[0] or actual[1]>limit[1]:bad.append(name)
 raise SystemExit(1 if bad else 0)
if __name__=='__main__':main()
