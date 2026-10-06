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
