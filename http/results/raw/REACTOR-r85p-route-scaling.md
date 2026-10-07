# R8.5-P — route-scaling measurement + compiled-segment router attempt (router REVERTED)

## Measurement (routes_considered counter, instrumented 51771f9; c=10 t1 wrk)
| routes | /r1 (first) | /rN (last) | miss | param-last |
|--------|-------------|-----------|------|------------|
| 10     | iters 1, rps 10162 | 10, 9001 | 11, 3130 | 11, 9470 |
| 100    | 1, 9889           | 100, 8568 | 101, 2825 | 101, 8591 |
| 1000   | 1, 10320          | 1000, 3123 | 1001, 2362 | 1001, 3292 |

routes_considered is EXACTLY linear (first=1, last=N, miss=N+1, param-last=N+1).
Throughput collapses with position: exact-last 10k->3.1k at N=1000; miss ->2.4k.
=> linear route scan IS a material scaling problem at 100-1000 routes.

## Compiled-segment router prototype (order- and 405-preserving; registration-order exact)
Precompiled per-route segments (built once at registration; same find()-based control
flow as strut_route_match), compiled match against the path; params materialized only
for the winning route; parallel compiled_routes array; all add_route/stream/request
stream/websocket paths parallel-populate. Buffered reactor pump loop rewritten to use
it. Legacy path + websocket pre-scan untouched.

Correctness: CTest 16/16; regressions 289/289 default + 289/289 reactor (incl. the
route-semantics fixtures: static/:param/multi-param/trailing-slash/mismatch). Exact.

Same-session alternating A/B:
- N=1000 exact-last (c=10, 4+4): base median 3863 vs router 3937 -> +1.9%.
- N=1 tiny (c=50, 3+3): base median 17095 vs router 16862 -> -1.4% (noise).
- N=1000 miss ~flat (scan count identical).

## Verdict: REVERT the router prototype
The compiled matcher preserves ordering+405 semantics, which FORBIDS skipping
candidates, so routes_considered stays exactly linear; the only win is a smaller
per-candidate constant (~+2% at N=1000), which does NOT meet R8.5-P's "substantial win
at 100/1000 routes" criterion. Package growth (>1 struct, parallel array, second
matcher) is not justified at +2%.

## Implication / next step
A genuinely sub-linear router requires an ORDER-RESPECTING route trie / exact-index
that reproduces "first registration-order path-match, method recorded for 405" -
a larger, higher-risk checkpoint (the reviewer's "later" study). P's measurement is the
deliverable: linear scan with exact routes_considered, throughput collapse to ~1/3 at
1000 late/miss. Park compiled routing for now; current Strut route behavior is
order-exact.

## State
Main unchanged at 51771f9 (router/counters lived only in the temporary worktree; both
discarded). Both repos clean. Node stopped.