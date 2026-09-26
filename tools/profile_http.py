#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, platform, socket, statistics, subprocess, tempfile, threading, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'profiles/fixtures/http_server.p'

def percentile(xs,p):
    if not xs:return None
    a=sorted(xs); i=min(len(a)-1,max(0,int(round((len(a)-1)*p))))
    return a[i]

def wait_port(port,deadline=5.0):
    end=time.monotonic()+deadline
    while time.monotonic()<end:
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.2):return True
        except OSError:time.sleep(.01)
    return False

def request(port):
    t=time.perf_counter_ns()
    with socket.create_connection(('127.0.0.1',port),timeout=2) as s:
        s.sendall(b'GET /hello HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        data=b''
        while True:
            b=s.recv(4096)
            if not b:break
            data+=b
    if b'200 OK' not in data or not data.endswith(b'hello, world!'):raise RuntimeError('bad HTTP response')
    return (time.perf_counter_ns()-t)/1e6

def batch(port,n,concurrency):
    if concurrency<=1:
        t=time.perf_counter_ns(); lat=[request(port) for _ in range(n)]; return (time.perf_counter_ns()-t)/1e6,lat
    counts=[n//concurrency]*concurrency
    for i in range(n%concurrency):counts[i]+=1
    def worker(k):return [request(port) for _ in range(k)]
    t=time.perf_counter_ns()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        chunks=list(ex.map(worker,counts))
    total=(time.perf_counter_ns()-t)/1e6
    return total,[x for c in chunks for x in c]

def main():
    ap=argparse.ArgumentParser(description='Repeatable localhost HTTP server throughput/latency profile.')
    ap.add_argument('--strut',default='../strut/build/strut');ap.add_argument('--requests',type=int,default=10000);ap.add_argument('--runs',type=int,default=5);ap.add_argument('--warmup',type=int,default=200);ap.add_argument('--concurrency',default='1,8,32');ap.add_argument('--output',default='profiles/results/http-throughput.json');a=ap.parse_args()
    st=Path(a.strut);st=st if st.is_absolute() else (ROOT/st).resolve(); levels=[int(x) for x in a.concurrency.split(',') if x.strip()]
    with tempfile.TemporaryDirectory(prefix='strut-http-throughput-') as td:
        exe=Path(td)/'server'; cpp=Path(td)/'server.cpp'
        t=time.perf_counter_ns(); p=subprocess.run([str(st),str(SRC),'--release','-o',str(exe)],text=True,capture_output=True); compile_ms=(time.perf_counter_ns()-t)/1e6
        if p.returncode:raise SystemExit(p.stderr)
        ep=subprocess.run([str(st),str(SRC),'--release','--emit-cpp',str(cpp)],text=True,capture_output=True); assert ep.returncode==0,ep.stderr
        out={'schema_version':1,'hostname':platform.node(),'requests_per_run':a.requests,'runs':a.runs,'warmup':a.warmup,'compile_ms':compile_ms,'generated_cpp_bytes':cpp.stat().st_size,'generated_cpp_lines':len(cpp.read_text().splitlines()),'levels':{}}
        for c in levels:
            proc=subprocess.Popen([str(exe)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
            try:
                if not wait_port(18091):raise RuntimeError('server did not start')
                for _ in range(a.warmup):request(18091)
                totals=[]; all_lat=[]
                for _ in range(a.runs):
                    total,lat=batch(18091,a.requests,c);totals.append(total);all_lat.extend(lat)
                rps=[a.requests/(x/1000.0) for x in totals]
                out['levels'][str(c)]={'throughput_rps':{'median':statistics.median(rps),'runs':rps},'total_ms':{'median':statistics.median(totals),'runs':totals},'latency_ms':{'median':statistics.median(all_lat),'p95':percentile(all_lat,.95),'p99':percentile(all_lat,.99),'max':max(all_lat)}}
            finally:
                if proc.poll() is None:proc.terminate()
                try:proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:proc.kill();proc.communicate()
    op=ROOT/a.output;op.parent.mkdir(parents=True,exist_ok=True);op.write_text(json.dumps(out,indent=2)+'\n');print(op)
if __name__=='__main__':main()
