#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shutil, socket, statistics, subprocess, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "profiles" / "fixtures"
DEFAULTS = ["json_parse", "async_tasks", "sqlite_loop"]

def median(xs):
    return statistics.median(xs) if xs else None

def run(cmd, *, cwd=None, timeout=120):
    t0=time.perf_counter_ns()
    p=subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout)
    return p,(time.perf_counter_ns()-t0)/1e6

def rss_kib(binary):
    gt=Path('/usr/bin/time')
    if not gt.exists(): return None
    p=subprocess.run([str(gt),'-f','__RSS__ %M',str(binary)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=120)
    if p.returncode: return None
    for line in p.stderr.splitlines():
        if line.startswith('__RSS__ '):
            return int(line.split()[1])
    return None

def profile_fixture(strut, name, runs, runtime_runs, outdir):
    src=FIXTURES/f'{name}.p'
    binary=outdir/name
    compile_samples=[]
    for _ in range(runs):
        binary.unlink(missing_ok=True)
        p,ms=run([strut,str(src),'--release','-o',str(binary)])
        if p.returncode:
            return {'status':'compile_error','stderr':p.stderr}
        compile_samples.append(ms)
    runtime=[]
    for _ in range(runtime_runs):
        p,ms=run([str(binary)])
        if p.returncode:
            return {'status':'runtime_error','stdout':p.stdout,'stderr':p.stderr}
        runtime.append(ms)
    emitted=outdir/f'{name}.generated.cpp'
    ep,_=run([strut,str(src),'--release','--emit-cpp',str(emitted)])
    generated={} if ep.returncode else {'generated_cpp_bytes':emitted.stat().st_size,'generated_cpp_lines':len(emitted.read_text().splitlines())}
    return {
        'status':'ok',
        'compile_ms':{'median':median(compile_samples),'runs':compile_samples},
        'runtime_ms':{'median':median(runtime),'runs':runtime},
        'rss_kib':rss_kib(binary),
        'binary_bytes':binary.stat().st_size,
        **generated,
    }

def wait_port(port, deadline=5.0):
    end=time.monotonic()+deadline
    while time.monotonic()<end:
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.1):
                return True
        except OSError:
            time.sleep(.02)
    return False

def http_request(port):
    with socket.create_connection(('127.0.0.1',port),timeout=2) as s:
        s.sendall(b'GET /hello HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        chunks=[]
        while True:
            b=s.recv(65536)
            if not b: break
            chunks.append(b)
    return b''.join(chunks)

def profile_http(strut,outdir,requests=1000):
    src=FIXTURES/'http_server.p'; binary=outdir/'http_server'
    p,compile_ms=run([strut,str(src),'--release','-o',str(binary)])
    if p.returncode: return {'status':'compile_error','stderr':p.stderr}
    # The fixture serves 2000 requests. One probe + requested benchmark calls stays below that.
    proc=subprocess.Popen([str(binary)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        if not wait_port(18091):
            proc.kill(); out,err=proc.communicate(timeout=2)
            return {'status':'startup_error','stdout':out,'stderr':err}
        # wait_port itself consumes one accepted socket with no request; server handles it and continues.
        first=http_request(18091)
        if b'200 OK' not in first or not first.endswith(b'hello, world!'):
            return {'status':'wrong_response','response':first.decode(errors='replace')}
        samples=[]
        t0=time.perf_counter_ns()
        for _ in range(requests):
            q0=time.perf_counter_ns(); r=http_request(18091); samples.append((time.perf_counter_ns()-q0)/1e6)
            if b'200 OK' not in r: return {'status':'bad_http_response'}
        total_ms=(time.perf_counter_ns()-t0)/1e6
        return {
            'status':'ok','compile_ms':compile_ms,'requests':requests,
            'total_ms':total_ms,'requests_per_second':requests/(total_ms/1000.0),
            'latency_ms':{'median':median(samples),'min':min(samples),'max':max(samples)},
            'binary_bytes':binary.stat().st_size,
        }
    finally:
        if proc.poll() is None: proc.terminate()
        try: proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.communicate()

def main():
    ap=argparse.ArgumentParser(description='Profile Strut feature-heavy paths separately from cross-language microbenchmarks.')
    ap.add_argument('--strut',default=os.environ.get('STRUT_BIN','../strut/build/strut'))
    ap.add_argument('--runs',type=int,default=5,help='compile samples per non-HTTP fixture')
    ap.add_argument('--runtime-runs',type=int,default=10)
    ap.add_argument('--http-requests',type=int,default=1000)
    ap.add_argument('--output',default='profiles/results/feature-profile.json')
    ap.add_argument('--skip-http',action='store_true')
    args=ap.parse_args()
    strut=str(Path(args.strut).resolve())
    if not Path(strut).exists(): ap.error(f'Strut compiler not found: {strut}')
    with tempfile.TemporaryDirectory(prefix='strut-feature-profile-') as td:
        outdir=Path(td)
        result={'schema_version':1,'fixtures':{}}
        for name in DEFAULTS:
            print(f'[{name}]',flush=True)
            result['fixtures'][name]=profile_fixture(strut,name,args.runs,args.runtime_runs,outdir)
        if not args.skip_http:
            print('[http_server]',flush=True)
            result['fixtures']['http_server']=profile_http(strut,outdir,args.http_requests)
    op=ROOT/args.output; op.parent.mkdir(parents=True,exist_ok=True)
    op.write_text(json.dumps(result,indent=2)+'\n')
    print(f'Wrote {op}')
    return 1 if any(x.get('status')!='ok' for x in result['fixtures'].values()) else 0
if __name__=='__main__': raise SystemExit(main())
