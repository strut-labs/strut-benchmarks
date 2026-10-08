# R8.5 FINAL REPORT — Linux HTTP/reactor hot-path performance campaign

Compiler retained: **0e95d0d** (0.0.3 line; all retained work below is in main ancestry).

## Retained wins (in order)
| commit | change | canonical effect |
|--------|--------|------------------|
| 0e86e14 | R6.5 vectored write / writev | large (early) |
| 87e00ff+80556b4 | R8.5-E response-head serializer (no ostringstream) + bounded reserve | **+8.4% c=50** (7/7) |
| 73d379a | R8.5-M route directly on connection-owned request (drop pump copy/copy-back) | **+4.6% c=50** (7/10) |
| da4a8f2 | R8.5-N move buffered request into callback (drop last deep copy) | +2.0% c=50 (7/10) |
| 51771f9 | R8.5-O direct/range-guided request-head construction (drop fields vector + temporaries) | +1.6% canonical; **+22.6% @ 8-extra-header** (5/5) |
| 56ea341 | R8.5-Q order-preserving indexed router (exact index + param trie + ordinals) | N=1000 exact-last **x2.5**, param x2.8, miss +37%; N=1 neutral; N=100 +3% |
| 5c647bf+a08fea5 | R8.5-R specialized flat `strut_http_headers` (+ equality/assign fix-forward) | **+3.4% c=50** (6/6); +7.1% @ 8-extra-header (5/5) |
| 0e95d0d | R8.5-T null-safe default cancellation_token placeholder | ~0-2% c=50 (mechanism: 1 eager alloc removed/request) |

Structural/scaling fixes retained: route matcher cleanup (beed5ba), R6.5 writev.

## Rejected/negative (reverted, evidence banked)
R8.5-A (incorrect empty->nonempty wake), R8.5-B (read-once neutral), R8.5-G (parser
copy/temp cleanup neutral), R8.5-I (pending-wake batching neutral), R8.5-K (worker request
move neutral pre-M), R8.5-L (cached reactor clock: mechanism -92% but neutral), R8.5-P
compiled-segment router (linear, +2%, reverted), R8.5-V (stable header backing: poor
canonical payoff/SSO, parked), R8.5-X (worker-direct completion arm: **-10.5%**, reverted).

## Diagnostics (not retained)
R8.5-F scoped phase attribution (parse/flush wall >> CPU; preemption-dominated).
R8.5-H CPU-vs-wall (1-vCPU wall not reproducible; thread-CPU is the stable metric).
R8.5-J futex/context-switch attribution (~2/3 of futex is the worker<->reactor handoff;
reactor involuntary csw ~0.44/req). R8.5-K malloc call-site attribution. S0 value-size
study (long values -> more malloc + lower throughput). R8.5-W reactor<->worker handoff
upper bound (**+6.7%**, 7/7, diagnostic-only/inline). R8.5-X (above).

## Current standing (same-session controls, healthy sessions)
- Strut canonical /plaintext c=50: ~17-18k (session-dependent).
- Frozen Go: ~19-20k. Rust: >=35k (generator-limited floor).
- Strut ~ mid/high-80%s of Go. The indexed router removed the 1000-route collapse.

## Remaining measured gap
After the retained structural wins, remaining canonical cost is dominated by syscall +
synchronisation/scheduling (recv ~1.92, writev ~0.96, eventfd ~0.96, futex ~1.34 per
request) and 1-vCPU socket/preemption wall. The two bounded scheduler experiments show:
(a) removing the whole handoff (W, unsafe inline) = +6.7% upper bound; (b) removing only
the safe completion half (X) = **-10.5%** (the completion queue is a batching mechanism).
No production-safe scheduler win is available cheaply, and the handoff does NOT explain
the ~2x Rust gap.

## Why R8.5 stops (exit criterion B)
The obvious high-value architectural/structural layers have been removed (serializer,
request copies, header construction/representation, route lookup, one cancellation
alloc). Remaining bottlenecks (kernel syscalls, sync/scheduling) are not a clean
removable user-space layer, and the one remaining topology hypothesis (the handoff) is
bounded at <=6.7% upper / negative for the safe subset. Continuing would require
disproportionately invasive redesign (production multi-core event-loop/executor model)
for an unproven payoff. Documented honestly; **R8.5 closed.**

## Notes
- Public `http_request.headers` (map<string,string>) semantics fully certified (294/294
  both modes, incl. insert/read/remove/length/contains/copy/typed-copy/pass/assign/eq/clear).
- Exact-route key normalization non-collision certified.
- Cancellation-token escape/lifetime certified; legacy-vs-reactor completion-cancellation
  divergence documented as an unresolved API/correctness question (not changed in R8.5).
- No R9/R10/FFI/comptime/freestanding touched.
## Final independent architectural challenge (2026-10-08)

Compared current Crow, Drogon/Trantor and oatpp source hot paths; review retained in
`REACTOR-r85-independent-architecture-review.md`. Identified one distinct bounded
candidate: keep worker callbacks/completion batching, but immediately flush ordinary
responses on reactor completion drain and arm OUT only when output remains.

Matched local mechanism: epoll_ctl 308 -> 207, writev 102 -> 102 over the same 102
responses. Correctness: CTest 16/16, focused network 27/27 both modes, large-body
backpressure, pipelining and disconnect checks passed.

Canonical same-session alternating c=50 N=7 extended to N=10: retained 0e95d0d BASE
median **21,583.23** vs CAND **21,484.305** RPS (**−0.46%**, CAND wins **5/10**).
Neutral/noisy -> **REVERT**. All individual runs and identities retained in
`r85-independent/`; decision in `REACTOR-r85-immediate-write-result.md`. This session's
higher absolute BASE does not imply a compiler gain; Go/Rust controls were not rerun.

W's +6.7% is evidence about that specific inline variant, not a mathematical upper
bound on all event-loop redesigns. X did not test immediate writes. This final
experiment independently tests the omitted readiness round trip and still finds no
convincing canonical gain. No full retention wall needed for a rejected candidate.

**R8.5 closure reaffirmed after the final independent challenge.** Retained compiler
remains 0e95d0d. No more R8.5 candidates; no R9/R10/FFI/comptime/freestanding work.
