# R8.5-K candidate — request deep-copy move-elision: A/B NEUTRAL -> REVERTED

Candidate from the R8.5-K malloc call-site attribution (see
REACTOR-r85k-alloc-attribution.md): largest single source was the buffered
app-worker handoff deep-copying `conn->head.request` (21.3% of malloc samples) plus
the `conn->fn(req)` by-value parameter copy (~3.6%). Both elided by moving:

    strut_server_request req = std::move(conn->head.request);
    ...
    try{ response = conn->fn(std::move(req)); }

Buffered path only; conn->head.version/persistent/framing are separate fields and the
moved-from conn->head.request is not read after dispatch. Stream/websocket paths
untouched. Verified present in the emitted program
(`req=std::move(conn->head.request)` / `conn->fn(std::move(req))`).

## Correctness (candidate)
- CTest 16/16 on the candidate build.
- Local functional parity vs BASE: /plaintext 200+body, /json 200, large request
  header 200, duplicate-Host 400; Content-Length values unchanged.

## Isolated warmed A/B (Linode, STRUT_HTTP_REACTOR=1, wrk -t2 -c50 -d15s, identity-gated)

| round | strut_base rps | strut_k_cand rps |
|-------|----------------|------------------|
| 1     | 15483.29       | 15949.07         |
| 2     | 15694.63       | 14816.73         |
| 3     | 14732.11       | 15332.14         |
| 4     | 15872.67       | 14379.11         |
| 5     | 15643.23       | 15435.01         |
| median| 15643.23       | 15332.14         |

Median CAND/BASE ~= -2.0%; ranges overlap (14732-15872 vs 14379-15949).
**No measurable win -> REVERTED**, not committed.

## Mechanism re-measurement
perf uprobe `probe_libc:malloc`, 5 s windows, identical methodology for both:
- strut_base: 395,514 samples @ rps 11,553 -> ~6.85 samples/request
- strut_k_cand: 339,784 samples @ rps 9,855 -> ~6.89 samples/request

Parity, so the traced malloc population (subset of the ~29/request interposer
baseline, ~1/4 of it) did not shrink per request despite the move being present.
Notable: 1-vCPU rps oscillated (9.8-15.9k across windows) so per-request sample
comparisons are coarse.

## Interpretation / implication
Same conclusion as R8.5-G, R8.5-H, R8.5-I: removing sizable user-space allocation +
copy work (up to ~25% of requested allocations/request) does not move saturated
throughput on the 1-vCPU box. Combined evidence stack: reactor involuntary csw
~0.44/request + flush/parse wall >> CPU + flat wake/parse/copy experiments imply the
binding constraint is scheduler/preemption and syscall churn (recv ~1.92, writev
~0.96, eventfd ~0.96, futex ~1.34 per request), not user-space CPU or allocation
volume. R8.5-E (serializer) remains the exception that proved removal matters only
when the removed work is a large share of the CPU-limited loop.

## State
Compiler retained at 80556b4. Nothing from R8.5-K retained. Both repos clean; node A
stopped. Evidence ledger: R8.5-H 90cb0e6, R8.5-I 73c4a14, R8.5-J 4d7b991 (wording
fix), R8.5-K attribution 6574a6c, this file follows.