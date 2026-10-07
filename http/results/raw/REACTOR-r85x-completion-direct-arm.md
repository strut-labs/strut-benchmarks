# R8.5-X — worker->reactor completion-handoff elimination: REVERT (negative, -10.5%)

Production-safe subset of W: keep arbitrary callbacks on the worker (blocking isolation
preserved), but have the worker set phase=writing and arm EPOLLOUT on that connection
directly, removing the completion queue push + completion eventfd wake + reactor
completion round-trip. Streams/WebSocket/async unchanged. Linux `modify` is `epoll_ctl`
(thread-safe); the poll backend would need a small lock if retained.

Correctness: CTest 16/16; local 16x20 concurrent keep-alive on :8080 all 200; /plaintext
/json/404 correct.

## Canonical A/B (c=50, alternating, identity-gated, N=7/7)
| round | base 0e95d0d | X |
|-------|--------------|---|
| 1 | 14099 | 13013 |
| 2 | 13093 | 14348 |
| 3 | 15614 | 13968 |
| 4 | 16277 | 14326 |
| 5 | 16756 | 15193 |
| 6 | 16014 | 13615 |
| 7 | 14601 | 13572 |
| median | 15614 | 13968 |
delta **-10.5%**, X wins 1/7.

## Interpretation
Directly arming EPOLLOUT from the worker is SLOWER than the completion-queue path. The
reactor's completion drain batches: it swaps the whole `completed` deque and issues one
`modify` per drained connection while already awake, and the eventfd wake is cheap
relative to a per-response `epoll_ctl(MOD)` from the worker plus re-waking the reactor.
So the worker->reactor completion handoff is NOT waste -- it is a batching mechanism.

Interpretation (not over-decomposed): X rules out the worker->reactor completion handoff
as a cheap production-safe optimization. It does NOT let us attribute W's +6.7% piecewise
-- W changed several interacting costs at once (removed reactor->worker queue/wake, worker
scheduling, ran the callback inline, removed the completion handoff+wake, kept hot state
on the reactor), while X changed only the completion half and replaced it with a
different pattern (worker-side epoll_ctl). Effects need not be additive. W still
establishes that eliminating the ENTIRE scheduling handoff topology has only a ~+6.7%
upper-bound benefit on canonical /plaintext.

## Decision: REVERT
No production-safe scheduler win is available here; the cheap half is negative. Per clause
<= ~2% / negative -> REVERT. No production change; main stays 0e95d0d.