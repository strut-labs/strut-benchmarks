# R8.5 allocation profile (/plaintext, 1-vCPU)

malloc/calloc/realloc/free interposer (LD_PRELOAD) on the R8 reactor server
under c=50 /plaintext load (~13.5-16k rps).

Over ~17 s lifetime (~15 s load):
- alloc_calls ~2,946,750  (~196k alloc/s)  => ~12-14 allocs/request
- free_calls  ~2,946,046  (balanced)
- total_bytes ~222.6 MB  => ~900 B/request

Conclusion: the simplest possible buffered request/server currently performs
~13 heap allocations + ~900 B per request. This is the confirmed R8.5 lever
(Rust per-request allocations are typically 1-3). Next iteration: attribute by
call-site and reduce across:

- request head parsing (vector fields, header unordered_map nodes, lowercased
  strings, query/params maps)
- request.params build even for routes that don't read params
- cancellation-source allocation per request
- strut_string / substr copies
- response body + header map + serialize via std::ostringstream

Each change: correctness wall + same-session A/B; KEEP/REVERT.
