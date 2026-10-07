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

## Mechanism re-measurement (NOT authoritative per-request)
Follow-up tracing used a 5 s perf window that overlapped only PART of the 12 s wrk
interval, so comparing samples against the full wrk request count does NOT establish a
precise per-request malloc delta. The follow-up tracing did not show an obvious large
reduction, but the "mallocs/request unchanged" claim is withdrawn.

## Interpretation / implication (hypothesis only)
One move-elision not moving throughput does NOT prove scheduler/preemption is the
binding constraint. The emitted runtime still contains other `strut_server_request`
copy sites earlier in the reactor path and in the stream/websocket workers, so this
candidate did NOT remove the whole header-copy chain. The pattern of flat results
(R8.5-G parse cleanup, R8.5-I pending-wake, this move) is consistent with, but does
not establish, a scheduler/preemption + syscall-churn hypothesis (recv ~1.92, writev
~0.96, eventfd ~0.96, futex ~1.34 per request; reactor involuntary csw ~0.44/request).
That remains a hypothesis to be tested by a retained throughput win, not a proven
constraint.

## State
Compiler retained at 80556b4. Nothing from R8.5-K retained. Both repos clean; node A
stopped. Evidence ledger: R8.5-H 90cb0e6, R8.5-I 73c4a14, R8.5-J 4d7b991 (wording
fix), R8.5-K attribution 6574a6c, this file follows.