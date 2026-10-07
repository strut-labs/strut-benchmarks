# R8.5 → next roadmap: handover

Status: **R8.5 (Linux HTTP/reactor hot-path performance) is CLOSED.**

## Final retained compiler
- Commit: **0e95d0d** (Strut 0.0.3 line).
- Retained ancestry: `beed5ba` (route matcher cleanup), `87e00ff`+`80556b4` (direct
  response serializer + bounded reserve), `73d379a` (pump copy/copy-back removal),
  `da4a8f2` (final buffered request copy removal), `51771f9` (direct/range-guided
  header construction), `56ea341` (order-preserving indexed router), `5c647bf`+`a08fea5`
  (flat `strut_http_headers` + equality/assign fix-forward), `0e95d0d` (null-safe default
  cancellation_token placeholder).
- Legacy remains the default; reactor is behind `STRUT_HTTP_REACTOR=1`.

## Final benchmark report
- `strut-benchmarks/http/results/raw/REACTOR-r85-final-report.md` (commit `1b28c09`).

## Retained architectural changes (with measured effect)
- R6.5 writev (early).
- R8.5-E serializer ~+8.4% c=50 (7/7).
- R8.5-M pump copy removal ~+4.6% (7/10).
- R8.5-N last buffered copy removal ~+2% (7/10).
- R8.5-O header construction: +1.6% canonical, +22.6% @ 8-extra-header (5/5).
- R8.5-Q indexed router: 1000-route exact-last ~2.5x, param ~2.8x, miss +37%; N=1 neutral.
- R8.5-R flat header container: +3.4% canonical (6/6), +7.1% @ 8-extra-header (5/5).
- R8.5-T null-safe default token: small positive (~0-2%, mechanism: 1 eager alloc/request
  removed).

## Known unresolved semantic notes (deliberately NOT changed in R8.5)
1. **Cancellation completion divergence** — an escaped `request.cancellation` token's
   post-completion `cancelled()` differs: legacy `true` (request_scope dtor cancels its
   source), reactor `false` (normal buffered completion does not cancel the per-request
   source). Unresolved API/correctness question; needs a deliberate decision. Evidence:
   REACTOR-r85u-cancellation-lifetime.md; fixture
   strut-regression-suite/fixtures/concurrency/cancellation-escape*.{p,json}.
2. **V — stable header backing / lazy values: PARKED** (poor expected CANONICAL payoff:
   short values are SSO; canonical /plaintext doesn't consume header values; a correct
   lazy representation needs a moderate runtime/codegen change). Evidence:
   REACTOR-r85v-header-backing-feasibility.md.
3. **Deeper cancellation ownership (allocations #2/#3): PARKED** — participation in shared
   lifetime semantics makes safe removal disproportionately invasive. Evidence:
   REACTOR-r85u-cancellation-lifetime.md.
4. **Scheduler topology**: fully-removed handoff (W diagnostic) = +6.7% upper bound;
   production-safe completion half (X) = -10.5% (reverted). No cheap production-safe win;
   the handoff is not the ~2x Rust gap. Evidence: REACTOR-r85w / -r85x.

## Current benchmark standing (same-session, healthy)
- Strut canonical /plaintext c=50: ~17-18k. Frozen Go: ~19-20k -> Strut ~mid/high-80%s of
  Go (session-dependent). Frozen Rust: >=35k historical, generator-limited floor.
- Strut has NOT reached Rust-class canonical throughput.

## Regression suite
- `strut-regression-suite`: **294/294 default + 294/294 reactor** (includes request.headers
  map-op certification, exact-route-key non-collision, cancellation escape/lifetime).

## Next roadmap checkpoint
- Return to the planned Strut roadmap; no further Linux HTTP/reactor performance work
  unless a future independent investigation produces genuinely new evidence.
- Infrastructure: both Linodes retained, services stopped while idle. Preserve
  stash@{0}, dogfood/__pycache__/, tools/__pycache__/, /tmp/strut-site-main; no destructive
  git, no `pkill -f`.