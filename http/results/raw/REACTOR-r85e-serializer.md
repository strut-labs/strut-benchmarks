# R8.5-E — response-head serializer (no std::ostringstream) — RETAINED (structural)

Compiler: R8.5-E commit (beed5ba + serializer).

## Change
strut_serialize_http_response_head built every response head via
std::ostringstream + out.str() copy. Replaced with a reserved std::string +
inline integer append. Semantics preserved (validated by the 289/289 regression
suite and curl parity: 200/Content-Length, 204, 302 Location, custom headers).

## Certification
CTest 16/16 x4, codegen, regressions 289/289 both modes, diff-check clean.

## Warmed alternating A/B (N=5 each; warm-up run before each measured run)
- c=50: BASE med 18.4k [12.1k-20.4k, two low outliers] | CAND med 20.3k [19.1k-20.7k] -> +10.3% (direction, but BASE is bimodal/noisy)
- c=10: BASE med 13.1k | CAND med 12.7k (one CAND outlier) -> -3.2%
- c=1 : BASE med 4.53k | CAND med 4.55k -> +0.3%

Node seeker variance (BASE c=50 ranged 12.1k-20.4k) is far larger than these
deltas; classification is "no controlled throughput win established". RETAINED
because it is a general hot-path cleanup (removes an ostringstream and a string
copy per response by construction), not as a measured speedup.
