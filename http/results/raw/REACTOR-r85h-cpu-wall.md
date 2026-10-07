# R8.5-H — CPU vs wall attribution for the two largest phase buckets (Linode)

Temporary diagnostic: same 1/64 per-connection sampler as R8.5-F, but every bucket
records BOTH wall (`steady_clock`) and per-thread CPU time
(`clock_gettime(CLOCK_THREAD_CPUTIME_ID)`), both reads gated on `phase_sample`.
Deployed as `/root/bench/phase_prof3`; identity-gated (pid == comm == exe == listener,
threads=6); warm 10 s + measured 15 s; /plaintext c=50, two fresh processes.

## Wall vs CPU, ns per sampled request (measured 15 s window)

Run2 (rps 15,645.84; sampled 3686 in window):

| phase  | wall ns/sample | cpu ns/sample | cpu/wall |
|--------|----------------|---------------|----------|
| parse  | 63827          | 13068         | 20.5%    |
| prep   | 5319           | 4789          | 90.0%    |
| route  | 4095           | 3628          | 88.6%    |
| cb     | 4055           | 3981          | 98.2%    |
| ser    | 4029           | 4088          | 101.5%   |
| comp   | 6576           | 6577          | 100.0%   |
| flush  | 46213          | 17378         | 37.6%    |

Run1 (rps 14,448.59) shape identical: parse 19%, flush 35-37%, all other 90-100%.

## Findings

1. **Wall is NOT reproducible across sessions at equal rps.** parse wall was 11.3-11.5
   us (R8.5-F) and is 63-64 us here; flush 12.5 us -> 46 us; rps identical (~15.6k).
   The 1-vCPU VM deschedules the reactor/writer threads during short regions; wall-time
   phase rankings on this box cannot be trusted as optimization evidence.
2. **CPU is the stable metric.** The only phases whose wall span is dominated by
   non-running time are parse (~20% cpu/wall) and flush (~38%); all others run 90-100%
   of their wall span.
3. **Caveat / instrumentation self-interference:** raw `clock_gettime` with
   CLOCK_THREAD_CPUTIME_ID is a non-vDSO syscall (~microsecond class on this contended
   VM); each phase pays two of them on a sampled request, inflating the cpu bucket by
   roughly a few us. Absolute CPU ns/sample are therefore inflated; the RATIOS and the
   per-thread truth (which phases actually consume cycles vs. wait) are robust.
4. No phase shows a large, stable, clean user-space CPU cost. prep/route/cb/ser/comp
   are small and CPU-bound; their true cost is on the order of ~1-2 us each.

## Conclusion / direction

- R8.5-F's "parse/flush dominate" wall ranking is superseded as an optimization basis.
- There is no large stable user-space phase to attack; the cost is in
  scheduling/kernel/wake/sync (eventfd ~0.96, futex ~1.51, recv ~1.92, writev ~0.96 per
  request) plus keep-alive handoff.
- Next candidate (single, isolated): the worker->reactor wake/dispatch path. Per earlier
  guidance, model an explicit pending-wake state on the reactor side so there is no race
  between "queue non-empty", "reactor drained queue", and "producer decides not to
  signal" — do NOT simply retry the empty() check (R8.5-A was incorrect; R8.5-B read-once
  was neutral). Combine with the ~29 allocs/request baseline only if a wake candidate is
  both CPU and allocation relevant.

## Repo state
Compiler retained at 80556b4 (R8.5-D beed5ba, R8.5-E 87e00ff + 80556b4; R8.5-G adds
nothing). Main repo pristine. Diagnostic branch/worktree /tmp/r85h-wt and binary
/home/nick/phase_prof3 retained until evidence is banked, then removed.