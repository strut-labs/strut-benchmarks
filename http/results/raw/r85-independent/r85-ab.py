import subprocess,json,time,re,pathlib,statistics,sys
A='96.126.107.155';B='96.126.107.181'
OUT=pathlib.Path('/home/nick/Repositories/strut-labs/strut-benchmarks/http/results/raw/r85-independent');OUT.mkdir(exist_ok=True)
OPTS=['-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=3','-o','ControlMaster=auto','-o','ControlPersist=120','-o','ControlPath=/tmp/r85ssh-%r@%h:%p']
def ssh(host,cmd,timeout=60):
 r=subprocess.run(['ssh',*OPTS,'root@'+host,'set -eu; '+cmd],capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError(f'SSH {host} {cmd!r}: {r.returncode} {r.stderr} {r.stdout}')
 return r.stdout
runs=[]
if (OUT/'ab-runs.json').exists():runs=json.loads((OUT/'ab-runs.json').read_text())
start=1;end=10 if '--extend' in sys.argv else 7
for pair in range(start,end+1):
 order=['base','cand'] if pair%2 else ['cand','base']
 for tag in order:
  if any(x['pair']==pair and x['tag']==tag for x in runs):continue
  unit=f'r85iw-{pair}-{tag}';binary='/root/bench/r85iw_'+tag
  assert 'pid=' not in ssh(A,'ss -ltnp sport = :8080'), 'Port busy before run'
  try:
   ssh(A,f'systemd-run --unit={unit} --collect --setenv=STRUT_HTTP_REACTOR=1 {binary}')
   gate=ssh(A,f'pid=$(systemctl show -p MainPID --value {unit}); test "$pid" -gt 0; exe=$(readlink -f /proc/$pid/exe); test "$exe" = {binary}; ss -ltnp sport = :8080 | grep "pid=$pid,"; echo PID=$pid; echo EXE=$exe; echo COMM=$(cat /proc/$pid/comm); echo THREADS=$(ls /proc/$pid/task | wc -l); sha256sum {binary}; curl -fsS -D - http://127.0.0.1:8080/plaintext')
   assert 'THREADS=6' in gate and 'Hello, World!' in gate
   (OUT/f'pair-{pair}-{tag}-identity.txt').write_text(gate)
   ssh(B,'wrk -t2 -c50 -d10s --timeout 2s http://96.126.107.155:8080/plaintext',timeout=45)
   text=ssh(B,'wrk -t2 -c50 -d15s --latency --timeout 2s http://96.126.107.155:8080/plaintext',timeout=50)
   (OUT/f'pair-{pair}-{tag}-wrk.txt').write_text(text)
   assert 'Socket errors:' not in text and 'Non-2xx or 3xx' not in text,text
   rps=float(re.search(r'Requests/sec:\s+([\d.]+)',text)[1]);requests=int(re.search(r'(\d+) requests in',text)[1])
   after=ssh(A,f'pid=$(systemctl show -p MainPID --value {unit}); test "$(readlink -f /proc/$pid/exe)" = {binary}; ss -ltnp sport = :8080 | grep "pid=$pid,"; echo THREADS=$(ls /proc/$pid/task | wc -l)')
   assert 'THREADS=6' in after
   runs.append(dict(pair=pair,tag=tag,rps=rps,requests=requests,warm_s=10,measure_s=15,threads=2,connections=50))
   (OUT/'ab-runs.json').write_text(json.dumps(runs,indent=2));print(json.dumps(runs[-1]),flush=True)
  finally:
   ssh(A,f'systemctl stop {unit}',timeout=55)
   assert 'pid=' not in ssh(A,'ss -ltnp sport = :8080'),'Port busy after stop'
for tag in ('base','cand'):
 vals=[x['rps'] for x in runs if x['tag']==tag];print(tag,'median',statistics.median(vals),'min',min(vals),'max',max(vals),flush=True)
pairs={p:{x['tag']:x['rps'] for x in runs if x['pair']==p} for p in sorted({x['pair'] for x in runs})};wins=sum(v['cand']>v['base'] for v in pairs.values());print('paired wins',wins,'/',len(pairs),flush=True)
