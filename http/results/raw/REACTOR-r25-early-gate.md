# Early architecture-validation gate — reactor path (R2–R5)

Date/node: single vCPU `strutbench-a` (id 107498466, 96.126.107.155),
`g6-nanode-1`, Ubuntu 24.04. Load from `strutbench-b` (96.126.107.181).
Compiler: current HEAD (reactor R2–R5). Strut server built from
`strut/server.p`; run with `STRUT_HTTP_REACTOR=1` (env-gated; legacy path is
the default until hardening).

## Thread count

| state | threads |
|---|---|
| idle (no connections) | 2 (1 reactor + 1 app worker) |
| during c=10 | 2 |
| during c=50 | 2 |
| c=1 | 2 |

Independent of connection count. (Old thread-per-connection: 51 at c=50.)

## Throughput / CPU / per-request cost

| path | c | RPS | CPU (% of 1 vCPU) | per-request CPU |
|---|---|---|---|---|
| /plaintext | 1  | ~4289  | —      | — |
| /plaintext | 10 | ~10782 | ~35%   | ~32 us |
| /plaintext | 50 | ~11451 | ~43%   | ~37 us |
| /json      | 10 | ~9518  | ~37%   | ~39 us |
| /json      | 50 | ~11039 | ~37%   | ~33 us |

Old (thread-per-connection) reference: c=1 ~5012 rps / ~80 us per request;
c=50 ~9023 rps / ~106 us per request (CPU 95.7%).

The key metric: per-request CPU **no longer inflates with concurrency**.
c=50 is ~37 us, below the old c=1 cost (~80 us) and roughly at Go's c=50
per-request cost (~39 us). The concurrency inflation (80 -> 106 us) is gone.

c=1 RPS is modestly lower than the legacy path (~4289 vs ~5012): a thread-hop
per request. This is the expected target of the later per-request/transport
pass (R13), not a reason to keep the legacy path.

## Slow-client isolation (this is the R0 amendment, proven)

On the 1-vCPU node with exactly ONE application worker:

- A connection that sent `GET /pla` (partial header) and then stalled was open
  while wrk ran: **11838 RPS**, no errors. The incomplete-request reader does
  not occupy the app worker.
- A connection that requested `/plaintext` and read only the response headers,
  then stopped reading (stalled receiver), was open while wrk ran:
  **11670 RPS**, zero socket errors. A slow receiver consumes no app worker.

Both cases confirm ordinary transport waits are reactor-owned.

## Preserved semantics (reactor path)

- keep-alive reuse (many requests per connection)
- pipelined requests (3 sent in one write -> 3 correct responses)
- Content-Length and chunked request bodies decoded correctly
- HEAD (200, empty body), HTTP/1.0, 405 method mismatch
- idle timeout closes idle keep-alive; read timeout closes a slow header
- RSS ~4.5 MB

## Legacy path

Untouched; all 16 unit suites still pass; legacy behavior unchanged when
`STRUT_HTTP_REACTOR` is unset.

## Gate verdict

HEALTHY. Thread count independent of c; concurrency per-request CPU inflation
removed; slow readers/writers do not starve the sole app worker; no latency
regression (c=50 avg latency ~4.6 ms vs old ~5.3 ms); memory sane.
Proceeding to R6+.

Go/Rust remain frozen; current Rust ~35k remains generator-limited (wrk
saturates ~37k). Generator headroom work deferred to R14.