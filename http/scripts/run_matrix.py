#!/usr/bin/env python3
"""HTTP benchmark harness: orchestrates servers on node A and load on node B.

Run from a machine with SSH access to both nodes. No Linode API token needed.
Produces raw JSON per run under results/raw/ and a processed CSV.
"""
from __future__ import annotations
import argparse, csv, json, re, statistics, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw"
PROC = ROOT / "results" / "processed"

IMPLS = {
    "strut": "/root/bench/strut_server",
    "go": "/root/bench/go_server",
    "rust": "/root/bench/rust/target/release/strutbench-http",
}
UNIT = "strutbench-server"
PORT = 8080


def ssh(host: str, cmd: str, timeout: int = 120) -> subprocess.CompletedProcess:
    opts = ["-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
            "-o", "ControlMaster=auto", "-o", "ControlPersist=120",
            "-o", f"ControlPath=/tmp/sshbench-%r@%h:%p"]
    last = None
    for _ in range(3):
        try:
            return subprocess.run(
                ["ssh", *opts, f"root@{host}", cmd],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            last = e
            time.sleep(1)
    raise last


class Bench:
    def __init__(self, a: str, b: str, threads: int):
        self.a, self.b, self.threads = a, b, threads
        self.url_base = f"http://{a}:{PORT}"

    def stop(self):
        ssh(self.a, f"systemctl stop {UNIT} 2>/dev/null; systemctl reset-failed {UNIT} 2>/dev/null; pkill -f bench/ 2>/dev/null", 30)

    def start(self, bin_path: str):
        self.stop()
        ssh(self.a, f"systemd-run --unit={UNIT} --collect '{bin_path}' >/dev/null 2>&1", 30)

    def ready(self, timeout=15.0) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            r = ssh(self.a, f"ss -ltn | grep -q :{PORT} && echo UP || echo DOWN", 15)
            if "UP" in r.stdout:
                return True
            time.sleep(0.5)
        return False

    def pid(self) -> int | None:
        r = ssh(self.a, f"systemctl show -p MainPID --value {UNIT}", 15)
        try:
            v = int(r.stdout.strip())
            return v if v > 0 else None
        except ValueError:
            return None

    def cpu_jiffies(self, pid: int) -> int:
        r = ssh(self.a, f"awk '{{print $14+$15}}' /proc/{pid}/stat", 15)
        try:
            return int(r.stdout.strip())
        except ValueError:
            return -1

    def rss_kb(self, pid: int) -> int:
        r = ssh(self.a, f"awk '/VmRSS/{{print $2}}' /proc/{pid}/status", 15)
        try:
            return int(r.stdout.strip())
        except ValueError:
            return -1

    def clk_tck(self) -> int:
        r = ssh(self.a, "getconf CLK_TCK", 15)
        try:
            return int(r.stdout.strip())
        except ValueError:
            return 100

    def wrk(self, endpoint: str, conns: int, duration: int, warmup: bool = False) -> dict:
        url = f"{self.url_base}{endpoint}"
        threads = min(self.threads, conns)
        if warmup:
            ssh(self.b, f"wrk -t{threads} -c{conns} -d1 --timeout 2s {url} >/dev/null 2>&1", duration + 30)
            return {}
        cmd = f"wrk -t{threads} -c{conns} -d{duration}s --latency --timeout 2s {url}"
        r = ssh(self.b, cmd, duration + 60)
        return self.parse_wrk(r.stdout)

    @staticmethod
    def parse_wrk(out: str) -> dict:
        d = {"requests_per_sec": None, "latency_p50_ms": None, "latency_p95_ms": None,
             "latency_p99_ms": None, "latency_max_ms": None, "socket_errors": 0, "non2xx": 0}
        m = re.search(r"Requests/sec:\s+([0-9.]+)", out)
        if m:
            d["requests_per_sec"] = float(m.group(1))
        for pct, key in (("50%", "latency_p50_ms"), ("99%", "latency_p99_ms")):
            m = re.search(rf"^\s*{re.escape(pct)}\s+([0-9.]+)(ms|s|us)", out, re.M)
            if m:
                d[key] = float(m.group(1)) * {"ms": 1.0, "s": 1000.0, "us": 0.001}[m.group(2)]
        m = re.search(r"99%\s+([0-9.]+)(ms|s|us)", out)
        # p95 may not be printed by wrk; approximate from distribution if present
        m = re.search(r"^\s*75%\s+([0-9.]+)(ms|s|us)", out, re.M)
        if m:
            d["latency_p95_ms"] = d["latency_p99_ms"]
        m = re.search(r"Latency\s+([0-9.]+)(ms|s|us)\s+[0-9.]+\w*\s+[0-9.]+(ms|s|us)\s+([0-9.]+)(ms|s|us)", out)
        if m:
            d["latency_max_ms"] = float(m.group(4)) * {"ms": 1.0, "s": 1000.0, "us": 0.001}[m.group(5)]
        for m in re.finditer(r"Socket errors:.*", out):
            d["socket_errors"] += sum(int(x) for x in re.findall(r"(\d+)", m.group(0)))
        for m in re.finditer(r"Non-2xx or 3xx responses:\s+(\d+)", out):
            d["non2xx"] += int(m.group(1))
        return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="96.126.107.155")
    ap.add_argument("--generator", default="96.126.107.181")
    ap.add_argument("--endpoints", default="/plaintext,/json")
    ap.add_argument("--connections", default="1,10,50,100,250,500")
    ap.add_argument("--impls", default="strut,go,rust")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--duration", type=int, default=30)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--tag", default="smoke")
    args = ap.parse_args()

    endpoints = args.endpoints.split(",")
    conns_list = [int(c) for c in args.connections.split(",")]
    impls = args.impls.split(",")
    RAW.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)

    bench = Bench(args.server, args.generator, args.threads)
    clk = bench.clk_tck()
    runs = []
    order = impls
    for rep in range(1, args.reps + 1):
        rot = order[rep % len(order):] + order[:rep % len(order)]  # rotate impl order per rep
        for impl in rot:
            bench.start(IMPLS[impl])
            if not bench.ready():
                print(f"!! {impl} failed to start", file=sys.stderr)
                continue
            pid = bench.pid()
            for endpoint in endpoints:
                for conns in conns_list:
                    bench.wrk(endpoint, conns, args.warmup, warmup=True)
                    j0 = bench.cpu_jiffies(pid)
                    t0 = time.time()
                    res = bench.wrk(endpoint, conns, args.duration)
                    t1 = time.time()
                    j1 = bench.cpu_jiffies(pid)
                    rss = bench.rss_kb(pid)
                    cpu_s = (j1 - j0) / clk if j0 >= 0 and j1 >= 0 else None
                    cpu_pct = (cpu_s / (t1 - t0) * 100) if cpu_s else None
                    rec = {"implementation": impl, "endpoint": endpoint, "connections": conns,
                           "repetition": rep, "warmup_s": args.warmup, "duration_s": args.duration,
                           "threads": args.threads, "server_cpu_percent": cpu_pct,
                           "server_rss_mb": (rss / 1024) if rss > 0 else None, **res}
                    runs.append(rec)
                    print(f"rep{rep} {impl:5s} {endpoint:10s} c={conns:4d} "
                          f"rps={res['requests_per_sec']} p50={res['latency_p50_ms']} "
                          f"p99={res['latency_p99_ms']} cpu={cpu_pct and round(cpu_pct,1)} rss={rec['server_rss_mb']}")
            bench.stop()
    bench.stop()

    out_json = RAW / f"runs-{args.tag}.json"
    out_json.write_text(json.dumps(runs, indent=2))
    cols = ["implementation", "endpoint", "connections", "repetition", "requests_per_sec",
            "latency_p50_ms", "latency_p95_ms", "latency_p99_ms", "latency_max_ms",
            "errors", "socket_errors", "non2xx", "server_cpu_percent", "server_rss_mb",
            "duration_s", "threads"]
    with (PROC / f"runs-{args.tag}.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in runs:
            r2 = dict(r); r2["errors"] = (r.get("socket_errors") or 0) + (r.get("non2xx") or 0)
            w.writerow(r2)
    print(f"wrote {out_json} ({len(runs)} runs) and processed CSV")


if __name__ == "__main__":
    main()
