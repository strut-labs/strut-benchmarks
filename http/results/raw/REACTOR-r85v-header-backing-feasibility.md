# R8.5-V feasibility gate — stable header backing / lazy values: ABORTED (canonical-neutral, disproportionate)

Requested: determine the smallest representation change letting read-only HTTP headers
avoid independent owned-value strings, else abort and pick another target.

## Findings
1. `http_request.headers` is DSL-typed `map<string,string>`; emitted reads like
   `req.headers[k]` are `string` values in expressions. A codegen-aware proxy/container
   could in principle preserve language-level string semantics while delaying
   materialization -- lazy values are NOT fundamentally impossible. The real obstacle is
   payoff, not feasibility (below).
2. Therefore storing values as spans into a stable backing only benefits requests that
   NEVER read/iterate the value (e.g. /plaintext). It shifts allocation from parse to
   first-read for handlers that DO read headers.
3. Canonical `/plaintext` uses short header values (Host + wrk headers) that fit `string`
   SSO -> they already require ~no heap allocation (confirmed by S0). So backing/lazy
   values buy ~nothing on the PRIMARY canonical scoreboard; they help only long/non-SSO
   values (the 8x256B synthetic case the strategy says NOT to optimize canonical for).
4. A correct lazy container needs: request-OWNED stable backing (a self-contained buffer,
   since a raw pointer to a sibling member breaks on move; entries store offsets),
   per-entry lazy "owned-on-first-access" values, mutation promotion, iteration semantics
   that still yield `.first/.second` pairs, plus equality/conversion. That is a moderate
   container+representation rewrite.

## Verdict: ABORT V
Disproportionate complexity for a canonical-neutral benefit (short values are SSO). The
net would help only long-value pass-through workloads, which the strategy explicitly
deprioritises relative to the canonical scoreboard. No implementation attempted.

## R8.5 status
Request-path structural wins retained: serializer (+8.4%), pump copy (M +4.6%), last copy
(N +2%), header construction (O), flat headers (R +3.4%), route index (Q scaling),
cancellation (T ~0-2%). Remaining measured cost is dominated by syscall +
synchronisation/scheduling activity (recv ~1.92, writev ~0.96, eventfd ~0.96, futex ~1.34
per request; reactor involuntary csw ~0.44/req). This does NOT by itself prove the space
is exhausted -- the scheduling topology is the prime remaining suspect and is tested by
R8.5-W.