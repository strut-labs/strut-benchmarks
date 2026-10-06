# R8.5 / early-R13 kickoff — fresh post-R8 profile (1-vCPU)

Compiler: R8 (417e197). c=50 /plaintext ~16k rps.

## Syscalls/request (perf stat, 6s)
- recvfrom ~1.92 (one real read + drain-EAGAIN)
- writev ~0.96 (coalesced head+body - the R6.5 win persists)
- write (eventfd wake) ~0.96 (one completion wake per request)
- futex ~1.51
- epoll_wait amortized (~1290/s)
- total ~5.5 syscalls/request

## CPU profile (top symbols, % of samples)
- strut_reactor::wait 6.49 (epoll_wait)
- kernel timespec64_add_safe 6.14
- run_reactor_server (loop) 6.14
- kernel next_expiry_recalc 5.48 (hrtimer/timer wheel)
- apic_timer_interrupt 4.94
- mem_cgroup / msr / sched_out / dequeue_entity ~4.9x4
- libc ~4.88
- set_normalized_timespec64 4.60
- libstdc++ steady_clock::now() 4.60  <-- hot clock reads
- std::swap(deque_base::_impl_data) 4.60  <-- completions/ready deque swaps + shared_ptr moves
- __fdget 3.09 (fd lookup in syscalls)

## R8.5 target lines (evidence-first)
1. steady_clock::now() per loop iteration/deadline refresh (~4.6%).
2. Kernel epoll/hrtimer per-wait setup (timeout to ~50ms every iteration) +
   the deadline scan (~30% kernel). Reducing per-iteration timer work.
3. std::swap of the shared_ptr<connection> deques (~4.6%).
4. reduce syscalls/request: drain-EAGAIN recv, eventfd wake, futex.

## Ledger (retained so far)
original ~1.2k, TCP_NODELAY ~9k, first reactor ~11-12k, +writev ~16.8k,
R7/R8 stable ~16k (steady), Rust >=35k generator-limited floor, Go ~24k.
A/B each R8.5 change; N>=5 median/min/max; keep/revert.
