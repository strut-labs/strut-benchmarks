# R8.5-R — specialized flat request-header container: KEPT

Follows the Hyper/HeaderMap lesson beyond R8.5-O. Audit finding: `http_request.headers`
has DSL type `map<string,string>` (api_registry.cpp), i.e. a GENERIC map whose emitted
operations must all keep working; the runtime member was
`std::unordered_map<strut_string,strut_string>`. Replaced ONLY that member with a
dedicated flat container `strut_http_headers` (vector<pair<strut_string,strut_string>>)
that is map-compatible: operator[] (insert-or-access), size/empty/reserve/clear,
begin/end (iteration yielding .first/.second), find/contains/count/at/emplace/erase, and
an implicit conversion to `std::unordered_map<strut_string,strut_string>` for the rare
escape cases (assigning/passing headers as a generic map). `query`/`params` remain
unordered_map. No codegen changes required (member-call surface preserved); no language
semantics changed.

## Correctness — full retention wall (green)
- CTest 16/16 normal, GCC -Werror, Clang -Werror, ASan/UBSan.
- Regressions 290/290 default + 290/290 STRUT_HTTP_REACTOR=1 (incl. the new exact-key
  fixture; all HTTP/header/cookie/TE/Content-Length/WebSocket fixtures exercise the
  container).

## Mechanism (perf uprobe malloc, /plaintext c=50)
WITHDRAWN: the earlier "8.79 -> 5.69 mallocs/request (-35%)" is NOT valid -- the perf
5 s window and the 12 s wrk interval were not coextensive (perf started ~2 s before the
load), so normalizing by rps*5 was wrong (same denominator error as R8.5-K).

Corrected coextensive measurement (perf window and wrk -d5s started together; same
method for both binaries, probe overhead applies to both):
- BASE 56ea341: 423,008 malloc samples / ~26,230 requests = 16.13 malloc/request.
- R: 402,973 samples / ~28,385 requests = 14.20 malloc/request.  **-12% per request**
  (R had FEWER samples despite MORE requests). Consistent with removing the per-header
  unordered_map node/bucket allocations. Same-shaped traces also showed 509,675 vs
  343,849 total samples earlier (different window) -- direction agrees, exact % differs.

## Throughput — same-session warmed identity-gated A/B (BASE 56ea341)
| workload                             | base median | R median | delta  | pairs |
|--------------------------------------|-------------|----------|--------|-------|
| /plaintext c=50 canonical            | 16707       | 17271    | +3.4%  | 6/6   |
| /plaintext c=50 + 8 extra headers    | 12865       | 13778    | +7.1%  | 5/5   |

Unlike R8.5-O (canonical weak/neutral), R is a genuine canonical win AND a larger
header-heavy win on top of O.

## Decision: KEEP
Committed as 5c647bf. Retained stack: beed5ba, 87e00ff/80556b4, 73d379a, da4a8f2,
51771f9, 56ea341, 5c647bf.

## Notes / next
- Stable span-backed values (S) and cancellation ownership remain the following
  architectural steps; not folded into R (bounded container-only change).
- Canonical Strut vs frozen Go (healthy session, N=7/6, c=50): Go median 20091
  (19787-21323), Strut median 17238 (16808-17594), ~85.8%. Essentially the same as the
  pre-Q ~87.3% (session-specific); R's +3.4% canonical A/B and Go's faster session
  offset. Current Strut ~= 86% of frozen Go at c=50 on a healthy node.