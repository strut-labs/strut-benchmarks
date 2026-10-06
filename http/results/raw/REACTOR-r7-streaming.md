# R7 — streaming responses on the reactor (bounded adapter + stream-worker pool)

Date/node: single vCPU `strutbench-a`; load `strutbench-b`. Mixed server:
`/plaintext`, `/json` (buffered) + `/bigstream` (a ~6 MiB chunked stream route).

## Design
- Streaming routes now run on the reactor path (no whole-server legacy
  fallback); buffered and streaming coexist.
- `response_writer` output feeds a bounded per-connection queue (1 MiB) drained
  by the reactor on socket writable readiness. Producer backpressure blocks the
  stream worker on queue capacity, never the reactor.
- A separate bounded stream-worker pool (default max(4, parallelism), cap 16)
  keeps slow/long-lived streams from occupying the CPU-sized app worker pool.

## Results (STRUT_HTTP_REACTOR=1)

| scenario | buffered /plaintext c=50 |
|---|---|
| no streams | 16814 rps |
| one stalled /bigstream reader (read 4 KiB then stopped) | 15450 rps |
| three stalled /bigstream readers simultaneously | 15414 rps |

Threads fixed at 6 (reactor + 1 app worker + 4 stream workers); RSS ~5 MB.
A slow stream receiver consumes queue capacity and a stream worker, not the app
worker: ordinary traffic keeps making progress.

## Coverage
Streaming response surface (stream routes, NDJSON, serve_file, SSE-style) is
reactor-native with bounded memory. request_stream request-body streaming and
WebSocket still use the legacy path (documented transitional; targeted in the
next checkpoint). Buffered perf unchanged from R6.5.
