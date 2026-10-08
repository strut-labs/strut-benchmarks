import subprocess,sys,pathlib
sys.path.insert(0,'/tmp')
# Reuse only definitions, never execute the A/B harness.
ns={};exec(open('/tmp/r85-ab.py').read().split('runs=[]')[0],ns)
ssh=ns['ssh'];A=ns['A'];B=ns['B'];out=ns['OUT']
assert 'pid=' not in ssh(A,'ss -ltnp sport = :8080')
ssh(A,'g++ -std=c++17 -O2 -pthread -I /root/bench/share/strut/jsonic /root/bench/r85-diag.cpp -o /root/bench/r85iw_diag',timeout=60)
unit='r85iw-diagnostic'
try:
 ssh(A,f'systemd-run --unit={unit} --collect --setenv=STRUT_HTTP_REACTOR=1 /root/bench/r85iw_diag')
 gate=ssh(A,f'pid=$(systemctl show -p MainPID --value {unit}); test "$(readlink -f /proc/$pid/exe)" = /root/bench/r85iw_diag; ss -ltnp sport = :8080 | grep "pid=$pid,"; echo THREADS=$(ls /proc/$pid/task | wc -l)')
 assert 'THREADS=6' in gate
 text=ssh(B,'wrk -t2 -c50 -d15s --timeout 2s http://96.126.107.155:8080/plaintext',timeout=50)
 assert 'Socket errors:' not in text and 'Non-2xx or 3xx' not in text
 counters=ssh(A,f'journalctl -u {unit} --no-pager -o cat | grep "R85 completions="')
 (out/'remote-mechanism.txt').write_text(gate+'\n'+text+'\n'+counters)
 print(counters,flush=True)
finally:
 ssh(A,f'systemctl stop {unit}',timeout=55)
 assert 'pid=' not in ssh(A,'ss -ltnp sport = :8080')
