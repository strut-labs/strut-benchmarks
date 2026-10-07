# R8.5-S0 — header value-size scaling study (target selection, a08fea5)

Short characterization only (c=50, warm 10s, N=3 per shape; not a candidate A/B).

## Throughput vs extra-header value size (8 extra headers)
| values | rps (3 runs)              | median |
|--------|---------------------------|--------|
| 8 B    | 14040 / 14199 / 13772     | ~14040 |
| 64 B   | 13147 / 12981 / 13490     | ~13147 (-6.4%) |
| 256 B  | 9990 / 10242 / 10098      | ~10098 (-28%) |

## Allocator density (perf malloc uprobe, perf-adjusted window; both shapes same method)
| values | malloc samples / ~reqs | ~malloc events/req |
|--------|------------------------|--------------------|
| 8 B    | 364,531 / 27,625       | 13.2               |
| 64 B   | 502,614 / 17,923       | 28.0               |

Long values DO add allocator work: 8x64B adds ~15 traced malloc events/request
(>SSO value strings heap-allocate, ~2/header). But throughput at 64B falls only ~6.4%
while bytes/request grow ~4x; at 256B (-28%) the drop tracks the ~2KB/request network
cost. This matches the campaign-wide finding that REDUCING MALLOC EVENTS ALONE rarely
moves throughput (R8.5-G/I/K were flat; wins came from removing CPU/whole layers).

## Decision: DEPRIORITIZE S (not disproven)
S0 is CHARACTERIZATION, not causal isolation: it changed bytes/request, bytes copied,
value-string construction, SSO->heap crossing, memory bandwidth, cache footprint, parser
work and generator load together, so it does NOT prove the -6.4%/-28% drops are "mostly
network bytes", nor that allocator cost is negligible. The malloc-uprobe run is heavily
perturbed (diagnostic rps 5.5k/3.6k vs 14k/13k uninstrumented), so 13.2 vs 28.0 events
only shows crossing SSO materially increases malloc activity -- not an authoritative
per-request count, and NOT a basis to project the payoff of removing them (S is
unimplemented).

Defensible conclusion: long header values DO create substantially more allocator
activity and lower throughput, so span/lazy values have real potential headroom for
long-value/header-heavy traffic. But canonical and current short-header workloads are
largely SSO-covered, while exploiting that headroom needs a comparatively invasive
proxy/codegen representation change. S is DEPRIORITIZED in favour of a target whose cost
sits on the CANONICAL path (cancellation), and remains a legitimate later optimization
for long-value/header-heavy workloads.

## Pivot: cancellation / shared ownership
Unlike short header values, per-request cancellation allocation exists in the CANONICAL
request (~10.7% of observed malloc samples in R8.5-K, sample-share). Prefer LAZY/ELIDED
cancellation work (don't construct cancellation state when the callback never observes
`req.cancellation`) over making make_shared cheaper — the Rust "don't do the work"
pattern that produced our retained wins. Preserve exactly: disconnect/stop cancellation,
callback lifetime, async, request_stream/response_stream, WebSocket, keep-alive
boundaries.

Cross-language control unchanged: Strut mid/high-80%s of frozen Go (session-specific).