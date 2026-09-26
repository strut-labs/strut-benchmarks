#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,platform,subprocess,tempfile,time,statistics,shutil,os
from pathlib import Path

def median(xs): return statistics.median(xs)
def compile_one(lang,tool,src,out):
    if lang=='strut': cmd=[tool,str(src),'--release','-o',str(out)]
    elif lang=='cpp': cmd=[tool,'-std=c++20','-O2','-DNDEBUG','-s',str(src),'-o',str(out)]
    elif lang=='rust': cmd=[tool,'-C','opt-level=2','-C','strip=symbols',str(src),'-o',str(out)]
    else: cmd=[tool,'build','-ldflags=-s -w','-o',str(out),str(src)]
    return subprocess.run(cmd,text=True,capture_output=True)

def run(exe,runs):
    vals=[]
    for _ in range(runs):
        t=time.perf_counter_ns();p=subprocess.run([str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);dt=(time.perf_counter_ns()-t)/1e6
        if p.returncode: raise RuntimeError(p.stderr)
        vals.append(dt)
    return vals

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--strut',default='../strut/build/strut');ap.add_argument('--runs',type=int,default=7);ap.add_argument('--files',type=int,default=2000);ap.add_argument('--output',default='profiles/results/filesystem-profile.json');a=ap.parse_args()
    root=Path(__file__).resolve().parents[1];st=Path(a.strut);st=st if st.is_absolute() else (root/st).resolve();tools={'strut':str(st),'cpp':shutil.which(os.environ.get('CXX','g++')) or shutil.which('clang++'),'rust':shutil.which('rustc'),'go':shutil.which('go')}
    result={'hostname':platform.node(),'files':a.files,'note':'Recursive traversal of an already-created tree; page-cache/filesystem state still affects results.','walk':{}}
    with tempfile.TemporaryDirectory(prefix='strut-fsbench-') as td_s:
        td=Path(td_s);tree=td/'tree';tree.mkdir()
        for i in range(a.files):
            d=tree/f'd{i%20}';d.mkdir(exist_ok=True);(d/f'f{i}.txt').write_text('x')
        q=str(tree).replace('\\','\\\\').replace('"','\\"')
        sources={
          'strut':f'include <filesystem>;\nfunction main() -> void : FilesystemError {{ string[] xs := walk("{q}"); print(xs.length); }}\n',
          'cpp':f'#include <filesystem>\n#include <iostream>\nint main(){{long long n=0;for(auto const&e:std::filesystem::recursive_directory_iterator("{q}"))++n;std::cout<<n<<"\\n";}}\n',
          'rust':f'use std::fs; use std::path::Path; fn walk(p:&Path,n:&mut usize){{for e in fs::read_dir(p).unwrap(){{let p=e.unwrap().path();*n+=1;if p.is_dir(){{walk(&p,n)}}}}}} fn main(){{let mut n=0;walk(Path::new("{q}"),&mut n);println!("{{}}",n);}}\n',
          'go':f'package main\nimport("fmt";"io/fs";"path/filepath")\nfunc main(){{n:=0;filepath.WalkDir("{q}",func(p string,d fs.DirEntry,e error)error{{if e!=nil{{return e}};if p!="{q}"{{n++}};return nil}});fmt.Println(n)}}\n'
        }
        exts={'strut':'p','cpp':'cpp','rust':'rs','go':'go'}
        for lang,text in sources.items():
            tool=tools.get(lang)
            if not tool: continue
            src=td/f'walk.{exts[lang]}';src.write_text(text);exe=td/f'walk-{lang}';p=compile_one(lang,tool,src,exe)
            if p.returncode: result['walk'][lang]={'status':'compile_error','stderr':p.stderr};continue
            for _ in range(2):subprocess.run([str(exe)],stdout=subprocess.DEVNULL,check=True)
            vals=run(exe,a.runs);result['walk'][lang]={'status':'ok','runtime_ms_median':median(vals),'runs':vals}
    out=root/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(out)
if __name__=='__main__':main()
