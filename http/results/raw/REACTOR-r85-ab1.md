# R8.5-A / R8.5-B — both neutral on the 1-vCPU bench (reverted)

## R8.5-A empty->non-empty queue notifications
Hypothesis: gate eventfd/condvar notifications to empty->non-empty transitions
to batch coordinator wakeups. Implemented for completed/ready/stream_ready.
RESULT: introduced a wake-correctness hang in reactor fixtures (regression
288->283) and was neutral-by-construction with a single app worker. REVERTED.

## R8.5-B read-once instead of drain-to-EAGAIN
Hypothesis: ~0.92 extra recv/request (drain EAGAIN probe) is removable by
reading once per level-triggered event (epoll re-fires if data remains).
Correct (regressions 288/288, TLS + incremental echo + request_stream pass).
Same-session A/B (background processes, port-polled, c=50 /plaintext):
- BASE (R8/417e197): 15501,15282,15101,14392 -> median 15191 (14392-15501)
- CAND:              15247,13043,15299,16016 -> median 15273 (13043-16016)
Difference ~0.5% = noise; the EAGAIN syscall (~0.5-1us) is ~1% of per-request
cost. read-once also risks extra event-loop iterations for large/pipelined
requests. REVERTED per discipline (noise / added risk, not clearly useful).

## Conclusion for R8.5
The visible coordination syscalls (eventfd ~0.96, extra recv ~0.9, futex ~1.5)
do NOT move the 1-vCPU bench by themselves; variance anyway swamps them. The
next levers to test with A/B: (D) cached steady_clock::now() per reactor
iteration + reduced timed-epoll/deadline work (~4.6% user + kernel timer cost),
then the allocation/parser/header/response-construction profile (likely where
larger user-space wins live).
