# R8.5-L — cached reactor clock (one `now` per event batch): neutral -> REVERTED

Candidate: hoist a single `const auto now = steady_clock::now();` immediately after the
reactor's blocking `wait()` (per event batch) and reuse it for the accept deadline, the
read-deadline refresh, and the loop's expiry scan, instead of 2-3 fresh
`steady_clock::now()` calls per request on the buffered path. Stream/TLS/Websocket and
legacy paths untouched. Deadline semantics: deadlines are computed from batch-start time
per batch, i.e. can only be marginally EARLIER than repeated fresh reads; expiry test
(scan) reuses the same batch `now`, so no premature close and no deadline extension.
No API/ownership changes.

## Mechanism measurement (STRUT_NOW_PROFILE counters, c=50, /plaintext)
| binary | now_calls | requests | now-calls/request |
|--------|-----------|----------|-------------------|
| base (80556b4, 3 sites)  | 376,833 | 346,022 | 1.089 |
| cand (1 hoisted site)     |  28,673 | 320,625 | 0.089 |
Mechanism change confirmed: reactor-loop `steady_clock::now()` drops ~92% per request.

## Correctness
- CTest 16/16 on the candidate build (and on the base-instrumented build).

## Isolated warmed A/B (identity-gated; STRUT_HTTP_REACTOR=1)

c=50 (wrk -t2 -c50 -d15s, alternating; n = 10 cand, 10 base):
| rounds | strut_base rps | lb_cand rps |
|--------|----------------|-------------|
| 1      | 15421.51       | 16181.78    |
| 2      | 15941.79       | 15891.60    |
| 3      | 15553.00       | 15679.87    |
| 4      | 16270.36       | 14820.07    |
| 6      | 15480.25       | 16274.92    |
| 8      | 15944.53       | (cand)16212.72 |
| 9      | 15449.66       | (cand)15603.94 |
| 10     | 15869.68       | 14437.40    |
| 11     | 15811.26       | 15923.70    |
| 12     | 16055.90       | 15515.97    |
medians: BASE 15840.5 vs CAND 15786.3 ~= -0.3%; paired wins 4/8. Ranges overlap fully.

c=10 (wrk -t1 -c10, n=6 base / 7 cand): medians BASE 8942.6 vs CAND 8901.3 ~= -0.5%.
c=1 (wrk -t1 -c1, n=3 base / 2 cand): 2/2 candidate pairs positive but tiny-N, RTT-dominated.
Growth across c=1/10/50 is a weak positive-at-lowest-concurrency, neutral-to-negative at
saturation; overall NO MEASURABLE WIN.

## Verdict: REVERT
Mechanism provably changed (-92% reactor clock calls) but throughput is neutral
across concurrency. Per rule, neutral + not-clearly-simpler => not retained. Wording:
"redundant reactor steady_clock reads are NOT a measurable throughput lever here" --
this closes the cached-now / event-batch reuse strategy for accept-deadline,
read-deadline refresh, and expiry scan on this 1-vCPU benchmark. It does NOT rule out
timed-epoll behavior, deadline data structures, timeout scanning, or broader reactor
timer architecture. Deadline semantics note: the reverted candidate based some
deadlines on the batch-start timestamp, so the deadline shift was bounded to the
event-batch processing interval (deadlines may be marginally earlier, never later).
Positive value: first high-confidence mechanism-level measurement in this campaign
showing a large reduction with zero throughput effect.

## State
Compiler retained at 80556b4 (unchanged). Nothing retained from R8.5-L. Node stopped,
port free. Evidence ledger: R8.5-K attribution 6574a6c (wording fix 49c4a29), K-flat
ca68d06; this file follows.