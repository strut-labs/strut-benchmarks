# R8.5 final independent candidate — immediate write: REVERT

Date: 2026-10-08 (Australia/Melbourne). **Decision: REVERT; CLOSE R8.5.**

Final retained compiler remains `0e95d0d5062f55a7a3c051e7311e26acc2e90a44`.
No production performance change retained. This was the one final candidate from the accepted independent Crow/Drogon/oatpp architecture review; no additional candidate follows.

## Candidate and isolation

BASE: exact rebuilt retained 0e95d0d. CAND: that commit plus immediate ordinary buffered-response writes on reactor completion drain, with writable readiness armed only when output remains. Callback worker isolation, completion deque batching and eventfd wake stay intact. Streams, request_stream, WebSocket and reactor-generated status paths are not routed through this new completion call site.

The reused nonblocking `reactor_flush` drains while writes make progress, stops on inability to progress, retains offsets and falls back to existing readiness. It does not busy-wait for a socket to become writable. Full success immediately invokes existing finish/keep-alive handling. That still needs the read-interest MOD because dispatch disabled read interests; only the unnecessary write-interest MOD/OUT event is removed. No additional keep-alive or scheduler change was attempted.

`reactor_flush` returns whether output remains; this avoids inspecting phase after finish, which may already pump a pipelined request and dispatch another worker callback. Candidate patch is preserved at `r85-independent/immediate-write.patch`. Generated-only diff at `r85-independent/generated-diff.patch`.

Worktrees `/tmp/r85-immediate-write` and `/tmp/r85-retained-base` were isolated at 0e95d0d. After the result, reversed only the candidate patch with `git apply -R`; candidate worktree is clean and retained main unchanged. No reset/clean/rebase/history rewrite.

## Provenance and method

Explicit user approval covered generated benchmark source/artifact upload and execution at `root@96.126.107.155:/root/bench/`; generator was retained `96.126.107.181`. Both Linodes preserved. Nothing unrelated uploaded.

Before canonical measurement, caught a stale local compiler-generated BASE that omitted retained changes. Rebuilt exact source in the baseline worktree and regenerated BASE. Source diff verified to contain only this candidate; all timed remote runs use that corrected BASE. Matched local mechanism check was repeated and supersedes the initial trace. This provenance correction is banked, not hidden.

Remote toolchain: GCC 13.3.0 Ubuntu; both generated programs built with identical `-std=c++17 -O2 -pthread`, same JSON include path. Full hashes in `r85-independent/benchmark-metadata.json` and source hashes file. These are explicit generated-source benchmark builds; compiler's ordinary native build command uses C++20, so this report does not claim these flags are the exact normal CLI default. Both A/B arms use identical options.

Canonical workload: HTTP/1.1 keep-alive GET /plaintext, body `Hello, World!`, c=50, wrk 4.2.0, t=2. Each fresh process warm 10 s, measured 15 s, latency output retained. Odd pairs BASE/CAND; even pairs CAND/BASE. Initial N=7 extended to N=10 because median effect was within 3%.

Every process identity-gated before and after load: systemd MainPID, :8080 listener PID, /proc/PID/exe, six threads. Binary hash, comm, response headers/body recorded in identity files. Each exact named unit stopped after its run; port-free checked before starting the next. No `pkill -f`.

One stop SSH command timed out after pair 1 CAND had completed and its result was saved. Independent recheck showed inactive service, MainPID=0, no listener/no systemd jobs. Resumed at pair 2 without repeating or discarding valid runs. Console traceback retained. Zero socket errors and zero non-2xx reported in all 20 timed runs. Raw output, request counts and order are retained; no run removed for being slow.

## Individual canonical results

| Pair | Order | BASE RPS | CAND RPS | Paired delta |
| --- | --- | --- | --- | --- |
| 1 | BASE/CAND | 22392.12 | 23210.87 | +3.66% |
| 2 | CAND/BASE | 21825.41 | 21990.86 | +0.76% |
| 3 | BASE/CAND | 21986.34 | 21567.34 | -1.91% |
| 4 | CAND/BASE | 21603.73 | 19224.92 | -11.01% |
| 5 | BASE/CAND | 18713.49 | 22504.47 | +20.26% |
| 6 | CAND/BASE | 21562.73 | 20685.33 | -4.07% |
| 7 | BASE/CAND | 21808.71 | 21401.27 | -1.87% |
| 8 | CAND/BASE | 21530.14 | 21272.93 | -1.19% |
| 9 | BASE/CAND | 20787.89 | 20808.63 | +0.10% |
| 10 | CAND/BASE | 21519.40 | 21767.97 | +1.16% |

| Statistic | BASE | CAND |
| --- | --- | --- |
| Median | 21,583.23 | 21,484.305 |
| Min | 18,713.49 | 19,224.92 |
| Max | 22,392.12 | 23,210.87 |

Median ratio: **−0.46%**. Median paired delta: **−0.55%**. CAND wins **5/10** pairs. At N=7: BASE median 21,808.71, CAND 21,567.34 (−1.11%), 3/7 wins.

Variation includes paired −11% and +20% swings; there is no clean paired signal. The rule forbids rescuing weak/noisy results with a theoretical mechanism advantage. This is canonical-neutral/noisy, not evidence of a reliable tiny gain. Strict decision: **REVERT**.

This session's retained BASE is faster than the historical ~17–18k sessions. Do not treat that absolute change as a compiler improvement: BASE is the same retained commit. Go and Rust were not remeasured; no new cross-language ratio is inferred.

## Mechanism and correctness

Matched local 102-response trace (100 plaintext, one JSON, one unchanged-path 404): **epoll_ctl 308 -> 207**, **writev 102 -> 102**, same correct output. Traces include startup/teardown; no absolute syscall/request percentage is claimed. The 101-call difference matches the 101 ordinary completions targeted by the code. Mechanism is real, but does not deliver a throughput win on this canonical workload.

Separate post-A/B diagnostic counters are recorded in `r85-independent/remote-mechanism.txt`: at the **300,000-completion checkpoint, 300,000 attempts completed without fallback and zero armed EPOLLOUT**. This instrumented binary did not participate in the timed A/B. The counter is explicitly `no_fallback`, not a direct EAGAIN/partial-write syscall count, and reports cumulative checkpoints rather than the exact measured-request denominator.

Pre-benchmark final candidate validation: Release build; CTest **16/16**; focused network fixtures **27/27 default + 27/27 reactor**; repeated keep-alive/JSON/404; delayed-reader 8 MiB body; 50 pipelined JSON responses; peer disconnect during large output followed by successful new request. Existing focused fixtures cover route/header semantics, coexistence with request_stream, and stop/drain. Scripts/logs retained. Initial restricted-sandbox socket failures were environmental; socket-enabled runs passed.

Full GCC/Clang/-Werror/sanitizer and 294/294 retention walls were **not run for this candidate**, as expressly requested when it does not win. The retained main's existing certification remains unchanged. No Go control was required after REVERT.

## Interpretation and final closure

Framework-source observation: inspected Drogon/Trantor attempts same-loop writes without a mandatory fresh OUT event; Crow's current ordinary small-response path directly uses synchronous Asio writes. Strut-specific inference: keeping the safe completion batch while removing one readiness transition could plausibly help. Experiment: that precise bounded change removed work but had no convincing canonical benefit.

This is distinct from W (inline callback execution, +6.7% but blocking isolation lost) and X (worker-side writable arm, −10.5%). None of these alone mathematically bounds all future architectural designs. Together with retained O/Q/R/T, allocation/lifetime evidence, and this independent horizontal review, they leave no compelling bounded canonical candidate for this campaign.

**R8.5 CLOSED.** Preserve all retained commits, source-semantics fixes and independent review. The remaining Rust gap is acknowledged. No new R8.5 performance candidate, no public execution API redesign, and no R9/R10/FFI/comptime/freestanding work undertaken.

Final cleanup verification: both hosts have no :8080 listener; no r85iw services/processes on server and no wrk process on generator. Rebuilt the reverted isolated compiler and its emitted server C++ is byte-identical to the corrected BASE (`cmp` passed). Main still 0e95d0d; pre-existing stash and untracked caches preserved. Both Linodes retained.
