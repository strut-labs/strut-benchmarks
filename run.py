#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, datetime as dt, json, os, platform, re, shutil, statistics, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / "benchmarks.json").read_text())
EXT = {"strut":"p","cpp":"cpp","rust":"rs","go":"go"}
ORDER = ["strut","cpp","rust","go"]
TOKEN_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|::|:=|->|=>|==|!=|<=|>=|\+\+|--|<<|>>|&&|\|\||[^\s]')

def command_version(cmd):
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
        return (p.stdout or "").strip().splitlines()[0] if p.stdout else ""
    except Exception:
        return ""

def detect_tools(strut_arg):
    def which_or_path(v):
        if not v: return None
        p=Path(v)
        if p.exists(): return str(p.resolve())
        return shutil.which(v)
    return {
        "strut": which_or_path(strut_arg) or shutil.which("strut"),
        "cpp": shutil.which(os.environ.get("CXX","g++")) or shutil.which("clang++"),
        "rust": shutil.which("rustc"),
        "go": shutil.which("go"),
    }

def machine_info(tools):
    cpu=""
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                cpu=line.split(":",1)[1].strip(); break
    except Exception:
        pass
    versions={}
    if tools.get("strut"): versions["strut"]=command_version([tools["strut"],"--version"])
    if tools.get("cpp"): versions["cpp"]=command_version([tools["cpp"],"--version"])
    if tools.get("rust"): versions["rust"]=command_version([tools["rust"],"--version"])
    if tools.get("go"): versions["go"]=command_version([tools["go"],"version"])
    return {
        "timestamp_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "hostname":platform.node(),
        "platform":platform.platform(),
        "machine":platform.machine(),
        "processor":platform.processor(),
        "cpu":cpu,
        "python":platform.python_version(),
        "toolchains":versions,
    }

def source_path(lang,task):
    return ROOT/"benchmarks"/lang/f"{task}.{EXT[lang]}"

def compile_cmd(lang, tool, src, out):
    if lang=="strut": return [tool,str(src),"--release","-o",str(out)]
    if lang=="cpp": return [tool,"-std=c++20","-O2","-DNDEBUG","-pthread","-s",str(src),"-o",str(out)]
    if lang=="rust": return [tool,"-C","opt-level=2","-C","strip=symbols",str(src),"-o",str(out)]
    if lang=="go": return [tool,"build","-ldflags=-s -w","-o",str(out),str(src)]
    raise ValueError(lang)

def run_compile(cmd, cwd):
    start=time.perf_counter_ns()
    p=subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    elapsed=(time.perf_counter_ns()-start)/1e6
    return p,elapsed

def parse_gnu_time(stderr):
    m=re.search(r"__STRUT_BENCH_TIME__\s+([0-9.]+)\s+([0-9]+)",stderr)
    if not m: return None,None
    return float(m.group(1))*1000.0,int(m.group(2))

def execute(binary, timeout=120):
    start=time.perf_counter_ns()
    p=subprocess.run([str(binary)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout)
    wall=(time.perf_counter_ns()-start)/1e6
    return p.returncode,p.stdout,p.stderr,wall

def measure_rss(binary, timeout=120):
    gtime=Path("/usr/bin/time")
    is_gnu_time = gtime.exists() and "GNU" in command_version([str(gtime),"--version"])
    if not is_gnu_time:
        return None
    p=subprocess.run([str(gtime),"-f","__STRUT_BENCH_RSS__ %M",str(binary)],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout)
    if p.returncode:
        return None
    m=re.search(r"__STRUT_BENCH_RSS__\s+([0-9]+)",p.stderr)
    return int(m.group(1)) if m else None

def verbosity(path):
    text=path.read_text()
    lines=text.splitlines()
    return {
        "bytes":len(text.encode()),
        "lines":len(lines),
        "nonblank_lines":sum(1 for x in lines if x.strip()),
        "tokens":len(TOKEN_RE.findall(text)),
    }

def median(xs):
    return statistics.median(xs) if xs else None

def bench_one(lang,task,tool,args,build_dir):
    src=source_path(lang,task)
    out=build_dir/lang/task
    out.parent.mkdir(parents=True,exist_ok=True)
    compile_times=[]
    cmd=compile_cmd(lang,tool,src,out)
    p,_=run_compile(cmd,ROOT)
    if p.returncode:
        return {"status":"compile_error","stderr":p.stderr,"compile_command":cmd}
    for _ in range(args.compile_runs):
        out.unlink(missing_ok=True)
        p,ms=run_compile(cmd,ROOT)
        if p.returncode:
            return {"status":"compile_error","stderr":p.stderr,"compile_command":cmd}
        compile_times.append(ms)
    expected=MANIFEST["tasks"][task]["expected_stdout"]
    rc,stdout,stderr,_=execute(out)
    if rc!=0 or stdout!=expected:
        return {"status":"wrong_output","exit_code":rc,"stdout":stdout,"stderr":stderr,
                "expected_stdout":expected,"compile_command":cmd}
    for _ in range(args.warmup_runs):
        rc,stdout,stderr,_=execute(out)
        if rc!=0 or stdout!=expected:
            return {"status":"runtime_error","exit_code":rc,"stdout":stdout,"stderr":stderr}
    runtime_ms=[]; rss=[]
    for _ in range(args.runtime_runs):
        rc,stdout,stderr,ms=execute(out)
        if rc!=0 or stdout!=expected:
            return {"status":"runtime_error","exit_code":rc,"stdout":stdout,"stderr":stderr}
        if ms is not None: runtime_ms.append(ms)
    for _ in range(args.memory_runs):
        kib=measure_rss(out)
        if kib is not None: rss.append(kib)
    return {
        "status":"ok",
        "compile_command":cmd,
        "compile_ms":{"median":median(compile_times),"min":min(compile_times),"max":max(compile_times),"runs":compile_times},
        "runtime_ms":{"median":median(runtime_ms),"min":min(runtime_ms) if runtime_ms else None,"max":max(runtime_ms) if runtime_ms else None,"runs":runtime_ms},
        "max_rss_kib":{"median":median(rss),"min":min(rss) if rss else None,"max":max(rss) if rss else None,"runs":rss},
        "binary_bytes":out.stat().st_size,
        "verbosity":verbosity(src),
    }

def write_outputs(result,outdir):
    outdir.mkdir(parents=True,exist_ok=True)
    stamp=dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path=outdir/f"results-{stamp}.json"
    json_path.write_text(json.dumps(result,indent=2)+"\n")
    rows=[]
    for task,tdata in result["results"].items():
        for lang,d in tdata.items():
            row={"task":task,"language":lang,"status":d.get("status")}
            if d.get("status")=="ok":
                row.update({
                    "compile_ms":d["compile_ms"]["median"],
                    "runtime_ms":d["runtime_ms"]["median"],
                    "max_rss_kib":d["max_rss_kib"]["median"],
                    "binary_bytes":d["binary_bytes"],
                    "source_bytes":d["verbosity"]["bytes"],
                    "nonblank_lines":d["verbosity"]["nonblank_lines"],
                    "tokens":d["verbosity"]["tokens"],
                })
            rows.append(row)
    csv_path=outdir/f"results-{stamp}.csv"
    fields=["task","language","status","compile_ms","runtime_ms","max_rss_kib","binary_bytes","source_bytes","nonblank_lines","tokens"]
    with csv_path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    md_path=outdir/f"results-{stamp}.md"
    def fmt(v,places=2):
        if v is None:return "—"
        if isinstance(v,float):return f"{v:.{places}f}"
        return f"{v:,}" if isinstance(v,int) else str(v)
    lines=["# Strut benchmark results","",f"Generated: `{result['environment']['timestamp_utc']}`","",
           "## Environment","",f"- Platform: `{result['environment']['platform']}`",f"- CPU: `{result['environment']['cpu'] or result['environment']['processor']}`",""]
    for task in result["results"]:
        lines += [f"## {task}","", "| Language | Runtime ms | RSS KiB | Binary bytes | Compile ms | LOC | Tokens |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for lang in ORDER:
            d=result["results"][task].get(lang)
            if not d: continue
            if d.get("status")!="ok":
                lines.append(f"| {lang} | {d.get('status')} | — | — | — | — | — |")
            else:
                lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(
                    lang,fmt(d["runtime_ms"]["median"]),fmt(d["max_rss_kib"]["median"]),
                    fmt(d["binary_bytes"]),fmt(d["compile_ms"]["median"]),
                    fmt(d["verbosity"]["nonblank_lines"]),fmt(d["verbosity"]["tokens"])))
        lines.append("")
    md_path.write_text("\n".join(lines)+"\n")
    for src,name in [(json_path,"latest.json"),(csv_path,"latest.csv"),(md_path,"latest.md")]:
        shutil.copyfile(src,outdir/name)
    return json_path,csv_path,md_path

def main():
    ap=argparse.ArgumentParser(description="Benchmark equivalent Strut/C++/Rust/Go programs.")
    ap.add_argument("--strut",default=os.environ.get("STRUT_BIN","../strut/build/strut"),help="Strut compiler path (or STRUT_BIN).")
    ap.add_argument("--languages",default="strut,cpp,rust,go")
    ap.add_argument("--tasks",default=",".join(MANIFEST["tasks"].keys()))
    ap.add_argument("--compile-runs",type=int,default=3)
    ap.add_argument("--runtime-runs",type=int,default=10)
    ap.add_argument("--memory-runs",type=int,default=3)
    ap.add_argument("--warmup-runs",type=int,default=2)
    ap.add_argument("--quick",action="store_true",help="Use 1 compile, 3 runtime and 1 warmup run.")
    ap.add_argument("--require-all",action="store_true",help="Fail if a requested toolchain is unavailable.")
    ap.add_argument("--output",default="results")
    args=ap.parse_args()
    if args.quick:
        args.compile_runs,args.runtime_runs,args.memory_runs,args.warmup_runs=1,3,1,1
    langs=[x.strip() for x in args.languages.split(",") if x.strip()]
    tasks=[x.strip() for x in args.tasks.split(",") if x.strip()]
    bad=[x for x in langs if x not in ORDER]
    if bad: ap.error("unknown languages: "+", ".join(bad))
    bad=[x for x in tasks if x not in MANIFEST["tasks"]]
    if bad: ap.error("unknown tasks: "+", ".join(bad))
    tools=detect_tools(args.strut)
    missing=[x for x in langs if not tools.get(x)]
    if missing and args.require_all:
        print("missing toolchains: "+", ".join(missing),file=sys.stderr); return 2
    if missing:
        print("Skipping unavailable toolchains: "+", ".join(missing),file=sys.stderr)
        langs=[x for x in langs if tools.get(x)]
    if not langs:
        print("No requested toolchains available.",file=sys.stderr); return 2
    result={"schema_version":1,"environment":machine_info(tools),"config":{
        "languages":langs,"tasks":tasks,"compile_runs":args.compile_runs,
        "runtime_runs":args.runtime_runs,"memory_runs":args.memory_runs,"warmup_runs":args.warmup_runs},
        "benchmarks":MANIFEST["tasks"],"results":{}}
    build_dir=ROOT/"build"
    build_dir.mkdir(exist_ok=True)
    failed=False
    for task in tasks:
        print(f"\n[{task}]")
        result["results"][task]={}
        for lang in langs:
            print(f"  {lang}...",end="",flush=True)
            d=bench_one(lang,task,tools[lang],args,build_dir)
            result["results"][task][lang]=d
            print(" "+d["status"])
            failed |= d["status"]!="ok"
    paths=write_outputs(result,ROOT/args.output)
    print("\nWrote:")
    for p in paths: print(" ",p)
    return 1 if failed else 0

if __name__=="__main__":
    raise SystemExit(main())
