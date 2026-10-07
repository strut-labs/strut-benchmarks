# R8.5-J — futex + context-switch attribution of the handoff (Linode, c=50)

Pre-requisites measured before choosing any synchronization change. Canonical server
(/root/bench/strut_base, compiled from main 80556b4), identity-gated (pid==comm==exe==
listener, threads=6; stream workers idle throughout). perf 6.8 on node A.

## Thruster (15-20 s c=50 wrk; attribution window 12 s, ~168-200k requests)

Thread model: main thread = reactor; 1 app worker; 4 stream workers (idle: 0 csw).

### Futex syscalls (perf record -e syscalls:sys_enter_futex -g -p <pid>)
Total: 226,133 samples in ~12 s = **~1.34 futex syscalls/request** (consistent with the
~1.51/request process-wide figure).

| owner                                          | share  | stack |
|------------------------------------------------|--------|-------|
| app worker (reactor_worker_loop)               | 66.66% | —     |
|   `condition_variable::wait` -> pthread_cond_wait | 33.38% | work_cv sleep (FUTEX_WAIT; useful blocking) |
|   `unique_lock::~unique_lock` -> mutex::unlock   | 33.27% | run->mutex release after completed.push_back (FUTEX_WAKE of contended reactor) |
| reactor thread (main, run loop)                | 33.34% | run->mutex wait/wake during completed/connections drain/scan |

So the future attribution says: **~2/3 of all futexes are the app-worker <-> reactor
handoff over `run->mutex` + `work_cv`** (half useful worker sleep, half contended
completion-lock wait/wake). Stream workers, allocator, and connection-state locks are
NOT material at c=50.

Raw-source caveat: the 66.66% worker share and the worker-side split (33.38%
pthread_cond_wait / 33.27% mutex::unlock) are directly visible in the perf call-tree.
The 33.34% reactor-thread share is its per-pid total from perf; its classification as
run->mutex wait/wake (completed/connections drain/scan) is inferred from the reactor
main loop's only shared-mutex operations, and its inner call stack was not fully
resolved. Treat the reactor-side sub-classification as approximate.

### Context switches (/proc/<pid>/task/*/status deltas, 12 s window)
| thread                            | voluntary  | involuntary |
|-----------------------------------|------------|-------------|
| reactor (main)                    | +3,183     | +71,501     |
| app worker                        | +73,023    | +48         |
| stream workers                    | ~0         | ~0          |
total ~0.87 csw/request (was ~1.2 reported at R6.5).

- App worker voluntary context switches occur at ~0.43/request (~168k requests over
  the window / ~73k additional voluntary switches ~= **2.3 requests per worker
  voluntary context switch**). This suggests SOME natural batching, but the exact
  requests per full work_cv wake/sleep cycle has NOT been measured here (mapping
  /proc voluntary_ctxt_switches increments onto wake/sleep cycles is not
  established). The precise number requires directly counting work_cv.wait
  entries / returns and requests processed between waits.
- Reactor involuntary ~0.44/req (its wakeups are preemptions, main cause of the
  1-vCPU wall inflation seen in R8.5-H).

## Interpretation / decision (R8.5-J step 6)

- The ~1.5 futexes/request ARE the worker<->reactor handoff, but they are dominated by
  useful worker blocking (condvar sleep when idle) plus one contended completion-lock
  wait/wake pair per completion.
- Because the worker already drains several ready requests per wake, queue-depth
  batch-notify is NOT a promising target (already amortized; extra batching would not
  reduce futex/request materially).
- The completion-side run->mutex wait/wake pair (~0.6-0.7/req) is inherent to the
  mutable shared completion queue with drain-at-top-of-loop; removing it without a
  scheduler/queue rewrite risks the R8.5-A class of correctness bugs (banned scope).
- **Verdict: the handoff is not a clean single-change target.** Follow the reviewer's
  step-8 fallback: return to **allocation/header attribution** (authoritative ~29
  allocs/req, ~2.2KB/req at c=50; R8.5-G touched only some parse copies) or the
  clock/deadline machinery. Do not attempt scheduler/queue rewrites in this pass.

## Instrumentation calibration (R8.5-H wording refinement)
Local micro-benchmark (identical clock functions):
- steady_clock::now(): ~21 ns/call
- clock_gettime(CLOCK_THREAD_CPUTIME_ID): ~236 ns/call (non-vDSO; higher under node
  contention). The R8.5-H per-phase CPU values for the small 3-6 us phases therefore
  include ~0.4-0.5 us of timer overhead of 14 gated reads/sampled and are
  "diagnostic upper-ish estimates / relative shape", not exact intrinsic costs. The
  parse/flush conclusions (large wall vs CPU gap) are robust to this.

## State after this run
Node A server stopped, port free. strut main pristine at 80556b4; benchmark repo clean.
R8.5-H evidence: 90cb0e6; R8.5-I evidence: 73c4a14.