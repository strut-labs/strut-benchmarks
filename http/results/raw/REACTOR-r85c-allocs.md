# R8.5-C — corrected authoritative allocation baseline (Strut)

Methodology: atomic-counter malloc/calloc/realloc/free interposer
(__atomic_fetch_add, no locks), server warmed first, counters snapshot/reset
right before a foreground 8s wrk run, and the EXACT completed request count from
that wrk invocation used as the denominator (delta over the same window).

Certified R8 compiler (417e197), STRUT_HTTP_REACTOR=1, 1-vCPU node:

| workload | exact reqs | rps | allocs/request | bytes/request |
|---|---|---|---|---|
| /plaintext c=1  | 32,386  | 4,042  | ~34   | ~3,686 |
| /plaintext c=50 | 119,621 | 14,803 | ~29   | ~2,210 |
| /json c=50     | 117,277 | 14,551 | ~32   | ~2,605 |

(calloc/realloc ~0; malloc==free live-balanced.)

Earlier ~12-14/req estimate was invalid (racy volatile counters + startup/warmup
contamination); the corrected delta-over-exact-request-window numbers above are
the authoritative per-request allocation baseline for R8.5.

## Concurrency vs inherent
c=1 (~34/req) > c=50 (~29/req): concurrency amortizes some worker/queue cost;
inherent request construction alone is ~34 alloc required.c JSON adds ~400
bytes/req over plaintext (serialization).

## Go/Rust comparison — NOT measured (limitation)
- Go: GC-managed runtime allocator (not libc malloc), so a libc-malloc
  interposer is not a valid comparison; requires a Go-appropriate tool.
- Rust control: the same interposer did not produce reliable output under the
  tokio runtime in this environment (no live dump produced with either
  signal- or periodic-thread delivery), and the control measured ~21k rps.
  Rather than risk a synthetic ratio, the cross-language allocation comparison
  is intentionally left unclaimed until an equivalent tool is available.
  The Strut-only numbers above are authoritative for guiding R8.5.

## Next
Attribute the ~29-34 allocs/req by call-site (perf-sampled malloc stacks or
scoped counters), then attack the largest clean source (candidates: per-request
cancellation-source make_shared, static-route params map, header unordered_map,
lowercase strings, substr copies, response serialization).
