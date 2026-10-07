# R8.5-F — scoped phase-attribution: COMPLETED (see REACTOR-r85f-attribution.md)

SUPERSEDED: clean phase attribution was completed. See REACTOR-r85f-attribution.md
(per-phase ns/sampled) and REACTOR-r85g-parse-flat.md (parse candidate A/B neutral,
reverted). Main repo remains pristine at 80556b4.

# R8.5-F — scoped phase-attribution: status (honest)

Repository/index-state incident resolved: the beed5ba baseline checkout had
staged a rollback in the index; `git restore --staged` fixed it. HEAD ==
worktree == 80556b4 (normal, GCC/Clang -Werror, ASan walls 16/16; regressions
289/289 both modes). The serializer R8.5-E isolated A/B (13c3f67) predates a
phantom Rust server that later held :8080 and is NOT affected by it; that A/B
stands (c=50 +8.4%, 7/7 pairs).

## Scoped attribution attempt
Temporary env-gated (STRUT_PHASE_PROFILE) phase counters were added to the
emitted runtime (parse/route/callback/serialize ns buckets + periodic dump). Two
issues prevented clean data in-session:
1. SSH/process plumbing on node A became unreliable (wedged control channels,
   failed binary transfers "Text file busy").
2. A leftover Rust benchmark process (strutbench-http) had re-occupied :8080,
   so the final diagnostic wrk samples were served by Rust, not Strut.

Both are infrastructure, not runtime defects. The instrumentation was reverted;
the working tree is clean at 80556b4.

## Formal state
- Per-phase allocation/time attribution for a /plaintext request: PENDING
  (the interposer is abandoned; perf gave no usable symbols; the runtime scoped
  counters were blocked by node flakiness). Re-attempt with:
   (a) a clean node session,
   (b) CPU/kernel-bandwidth-per-phase via the temporary counters OR
   (c) temporarily stubbing one phase at a time (diagnostic-only).
- The request-parser/header cost remains a code-inspection hypothesis, NOT an
  attributed largest source. It must not be selected as R8.5-G without
  attribution.
