#!/usr/bin/env python3
from __future__ import annotations
import argparse,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('task',nargs='?',default='vector_sum');ap.add_argument('--strut',default=os.environ.get('STRUT_BIN','../strut/build/strut'));ap.add_argument('--cxx',default=os.environ.get('CXX','c++'));ap.add_argument('--jsonic-include',default='../strut/third_party/jsonic/include');args=ap.parse_args()
    cxx=shutil.which(args.cxx) or args.cxx; out=ROOT/'profiles'/'results'/args.task;out.mkdir(parents=True,exist_ok=True);gen=out/'strut-generated.cpp'
    subprocess.run([str(Path(args.strut).resolve()),str(ROOT/'benchmarks'/'strut'/f'{args.task}.p'),'--release','--emit-cpp',str(gen)],check=True)
    common=['-std=c++20','-O2','-S','-masm=intel']
    subprocess.run([cxx,*common,'-I'+str((ROOT/args.jsonic_include).resolve()),str(gen),'-o',str(out/'strut.s')],check=True)
    subprocess.run([cxx,*common,str(ROOT/'benchmarks'/'cpp'/f'{args.task}.cpp'),'-o',str(out/'cpp.s')],check=True)
    print(out/'strut.s');print(out/'cpp.s')
if __name__=='__main__':main()
