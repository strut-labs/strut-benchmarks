# R6.5 — reactor/worker utilisation investigation (corrected)

Follow-up to REACTOR-r25-early-gate.md. The early-gate note reported ~43% CPU
at c=50 based on a `pidstat` average; that reading was a sampling artifact.

## Corrected CPU fraction (steady state, c=50 /plaintext)

- `pidstat -p <pid> 1 N` per-second rows, averaged: **~95% CPU**
- `perf stat -p <pid>` task-clock ≈ 90% of a core over the window
- earlier `pidstat` "Average 49.6%" was wrong; the per-second rows and
  task-clock agree the box is essentially saturated.

So there is **no large utilisation bubble**. The Box is busy.

## Where the CPU goes (c=50 /plaintext)

Per-thread (from /proc task utime+stime, CLK_TCK=100), same window:

| thread | CPU |
|---|---|
| reactor | ~72–79% |
| app worker | ~20% |

The reactor thread carries nearly all transport + parsing + response-I/O work;
the worker only builds the response. The worker is not the bottleneck.

Syscalls (perf, per second, steady state ~11k req/s):

| syscall | per sec | per request |
|---|---|---|
| recvfrom | ~20k | ~1.9 (one read + one drain EAGAIN) |
| sendto   | ~20k | ~1.9 (head and body as two segments) |
| write (eventfd wake) | ~10k | ~1.0 |
| futex | ~20k | ~2 |
| epoll_wait | ~0.5k | amortised |

context switches ≈ 1.2 per request (reactor<->worker round trip).

## Answers to the R6.5 questions

1. Reactor and worker do alternate (one dispatch wake + one completion wake per
   request), but this is not leaving large idle gaps — the process is ~95% busy.
2. Yes: each request does reactor->worker and worker->reactor (2 wakeups), no
   batching. With one worker there is no completion batching opportunity.
3. Yes, completion wakeups are one eventfd write per request (~1.0/req).
4. eventfd/futex traffic is real (~1 eventfd + ~2 futex per request) but small
   relative to the reactor's transport/parse cost.
5. The worker queue is not starved; the worker runs (~20%).
6. No: completions are drained promptly (eventfd wake).
7. Batching would only help with >1 worker (no batching benefit with 1).
8. On 1 vCPU, 1 worker already saturates the box, so worker-count tuning is
   moot here. Multi-core evidence (R15) is still required.

## The actual dominant lever: TCP segment / syscall count per response

The reactor emitted the response head and body as **two** `send` calls
(TCP_NODELAY => two segments per response). On a 1-vCPU host the server's own
TCP/IP stack cost dominates, so halving segments per response is a large win.

Change: `strut_tcp_socket::writev_some` (`writev` on POSIX, `WSASend` with two
buffers on Windows); `reactor_flush` now emits head+body in one call.

Interleaved A/B on the same node/session, /plaintext c=50 (req/s):

| binary | runs | mean |
|---|---|---|
| before (two sends) | 12246, 12296, 12166, 12492 | ~12.3k |
| after (one writev)  | 17049, 17562, 16797, 16197 | ~16.9k |

**+37%**. c=1 ~4.85k (previously ~4.29k, no longer behind the legacy 5.0k) —
the low-concurrency regression is closed. c=10 ~13.9k.

## Consequence

- The R25 "~37 µs/request, Go-class" claim was derived from the bad CPU reading
  and is withdrawn. True per-request CPU before R6.5 was ~85 µs; after R6.5 the
  gain comes from removing per-response overhead, not from a scheduling change.
- Remaining gap to Go/Rust is per-request cost (reactor-thread parse/serialise/
  copies) — R13 territory — not a scheduling bubble.
- Inline/worker-steal execution on the reactor is **not** adopted: the data
  does not justify taking on the "reactor must not run arbitrary blocking user
  code" risk.

Benchmark still run via `STRUT_HTTP_REACTOR=1`; legacy default unchanged.
Go/Rust frozen; Rust ~35k still generator-limited.