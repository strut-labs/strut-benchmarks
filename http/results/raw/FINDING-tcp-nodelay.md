# FINDING (B8, pre-matrix): Strut HTTP server misses `TCP_NODELAY`

Status: **STOP — genuine Strut runtime defect. Strut core NOT modified.**

## Summary

Strut's HTTP server does not disable Nagle's algorithm (`TCP_NODELAY`) on
accepted sockets, and writes the buffered response head and body as separate
sends. On a persistent (keep-alive) connection the client's delayed ACK then
stalls each subsequent small write by ~40 ms, collapsing throughput.

Go's `net/http` and Rust's axum/hyper set `TCP_NODELAY` on accepted sockets, so
they do not exhibit the stall.

## Evidence

1. Source: `grep -rn TCP_NODELAY src/` in the Strut compiler returns nothing.
   `strut_tcp_socket::accept()` configures blocking mode but leaves Nagle on.

2. Sequential requests on one keep-alive connection, node B -> node A
   (`curl -w '%{time_total}'`, same-region RTT p50 ~0.15 ms):

   ```
   request 1 (fresh connection):  0.00166 s
   request 2 (reused):            0.04135 s
   request 3 (reused):            0.04158 s
   request 4 (reused):            0.04066 s
   request 5 (reused):            0.04074 s
   ```

   With `Connection: close` each request is ~0.001 s (fresh socket, no unacked
   data -> Nagle does not stall).

3. `wrk` smoke (c=50, 15 s measure, node B -> node A):

   | impl  | req/s   | p50    | p99    | server CPU | RSS    |
   |-------|---------|--------|--------|------------|--------|
   | strut | ~1200   | 41 ms  | 52 ms  | 11%        | 5.5 MB |
   | go    | ~26100  | 1.9 ms | 4.0 ms | 96%        | 12.5MB |
   | rust  | ~35500  | 1.3 ms | 4.8 ms | 90%        | 4.4 MB |

   Strut is ~20x slower while using only ~11% of the single core — i.e. blocked,
   not compute-bound, exactly the delayed-ACK signature.

## Mechanism

`strut_http_json_response` / text responses serialize the head and then the body
and send them with two small `send` calls. On a reused connection the previous
response's tail may still be unacknowledged, so Nagle holds the next small write;
Linux's delayed ACK timer (~40 ms) releases it. Fresh connections use quick ACK
and are fast, which is why the first request is fine and all reused requests
stall.

## Recommendation (not applied)

Set `TCP_NODELAY` on accepted HTTP server sockets (and likely on `tcp_connect`
client sockets and PTY/process pipes) once, at accept/connect time. This is a
one-line `setsockopt(..., IPPROTO_TCP, TCP_NODELAY, ...)`. Re-run the benchmark
afterward; expect Strut to move into the same order of magnitude as Go/Rust.

Do **not** change the benchmark methodology to hide this; the plaintext endpoint
is byte-identical and the gap is an unambiguous server-side defect.
