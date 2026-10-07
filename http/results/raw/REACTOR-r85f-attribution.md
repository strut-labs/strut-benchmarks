# R8.5-F — clean scoped phase attribution (/plaintext, c=50, 1-vCPU Linode)

Instrumentation: env-gated (`STRUT_PHASE_PROFILE`), **1/64 per-request sampling gated
on `conn->phase_sample`** (per-connection flag follows reactor->worker->reactor; both
`steady_clock::now()` calls per phase are conditional). Note: the phase counters
accumulate from server start and are dumped periodically, so the reported `sampled`
counts INCLUDE the warm-up interval — they must NOT be paired with the exact measured
wrk request count as if they covered the same window. The `ns/sampled` averages are
steady-state over warm+measured load and remain valid for ranking. Buckets:
request-head copy+parse,
prep, route lookup, callback/response creation, serializer (nested in build+enqueue),
build+completion enqueue, flush/write. All are **scoped sampled user-space cost**, NOT
total CPU/latency. Deployed as `/root/bench/phase_prof2`; identity-gated (pid == comm ==
exe == listener owner, threads=6) before every wrk run. wrk -t2 -c50 -d20s.

## Phase cost, ns per sampled request (stable across runs)

| phase                       | run1   | run2   | /json   |
|-----------------------------|--------|--------|---------|
| request-head copy + parse   | 11332  | 11528  | 11366   |
| request preparation (prep)  | 1074   | 1092   | 1218    |
| route lookup                | 1000   | 973    | 1187    |
| callback/response creation  | 3099   | 3235   | 6849    |
| serializer (nested in comp) | 3363   | 3430   | 2724    |
| build + completion enqueue  | 4163   | 4229   | 3617    |
| flush/write                 | 12512  | 12518  | 11630   |
| rps (20s)                   | 15839  | 15656  | 15665   |
| sampled count               | 9782   | 7448   | 5554    |

rps repeated for stability; /json differential confirmed parse is **request-fixed**
(11332/11528/11366) while callback grows 3.2 -> 6.8us (response-specific).

## Reading
- Flush/write is the largest bucket (~12.5us) but is wall time around the writev syscall
  (syscall picture: ~0.96 writev/request), i.e. largely socket/kernel.
- Parse is the largest **pure user-space** request-fixed phase (~11.4us). Note this wall
  also includes 1-vCPU preemption, so it overstates real parse CPU.
- Callback 3.2us, serializer 3.4us (nested), and build+enqueue-minus-serializer ~0.8us
  are small; prep/route ~1us.
- Conclusion: no single clean user-space phase dominates the budget; the already-measured
  kernel/synchronization costs (eventfd ~0.96, futex ~1.51, recv ~1.92, writev ~0.96 per
  request) sit outside this scoped profile.

## Formal state
Per-phase scoped attribution: **COMPLETED** (replaces PENDING status). The parser was
NOT preselected; it was chosen as the largest clean request-fixed user-space source and
then tested (see REACTOR-r85g-parse-flat.md).