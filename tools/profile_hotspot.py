#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,platform,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(cmd,**kw):
    print('+',' '.join(map(str,cmd)))
    return subprocess.run(cmd,**kw)

def version(cmd):
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
        return (p.stdout or '').splitlines()[0] if p.stdout else ''
    except Exception:return ''

def perf_record(perf,binary,data,report):
    data.unlink(missing_ok=True)
    p=run([perf,'record','-q','-g','-o',str(data),str(binary)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    if p.returncode or not data.exists() or data.stat().st_size==0:
        data.unlink(missing_ok=True)
        report.write_text('perf record unavailable for this run.\n'+f'exit_code: {p.returncode}\n'+(p.stderr or ''))
        return {'status':'unavailable','exit_code':p.returncode,'stderr':p.stderr or ''}
    with report.open('w') as f:
        rp=run([perf,'report','--stdio','-i',str(data)],stdout=f,stderr=subprocess.PIPE,text=True)
    if rp.returncode:
        with report.open('a') as f:f.write('\nperf report stderr:\n'+(rp.stderr or ''))
        return {'status':'report_error','exit_code':rp.returncode,'stderr':rp.stderr or ''}
    return {'status':'ok','bytes':data.stat().st_size}

def main():
    ap=argparse.ArgumentParser(description='Build profile-friendly Strut/C++ binaries and capture perf, vectorisation and assembly artifacts.')
    ap.add_argument('task',nargs='?',default='vector_sum');ap.add_argument('--strut',default=os.environ.get('STRUT_BIN','../strut/build/strut'));ap.add_argument('--cxx',default=os.environ.get('CXX','c++'));ap.add_argument('--jsonic-include',default='../strut/third_party/jsonic/include');ap.add_argument('--perf-runs',type=int,default=5);args=ap.parse_args()
    cxx=shutil.which(args.cxx) or args.cxx;strut=str(Path(args.strut).resolve());inc=str((ROOT/args.jsonic_include).resolve());out=ROOT/'profiles'/'results'/args.task;out.mkdir(parents=True,exist_ok=True)
    gen=out/'strut-generated.cpp';sb=out/'strut-profile';cb=out/'cpp-profile';srcs=ROOT/'benchmarks'/'strut'/f'{args.task}.p';srcc=ROOT/'benchmarks'/'cpp'/f'{args.task}.cpp'
    if run([strut,str(srcs),'--release','--emit-cpp',str(gen)]).returncode: raise SystemExit(1)
    common=['-std=c++20','-O2','-g','-fno-omit-frame-pointer','-pthread']
    if run([cxx,*common,'-I'+inc,str(gen),'-o',str(sb)]).returncode: raise SystemExit(1)
    if run([cxx,*common,str(srcc),'-o',str(cb)]).returncode: raise SystemExit(1)
    for label,b in [('strut',sb),('cpp',cb)]:
        with (out/f'{label}.asm').open('w') as f: run(['objdump','-d','-C',str(b)],stdout=f)
    cxx_version=version([cxx,'--version'])
    resolved_cxx=Path(cxx).resolve().name.lower()
    if 'gcc' in cxx_version.lower() or 'g++' in cxx_version.lower() or 'free software foundation' in cxx_version.lower() or 'g++' in resolved_cxx:
        # Recompile only for GCC optimisation diagnostics; these binaries are not used for timing.
        for label,src,extra in [('strut',gen,['-I'+inc]),('cpp',srcc,[])]:
            diag=out/f'{label}-vectorization.txt'; tmp=out/f'{label}-vec-probe'
            with diag.open('w') as f:
                run([cxx,*common,*extra,'-fopt-info-vec-all',str(src),'-o',str(tmp)],stderr=f,stdout=subprocess.DEVNULL)
            tmp.unlink(missing_ok=True)
    perf=shutil.which('perf'); meta={'hostname':platform.node(),'platform':platform.platform(),'cxx':cxx_version,'perf':version([perf,'--version']) if perf else None,'perf_record':{}}
    if perf:
        events='cycles,instructions,branches,branch-misses,cache-references,cache-misses'
        for label,b in [('strut',sb),('cpp',cb)]:
            with (out/f'{label}-perf-stat.txt').open('w') as f:
                sp=run([perf,'stat','-r',str(args.perf_runs),'-e',events,str(b)],stderr=f,stdout=subprocess.DEVNULL)
            meta.setdefault('perf_stat',{})[label]={'status':'ok' if sp.returncode==0 else 'unavailable','exit_code':sp.returncode}
            meta['perf_record'][label]=perf_record(perf,b,out/f'{label}.perf.data',out/f'{label}-perf-report.txt')
    else: print('perf not found: assembly/vectorisation artifacts were still generated')
    (out/'profile-meta.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(out)
if __name__=='__main__':main()
