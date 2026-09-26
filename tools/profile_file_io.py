#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,platform,subprocess,tempfile,time,statistics,shutil,os
from pathlib import Path

def med(xs): return statistics.median(xs)
def timed(exe,runs):
    out=[]
    for _ in range(runs):
        t=time.perf_counter_ns(); p=subprocess.run([str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=False); dt=(time.perf_counter_ns()-t)/1e6
        if p.returncode: raise RuntimeError(p.stderr)
        out.append(dt)
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--strut',default='../strut/build/strut');ap.add_argument('--runs',type=int,default=7);ap.add_argument('--sizes',default='1024,1048576,104857600');ap.add_argument('--output',default='profiles/results/file-io.json');a=ap.parse_args()
    root=Path(__file__).resolve().parents[1];st=Path(a.strut);st=st if st.is_absolute() else (root/st).resolve()
    tools={'strut':str(st),'cpp':shutil.which(os.environ.get('CXX','g++')) or shutil.which('clang++'),'rust':shutil.which('rustc'),'go':shutil.which('go')}
    res={'hostname':platform.node(),'note':'Cached whole-file read wall time including process startup. Run on a quiet system; storage/page-cache state matters.','sizes':{}}
    with tempfile.TemporaryDirectory(prefix='strut-fileio-') as td:
        td=Path(td)
        for size in map(int,a.sizes.split(',')):
            data=td/f'data-{size}.bin';data.write_bytes(b'x'*size); q=str(data).replace('\\','\\\\').replace('"','\\"'); row={}
            srcs={
              'strut':(td/'r.p',f'include <filesystem>;\nfunction main() -> void : FilesystemError {{ string s := read_file("{q}"); print(s.length); }}\n'),
              'cpp':(td/'r.cpp',f'#include <fstream>\n#include <iostream>\n#include <string>\nint main(){{std::ifstream f("{q}",std::ios::binary|std::ios::ate);auto n=f.tellg();std::string s((size_t)n,\'\\0\');f.seekg(0);if(n>0)f.read(s.data(),n);std::cout<<s.size()<<"\\n";}}\n'),
              'rust':(td/'r.rs',f'use std::fs; fn main(){{let s=fs::read("{q}").unwrap();println!("{{}}",s.len());}}\n'),
              'go':(td/'r.go',f'package main\nimport("fmt";"os")\nfunc main(){{b,e:=os.ReadFile("{q}");if e!=nil{{panic(e)}};fmt.Println(len(b))}}\n')
            }
            for lang,(src,text) in srcs.items():
                tool=tools.get(lang)
                if not tool: continue
                src.write_text(text);exe=td/f'{lang}-{size}'
                if lang=='strut': cmd=[tool,str(src),'--release','-o',str(exe)]
                elif lang=='cpp': cmd=[tool,'-std=c++20','-O2','-DNDEBUG','-s',str(src),'-o',str(exe)]
                elif lang=='rust': cmd=[tool,'-C','opt-level=2','-C','strip=symbols',str(src),'-o',str(exe)]
                else: cmd=[tool,'build','-ldflags=-s -w','-o',str(exe),str(src)]
                p=subprocess.run(cmd,text=True,capture_output=True); 
                if p.returncode: row[lang]={'status':'compile_error','stderr':p.stderr}; continue
                for _ in range(2): subprocess.run([str(exe)],stdout=subprocess.DEVNULL,check=True)
                runs=timed(exe,a.runs); row[lang]={'status':'ok','runtime_ms_median':med(runs),'runs':runs,'binary_bytes':exe.stat().st_size}
            res['sizes'][str(size)]=row
    out=root/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(res,indent=2)+'\n');print(out)
if __name__=='__main__': main()
