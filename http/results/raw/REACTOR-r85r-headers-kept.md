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

## Mechanism (perf uprobe malloc, 5 s, /plaintext c=50)
- BASE 56ea341: 8.79 malloc-samples/request.
- R: 5.69 malloc-samples/request. **-35%** (per-header hash node/bucket allocations
  gone). Header-related allocations now grow with the flat vector, not per-node.

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
- Canonical Strut vs frozen Go rerun: pending a healthy node session.