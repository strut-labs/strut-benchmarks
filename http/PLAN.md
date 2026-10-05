# Strut vs Go vs Rust — Linode HTTP benchmark

An independent **engineering** benchmark comparing Strut's current native HTTP
server stack against mature Go and Rust stacks over a real network on Linode.
This is not a marketing benchmark and not a Warden rewrite. It answers one
question: *how competitive is Strut's native HTTP stack in throughput, latency,
CPU and memory against Go and Rust?*

## Non-goals / rules

- No cherry-picking, no framework-specific heroic tuning, no deliberately weak
  competitors.
- Do not tune Strut for the benchmark. Pin the accepted compiler SHA.
- Do not mix SQLite results into the plaintext/JSON conclusions.
- No localhost-only result presented as network performance.
- Do not modify Strut core. If the benchmark exposes a correctness/runtime
  defect, STOP and report before changing Strut.

## Pinned versions

```
strut compiler : 74d46112310d825ad319bc73b58b4eca1c75e1c7   (strut 0.0.3)
go             : recorded at run time
rust / cargo   : recorded at run time (axum + tokio)
```

## Topology

Two Linodes in the same region:

```
node A (server)     benchmark servers run here (one at a time)
node B (generator)  load generator runs here
```

- Traffic is node B -> node A over the private network (recorded). Loopback
  results are not used.
- Baseline network latency between the nodes is measured before benchmarking.
- Both nodes: `g6-nanode-1` (1 vCPU, 1 GB), Ubuntu 24.04 LTS, same region.
  A swap file is added on the server node for building.

## Endpoints (Phase 1)

Identical semantics in all three implementations.

| Route | Response |
| --- | --- |
| `GET /plaintext` | 200, `text/plain`, body `Hello, World!` |
| `GET /json` | 200, `application/json`, body `{"message":"Hello, World!"}` |

Keep-alive on, HTTP/1.1, TLS off, compression off, logging off/minimal.
Each implementation uses its idiomatic normal path (Go `encoding/json`, Rust
`serde_json`, Strut JSON response helper) — no pre-serialized constant in one
and a serializer in another.

Phase 2 (separate, only after Phase 1 is trustworthy): `GET /db/:id` with a
prepared read-only SQLite query, same schema/data on all three.

## Build modes

- Strut: release (`-O2` generated C++), normal production path.
- Go: `go build` (normal defaults).
- Rust: `cargo build --release`.

Record all toolchain versions.

## Load generator

`wrk` (primary), on node B. Record threads, connections, duration, timeout.
Settings are identical across implementations.

## Matrix

Connections: 1, 10, 50, 100, 250, 500 (adjusted only if the node class makes
part of the range meaningless; retain low / moderate / saturation).

Per (implementation, endpoint, connections):

- warmup: 20 s
- measured: 30 s
- repetitions: >= 5
- report median (+ min/max/MAD)

Alternate implementation order across cycles to reduce ordering bias. Verify
only the target server is running before each trial. One server per run.

## Measurements per run

requests/sec, latency p50/p95/p99 (and max if available), non-2xx/errors,
server-side CPU (process + system), server RSS, plus one-off binary size and
startup time.

## Outputs

- raw: `results/raw/`
- processed CSV/JSON: `results/processed/`
- derived summary tables (never hand-copied)

## Checkpoints

```
B0  repo audit + methodology + infra plan        (this document)
B1  provision/bootstrap two Linodes
B2  three server baselines + parity tests
B3  harness + metrics collection + smoke qualification
B4  plaintext full matrix
B5  JSON full matrix
B6  aggregation / statistical sanity checks
B7  baseline HTTP report
B8  optional profiling of obvious Strut gaps (no optimization)
B9  SQLite benchmark (if warranted)
B10 final report + handover
```

## Security

The Linode API token lives in the local shell environment (sourced from
`~/.bashrc`). It is never printed, logged, committed, or copied to a node.
Benchmark scripts that run on the Linodes require no Linode API token.
