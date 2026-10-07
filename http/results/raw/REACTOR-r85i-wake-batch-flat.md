# R8.5-I — worker->reactor pending-wake batching: A/B NEUTRAL -> REVERTED

Candidate from R8.5-H (no large stable user-space phase; cost in sync/wake): an explicit
pending-wake state on the reactor so a producer that sees the reactor NOT inside
`wait()` records `pending_wake` instead of writing the eventfd; the reactor, under the
same mutex, only blocks when `pending_wake` is false at the moment it transitions to
waiting, otherwise it returns immediately and re-drains the work queues at loop top.
Race-free (single mutex; no lost wake). R8.5-A's incorrect case is not retried.

## Correctness (candidate, local)
- CTest 16/16 on the candidate build.
- Functional smoke: /plaintext 200 + body, /json 200, duplicate-Host 400 (matches BASE).

## Isolated warmed A/B (Linode, STRUT_HTTP_REACTOR=1, wrk -t2 -c50 -d15s, identity-gated)

| round | strut_base rps | strut_i_cand rps |
|-------|----------------|------------------|
| 1     | 14952.79       | 15546.79         |
| 2     | 15667.16       | 15325.93         |
| 3     | 15484.78       | 14483.37         |
| 4     | 15767.23       | 15051.67         |
| 5     | 14956.53       | 15699.25         |
| median| 15484.78       | 15325.93         |

Median CAND/BASE ≈ -1.0%; ranges overlap completely (14953-15767 vs 14483-15699).
**No measurable effect.**

## Mechanism analysis (why it is neutral here)
With 1 worker and c=50, the reactor is almost always inside `wait()` when a completion
arrives (waiting_==true), so the producer writes the eventfd unconditionally and the
batch path (pending_wake) rarely executes. The eventfd count therefore stays near the
known ~0.96/request. Batching would only matter if completions routinely arrived while
the reactor was busy processing (higher producer concurrency / multiple workers).
The futex/dispatch side (work_cv, ~1.51/request) is a separate path this change did not
touch.

## Decision: REVERT (neutral)
Not committed; main stays pristine at 80556b4. Temporary worktree removed.

## Remaining direction (still ONE variable at a time)
- Eventfd write+read pair (~0.96/req) is inherent to the 1-writer/1-waiter handoff at
  this load; pending-wake does not help when the reactor is already parked.
- Next isolated candidates on the sync budget: the dispatch futex path
  (work_cv.wait/notify_pair ~1.51/req) is now the largest documented non-request
  syscall component and is untouched; a queue-depth-batched worker wake
  (drain-ready batch in one notify) is a candidate only if it can avoid the R8.5-A
  correctness trap. Allocation baseline (~29 allocs/req) remains for the follow-up
  decision, but no user-space CPU work is large enough to justify it yet.