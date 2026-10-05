# TCP_NODELAY before/after (c=50, 15 s, node B -> node A)

compiler before: 74d46112310d825ad319bc73b58b4eca1c75e1c7
compiler after:  4686a97b4215f93b0958bf4b9c5e775d854a83ae

| metric (strut, /plaintext, c=50) | before | after |
|---|---|---|
| requests/sec | ~1 200 | ~9 023 |
| p50 ms       | ~41    | ~5.34 |
| p99 ms       | ~52    | ~11.6 |
| server CPU   | ~11%   | ~95.7% |
| RSS          | 5.5 MB | 5.6 MB |

Keep-alive sequential per-request latency (node B):
  before: first 1.6 ms, then ~40 ms each
  after:  first 1.6 ms, then ~0.23 ms each

Post-fix c=50 controls (unchanged Go/Rust):
  go   /plaintext 24 197 rps, p50 2.00 ms, CPU 94.9%, RSS 12.7 MB
  rust /plaintext 35 454 rps, p50 1.28 ms, CPU 88.4%, RSS 4.4 MB

Interpretation: TCP_NODELAY removed the dominant transport blocker; Strut is now
CPU-bound (~96%), so the remaining ~2.7x (go) / ~3.9x (rust) gap is a
compute-efficiency problem, not a scheduling/waiting problem.
