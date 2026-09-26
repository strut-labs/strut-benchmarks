#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, platform, re, shutil, statistics, subprocess, tempfile, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TIMING_RE=re.compile(r'^timing ([a-z_]+)=([0-9.]+)$',re.M)

def run_timed(cmd,cwd=None):
    t=time.perf_counter_ns(); p=subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE); ms=(time.perf_counter_ns()-t)/1e6
    return p,ms

def median(v): return statistics.median(v) if v else None

def command_version(cmd):
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
        return (p.stdout or '').strip().splitlines()[0] if p.stdout else ''
    except Exception:
        return ''

def machine_info(strut,cxx):
    cpu=''
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.lower().startswith('model name'):
                cpu=line.split(':',1)[1].strip(); break
    except Exception:
        pass
    return {
        'hostname':platform.node(),
        'platform':platform.platform(),
        'machine':platform.machine(),
        'cpu':cpu,
        'strut':command_version([strut,'--version']),
        'cxx':command_version([cxx,'--version']),
    }

def main():
    ap=argparse.ArgumentParser(description='Profile the Strut frontend separately from matching direct native compilation and project-style object/link work.')
    ap.add_argument('--strut',default=os.environ.get('STRUT_BIN','../strut/build/strut'))
    ap.add_argument('--source',default='benchmarks/strut/vector_sum.p')
    ap.add_argument('--runs',type=int,default=10)
    ap.add_argument('--cxx',default=os.environ.get('CXX','c++'))
    ap.add_argument('--jsonic-include',default='../strut/third_party/jsonic/include')
    ap.add_argument('--output',default='profiles/results/compile-profile.json')
    args=ap.parse_args()
    strut=str(Path(args.strut).resolve()); src=(ROOT/args.source).resolve(); cxx=shutil.which(args.cxx) or args.cxx; inc=str((ROOT/args.jsonic_include).resolve())
    result={'source':str(src),'runs':args.runs,'environment':machine_info(strut,cxx),'full_compile_ms':[],'emit_cpp_ms':[],'host_direct_compile_ms':[],'project_host_object_ms':[],'project_host_link_ms':[],'strut_phase_samples':[],'generated_cpp_bytes':0,'generated_cpp_lines':0}
    with tempfile.TemporaryDirectory(prefix='strut-profile-') as td:
        td=Path(td); exe=td/'strut-app'; gen=td/'generated.cpp'; obj=td/'generated.o'
        # Warm both toolchains before recording medians.
        subprocess.run([strut,str(src),'--release','-o',str(exe)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(args.runs):
            exe.unlink(missing_ok=True)
            p,ms=run_timed([strut,str(src),'--release','--timings','-o',str(exe)],ROOT)
            if p.returncode: raise SystemExit(p.stderr)
            result['full_compile_ms'].append(ms)
            result['strut_phase_samples'].append({k:float(v) for k,v in TIMING_RE.findall(p.stdout)})
        for _ in range(args.runs):
            gen.unlink(missing_ok=True)
            p,ms=run_timed([strut,str(src),'--release','--timings','--emit-cpp',str(gen)],ROOT)
            if p.returncode: raise SystemExit(p.stderr)
            result['emit_cpp_ms'].append(ms)
        text=gen.read_text(); result['generated_cpp_bytes']=gen.stat().st_size; result['generated_cpp_lines']=len(text.splitlines())
        # Match CppBackend::compile() for a native, direct, one-file release build.
        direct_cmd=[cxx,'-std=c++20','-O2','-ffunction-sections','-fdata-sections','-I'+inc,str(gen),'-o',str(exe),'-Wl,--gc-sections','-s']
        # Project/object builds intentionally retain LTO across translation units.
        object_cmd=[cxx,'-std=c++20','-O2','-flto','-ffunction-sections','-fdata-sections','-I'+inc,'-c',str(gen),'-o',str(obj)]
        link_cmd=[cxx,str(obj),'-flto','-Wl,--gc-sections','-s','-o',str(exe)]
        for _ in range(args.runs):
            exe.unlink(missing_ok=True); p,ms=run_timed(direct_cmd,ROOT)
            if p.returncode: raise SystemExit(p.stderr)
            result['host_direct_compile_ms'].append(ms)
        for _ in range(args.runs):
            obj.unlink(missing_ok=True); p,ms=run_timed(object_cmd,ROOT)
            if p.returncode: raise SystemExit(p.stderr)
            result['project_host_object_ms'].append(ms)
        for _ in range(args.runs):
            exe.unlink(missing_ok=True); p,ms=run_timed(link_cmd,ROOT)
            if p.returncode: raise SystemExit(p.stderr)
            result['project_host_link_ms'].append(ms)
    phases={}
    for sample in result['strut_phase_samples']:
        for k,v in sample.items(): phases.setdefault(k,[]).append(v)
    result['medians']={
        'full_compile_ms':median(result['full_compile_ms']),
        'emit_cpp_ms':median(result['emit_cpp_ms']),
        'host_direct_compile_ms':median(result['host_direct_compile_ms']),
        'project_host_object_ms':median(result['project_host_object_ms']),
        'project_host_link_ms':median(result['project_host_link_ms']),
        'phases':{k:median(v) for k,v in phases.items()}}
    out=(ROOT/args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'environment':result['environment'],'medians':result['medians']},indent=2));print(f'generated C++: {result["generated_cpp_lines"]} lines, {result["generated_cpp_bytes"]} bytes');print(out)
if __name__=='__main__': main()
