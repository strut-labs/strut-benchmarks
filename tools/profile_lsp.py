#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,platform,statistics,subprocess,tempfile,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE="""function identity[T](T value) -> T { return value; }
function helper(int value) -> int { return value + 1; }
function main() -> int : HttpError {
    values := [1, 2, 3];
    doubled := values.map((int value) => helper(value));
    response := http_get("https://example.test");
    identity(doubled);
    return response.status;
}
"""

def frame(message):
    body=json.dumps(message,separators=(",",":")).encode()
    return b"Content-Length: "+str(len(body)).encode()+b"\r\n\r\n"+body

def read_message(stream):
    headers={}
    while True:
        line=stream.readline()
        if not line:raise EOFError("LSP server closed stdout")
        if line in (b"\r\n",b"\n"):break
        key,value=line.decode().split(":",1);headers[key.lower()]=value.strip()
    return json.loads(stream.read(int(headers["content-length"])))

def timed_request(proc,identifier,method,params):
    start=time.perf_counter_ns();proc.stdin.write(frame({"jsonrpc":"2.0","id":identifier,"method":method,"params":params}));proc.stdin.flush()
    while True:
        message=read_message(proc.stdout)
        if message.get("id")==identifier:return (time.perf_counter_ns()-start)/1e6,message

def main():
    ap=argparse.ArgumentParser(description="Measure Strut LSP request latency over the real stdio transport.")
    ap.add_argument("--strut",default="../strut/build/strut");ap.add_argument("--runs",type=int,default=10);ap.add_argument("--output",default="profiles/results/lsp-latency.json");a=ap.parse_args()
    compiler=Path(a.strut);compiler=compiler if compiler.is_absolute() else (ROOT/compiler).resolve();samples={name:[] for name in ("startup_initialize","did_open_diagnostics","completion","hover","signature_help","definition","did_change_diagnostics")}
    with tempfile.TemporaryDirectory(prefix="strut-lsp-profile-") as temporary:
        uri=(Path(temporary)/"main.p").as_uri()
        for run in range(a.runs):
            started=time.perf_counter_ns();proc=subprocess.Popen([str(compiler),"lsp"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            elapsed,_=timed_request(proc,1,"initialize",{});samples["startup_initialize"].append((time.perf_counter_ns()-started)/1e6)
            opened=time.perf_counter_ns();proc.stdin.write(frame({"jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{"uri":uri,"text":SOURCE}}}));proc.stdin.flush();message=read_message(proc.stdout);samples["did_open_diagnostics"].append((time.perf_counter_ns()-opened)/1e6)
            if message.get("method")!="textDocument/publishDiagnostics":raise SystemExit(f"unexpected didOpen response: {message}")
            params=lambda line,char:{"textDocument":{"uri":uri},"position":{"line":line,"character":char}}
            samples["completion"].append(timed_request(proc,2,"textDocument/completion",params(4,28))[0])
            samples["hover"].append(timed_request(proc,3,"textDocument/hover",params(5,17))[0])
            samples["signature_help"].append(timed_request(proc,4,"textDocument/signatureHelp",params(5,24))[0])
            samples["definition"].append(timed_request(proc,5,"textDocument/definition",params(4,48))[0])
            changed=SOURCE.replace("return response.status;","return missing_name;")
            start=time.perf_counter_ns();proc.stdin.write(frame({"jsonrpc":"2.0","method":"textDocument/didChange","params":{"textDocument":{"uri":uri,"version":2},"contentChanges":[{"text":changed}]}}));proc.stdin.flush();message=read_message(proc.stdout);samples["did_change_diagnostics"].append((time.perf_counter_ns()-start)/1e6)
            timed_request(proc,6,"shutdown",{});proc.stdin.write(frame({"jsonrpc":"2.0","method":"exit","params":{}}));proc.stdin.flush();proc.communicate(timeout=5)
            if proc.returncode!=0:raise SystemExit(proc.stderr.read().decode(errors="replace"))
    result={"schema_version":1,"hostname":platform.node(),"runs":a.runs,"latency_ms":{name:{"median":statistics.median(values),"runs":values} for name,values in samples.items()}}
    output=ROOT/a.output;output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+"\n");print(output)
if __name__=="__main__":raise SystemExit(main())
