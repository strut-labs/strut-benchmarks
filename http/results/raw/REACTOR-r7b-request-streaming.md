# R7b — request_stream on the reactor (memory-bounded) + buffered gate

Note: this now continues to 2026-10-06. request_stream routes run on the
reactor path (no whole-server legacy fallback); the reactor accumulates the
request body under max_body_bytes (reactor-owned nonblocking reads; slow
uploaders occupy no worker) and the stream handler runs on the bounded
stream-worker pool; Content-Length and chunked decode through the existing
request_body machinery; release() preserves pipelined leftover.

## Buffered regression gate (same 1-vCPU node, STRUT_HTTP_REACTOR=1)

| path | c | RPS |
|---|---|---|
| /plaintext | 1  | ~3.8k–4.8k |
| /plaintext | 10 | ~11.8k |
| /plaintext | 50 | ~15.6k–16.6k (run variance; 16.0k typical) |
| /json      | 50 | ~14.5k |

c=50 plaintext remains ~16k, within session run-to-run variance of the R6.5
baseline (~16.1–17.5k); the buffered dispatch path is unchanged by R7b.

## Coverage
request-body streaming (CL + chunked) and response streaming are reactor-native
and memory-bounded. Remaining non-reactor surfaces: WebSocket (bounded
long-lived pool plan, targeted next) and TLS (R8).

## Ledger
- original ~1.2k -> TCP_NODELAY ~9k -> reactor ~11–12k -> +writev ~16.8k
- R7a streaming coexists at ~16.8k; R7b request streaming at ~16k (variance)
