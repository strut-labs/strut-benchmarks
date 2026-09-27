#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,platform,statistics,subprocess,tempfile,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def source_for(count:int)->str:
    declarations=[]
    for i in range(count):
        declarations.append(f"function identity_{i}[T](T value) -> T {{ return value; }}")
    body=["function main() -> int {"]
    for i in range(count):
        body.append(f"    int[][] nested_{i} := identity_{i}([[{i}], []]);")
    body.extend(["    int* owner := identity_0(new(1));","    int[] empty := identity_0([]);","    return *owner + empty.length;","}"])
    return "\n".join(declarations+body)+"\n"

def main():
    ap=argparse.ArgumentParser(description="Measure contextual generic-inference frontend scaling.")
    ap.add_argument("--strut",default="../strut/build/strut")
    ap.add_argument("--sizes",default="10,50,100,250,500")
    ap.add_argument("--runs",type=int,default=10)
    ap.add_argument("--output",default="profiles/results/generic-scaling.json")
    a=ap.parse_args();compiler=Path(a.strut);compiler=compiler if compiler.is_absolute() else (ROOT/compiler).resolve()
    out={"schema_version":1,"hostname":platform.node(),"runs":a.runs,"mode":"strut --check (load, parse, semantic analysis and IR validation; excludes native backend)","sizes":{}}
    with tempfile.TemporaryDirectory(prefix="strut-generics-") as temporary:
        temporary=Path(temporary)
        for count in map(int,a.sizes.split(",")):
            source=temporary/f"generic-{count}.p";source.write_text(source_for(count));values=[]
            for _ in range(a.runs):
                start=time.perf_counter_ns();run=subprocess.run([str(compiler),str(source),"--check"],text=True,capture_output=True);elapsed=(time.perf_counter_ns()-start)/1e6
                if run.returncode:raise SystemExit(run.stderr)
                values.append(elapsed)
            out["sizes"][str(count)]={"source_bytes":source.stat().st_size,"median_ms":statistics.median(values),"runs":values}
    path=ROOT/a.output;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2)+"\n");print(path)
if __name__=="__main__":raise SystemExit(main())
