# R8.5-W — reactor<->app-worker handoff upper-bound diagnostic: +6.7% (not the Rust gap)

Question: is the separate reactor / app-worker handoff the major remaining architectural
gap (candidate explanation for ~2x vs Rust)?

Diagnostic candidate (NOT production, NOT retained): for the ORDINARY buffered
synchronous path only, the reactor executes the already-selected callback inline
(`conn->fn`) + `reactor_build_response` + arm write, bypassing the ready-queue push,
`work_cv` notify, worker sleep/wake, completion queue, and eventfd wake. Streams /
request_stream / WebSocket / async stay on the existing machinery. No public API change.

Correctness (local): /plaintext 200, /json 200, 404, 3x keep-alive on one connection all
correct. (Full suite intentionally not run -- inline callbacks are not production-safe, so
W is a diagnostic, not a candidate for retention.)

## Canonical A/B (c=50, alternating, identity-gated, N=7/7)
| round | base 0e95d0d | W (inline) |
|-------|--------------|------------|
| 1     | 16432        | 17911      |
| 2     | 17164        | 18789      |
| 3     | 17297        | 18414      |
| 4     | 17324        | 17558      |
| 5     | 15840        | 16814      |
| 6     | 16823        | 18763      |
| 7     | 16766        | 17945      |
| median| 16823        | 17945      |
delta +6.7%, W wins 7/7.

## Interpretation
The reactor<->worker handoff costs at most ~+6.7% on canonical /plaintext (upper bound:
inline also removes completion/eventfd and runs the callback while the reactor is hot).
This is a real but MODEST single-digit effect -- NOT a large double-digit layer. It does
not come close to explaining the ~2x Rust gap (Strut ~17-18k vs Rust >=35k).
=> The handoff is not the major missing architectural layer.

## Decision
Accept R8.5 exit criterion B: the handoff experiment shows only a small upper bound; the
obvious high-value architectural layers are exhausted; remaining work (a production-safe
inline/offload scheduler hybrid) would be invasive for at most ~a few % (safe subset of
the 6.7% upper bound). Current same-session control: Strut ~mid/high-80%s of frozen Go
(healthy sessions; Go ~19-20k, Rust >=35k generator-limited). Document and move on.

Note: the 6.7% upper bound is NOT retained (inline callbacks on the reactor would stall on
blocking/CPU-heavy user callbacks); no production change made.