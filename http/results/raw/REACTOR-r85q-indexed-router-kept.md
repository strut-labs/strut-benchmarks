# R8.5-Q — order-preserving indexed router (exact path index + param trie): KEPT

Fixes the measured O(N) route-scan (R8.5-P): indexes route patterns at registration
(routes only change while stopped), retaining registration ordinals, so a request
retrieves only actually-matching candidate RouteIds instead of scanning all routes.

Architecture: static (no ':') patterns -> unordered_map keyed by a segment-sequence
serialization (compile_pattern segments; trailing-slash exact: "/a" and "/a/" share a
key, matching historical strut_route_match); parameterized patterns -> a segment trie
(static children + one param child; segments from the same strut_compile_pattern;
branch-forking when a segment matches BOTH a static child and the param child, so all
matching patterns are collected). Resolution: winner = lowest registration ordinal
whose method==route_method and which has a handler; 405 iff any path-matched candidate
had no compatible method+handler; 404 iff no candidate. Params materialized only for
the winner (captures as {name, path offset+length}); websocket/stream/request-stream
routes all index through their add_* path.

## Mechanism (STRUT_ROUTE_PROFILE counter, N=1000)
| request       | candidates/req |
|---------------|----------------|
| exact-first   | 1.00 (was 1)  |
| exact-last    | 1.00 (was ~1000) |
| miss          | 0.00 (was ~1001) |
| param last    | 1.00 (was ~1001) |

## Same-session warmed identity-gated scaling A/B (BASE 51771f9, CAND Q)
| workload                        | base median | Q median   | delta    |
|---------------------------------|-------------|------------|----------|
| N=1000 exact-last /r1000 (c10)  | 3909        | 9693       | +148%    |
| N=1000 param /user/x (c10)      | ~3343       | ~9598      | +~187%   |
| N=1000 miss /nope (c10)         | ~2301       | ~3170      | +~37%    |
| N=100 exact-last (c10)          | ~8659       | ~8917      | +~3%     |
| N=1 tiny /plaintext (c50)       | ~16850      | ~17610     | +4.5% (noise, no regression) |

## Correctness — full retention wall (all green)
- CTest 16/16 normal, GCC -Werror, Clang -Werror, ASan/UBSan.
- Regressions 289/289 default + 289/289 STRUT_HTTP_REACTOR=1.
- Route behavior battery vs base (identical statuses+handlers): param-before-static
  order, static-before-param, same-path GET/POST, PUT->405, missing->404, trailing
  slash ("/a/"->"/a" and "/users/new/"->param), multi-param, HEAD->GET path.
- codegen slice budget 160000->165000 (indexed-router emission; collar in the http
  server slice test).

## Decision: KEEP
Committed as 56ea341. Retained stack: beed5ba, 87e00ff/80556b4, 73d379a, da4a8f2,
51771f9, 56ea341. Sub-linear candidate selection; hit cases no longer depend on total
route count. Route index is built at registration (routes only registered while
stopped), preserving "expensive compile at registration, cheap lookup" (Hyper/matchit
lesson).

## Exact-key safety invariant
The exact static-route key serializes compiled segments with '\0' delimiters, so "/a"
and "/a/" intentionally share a bucket (historical trailing-slash semantics). This is
unambiguous because '\0' cannot occur in a legal route segment (DSL string literal) or
request path segment (strut_http_target rejects raw control bytes and %00-decoded
0x00/0x7f). Covered by a permanent regression fixture:
strut-regression-suite fixtures/network/route-exact-key-distinct.p (+.json), proving
/a/bc, /ab/c, /a/b/c stay distinct while /a and /a/ share (290/290 both modes).

## Canonical Go control wording
"Last clean canonical control (pre-Q): Strut ~17,033 vs Go ~19,515 = ~87.3%."
This was measured BEFORE Q (on 51771f9). Q's N=1/tiny-route A/B is canonical-neutral,
so a similar ratio is EXPECTED, but 56ea341 vs Go has NOT been cleanly re-measured
(the attempted rerun hit a degraded node session: both sides ~3k, discarded). Rerun on
a healthy node.