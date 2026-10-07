# R8.5-N — move the buffered request into the callback (last deep copy): KEPT (c=50 +2.0%)

Follow-up to R8.5-M and part of the Rust-gap hypothesis (design note:
REACTOR-rust-gap-design-note.md): with the pump prep copy/copy-back gone (R8.5-M
73d379a), the buffered path still deep-copied the whole request once at the worker
(`req = conn->head.request; conn->fn(req)` - by-value param). R8.5-K tested the same
shape BEFORE the pump copy was removed and was neutral; re-test now that the pump
copy is gone. This removes the LAST full request deep-copy on the buffered path:

    strut_server_request req = std::move(conn->head.request);
    ...
    response = conn->fn(std::move(req));

Head/persistent/framing fields (on strut_http_request_head) are separate from
conn->head.request, which is not read after dispatch on the buffered path; keep-alive
re-parse overwrites head. Behavior identical for the app.

## Correctness
- CTest 16/16; regressions 289/289 default; 289/289 STRUT_HTTP_REACTOR=1.
- Functional battery: 3x keep-alive /plaintext on one conn, /json on same conn, 404,
  duplicate-Host 400, POST->405 — all correct.

## Isolated warmed identity-gated A/B (BASE = 73d379a, CAND = 73d379a+move)
c=50 (wrk -t2 -c50 -d15s, warm 10s, alternating, n=10 each):
| metric        | m_base (73d379a) | n_cand |
|---------------|------------------|--------|
| median rps    | 15420.5          | 15722.8|
| delta         | --               | +2.0%  |
| paired        | 10               | CAND wins 7 (70%) |
c=10 (n=4 usable): median ~+4.7%, 3/4 pairs positive.
c=1: not measured (latency/RTT-dominated, expected flat).

## Mechanism note
Request deep-copy count on the buffered path now 0 (pump+worker+callback all move).
Systematic per-request malloc count vs base was inconclusive on the noisy node in
this session (perf -g symbolization of the candidate trace failed again).

## Decision: KEEP
Committed as da4a8f2 (main head). Buffered request path is now a pure move chain.
Cumulative since 80556b4 (retained): R8.5-M +4.6% + R8.5-N +2.0% at c=50. R8.5-M
certified via 289x2 at 73d379a; R8.5-N certified via 289x2 at the candidate build.

Next: same-session Strut (da4a8f2) vs frozen Go, N>=7.

## Same-session Strut (da4a8f2) vs frozen Go (c=50, N=7 each, alternating, identity-gated)
- Go median 18872.8 (range 17165-20152); Strut median 16368.9 (range 14696-16851).
- **Strut/Go = 86.7%** (up from ~84% at 73d379a post-M vs ~79% at 80556b4).