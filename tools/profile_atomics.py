#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,platform,statistics,subprocess,tempfile,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(description="Compare Strut atomic and mutex counters under equal contention.")
    ap.add_argument("--strut",default="../strut/build/strut")
    ap.add_argument("--runs",type=int,default=10)
    ap.add_argument("--output",default="profiles/results/atomic-mutex.json")
    a=ap.parse_args()
    compiler=Path(a.strut);compiler=compiler if compiler.is_absolute() else (ROOT/compiler).resolve()
    result={"schema_version":1,"hostname":platform.node(),"threads":4,"increments_per_thread":250000,"runs":a.runs,"cases":{}}
    with tempfile.TemporaryDirectory(prefix="strut-atomic-profile-") as temporary:
        temporary=Path(temporary)
        for name in ("atomic_counter","mutex_counter"):
            source=ROOT/"profiles"/"fixtures"/f"{name}.p";binary=temporary/name
            start=time.perf_counter_ns();built=subprocess.run([str(compiler),str(source),"--release","-o",str(binary)],text=True,capture_output=True);compile_ms=(time.perf_counter_ns()-start)/1e6
            if built.returncode:raise SystemExit(built.stderr)
            values=[]
            for _ in range(2):subprocess.run([str(binary)],check=True,stdout=subprocess.DEVNULL)
            for _ in range(a.runs):
                start=time.perf_counter_ns();run=subprocess.run([str(binary)],text=True,capture_output=True);elapsed=(time.perf_counter_ns()-start)/1e6
                if run.returncode or run.stdout!="1000000\n":raise SystemExit(run.stderr or f"unexpected output: {run.stdout!r}")
                values.append(elapsed)
            result["cases"][name]={"compile_ms":compile_ms,"runtime_ms":{"median":statistics.median(values),"runs":values},"binary_bytes":binary.stat().st_size}
    output=ROOT/a.output;output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+"\n");print(output)
if __name__=="__main__":raise SystemExit(main())
