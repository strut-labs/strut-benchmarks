# R8.5-D — de-allocating route matcher (KEPT)

Compiler: beed5ba.

## Change
strut_route_match built 2 std::stringstreams + a std::string per segment per
match. For a server with N static routes that was ~2N allocations/request even
with zero params. Replaced with an index-based, allocation-free tokenizer that
allocates ONLY when a segment captures a :param (static routes: zero).

General optimization for every routed server (not /plaintext-specific).

## Correctness
Regressions 288/288 both modes (route/:params/trailing-slash/empty-segment
fixtures green), codegen, CTest 16/16 x4 (GCC/Clang -Werror, ASan/UBSan).

## Performance (wide-node-variance session caveat)
Alternating uninstrumented A/B:
- c=1: BASE 5455,5220,5111,5529 (median ~5337); CAND 5508,5437,5426,5542
  (median ~5473) -> +~2.5% direction
- c=50 (earlier session): BASE ~15.2-16.0k vs CAND ~15.3-16.0k, plus one
  20k/21.6k pair (+~4%). Node session variance is large; treat direction as
  supportive, not a precise figure.
- Allocation reduction is BY CONSTRUCTION: stringstream + per-segment string
  allocations removed for static routes (~2N allocs/request for N routes).

## Next candidates (after attribution reasoning)
- request-head parsing: header unordered_map nodes + lowercase strings +
  substr copies (likely the largest remaining source; host header + request
  line parsing).
- request/response object copies + params map.
- response serialization via std::ostringstream.
- cancellation source make_shared (2 allocs/request; hard to remove without a
  public token/API change - deprioritized).

## EVIDENCE CORRECTION (per review)
- The "C50/B50" confirmation accidentally used a helper hard-coded to
  `wrk -t1 -c1`; those samples were c=1 and are WITHDRAWN as c=50 evidence.
- The B-C-B-C-B c=50 sequence had N=3 BASE / N=2 CAND and is SUGGESTIVE ONLY,
  not an authoritative +4%.
- Exact heap-allocation reduction was NOT measured; the "~2N allocations/request
  removed" figure is WITHDRAWN. Established by construction only: the old
  matcher created 2 std::stringstream objects + temporary segment std::strings
  per match; the new static path performs no explicit dynamic string
  materialization. Allocation delta is recorded as UNMEASURED pending a reliable
  interposer dump.
- beed5ba classification: code-inspection-guided optimization (not
  profiler-ranked largest allocation source).
- Full strict certification now demonstrated: CTest 16/16 x4 (normal, GCC
  -Werror, Clang -Werror, ASan/UBSan) plus regressions 289/289 both modes
  (incl. a new route-semantics fixture verifying static/:param/multi-param/
  trailing-slash-normalization/mismatch matching the original getline semantics).
