# R8.5-V feasibility gate — stable header backing / lazy values: ABORTED (canonical-neutral, disproportionate)

Requested: determine the smallest representation change letting read-only HTTP headers
avoid independent owned-value strings, else abort and pick another target.

## Findings
1. `http_request.headers` is DSL-typed `map<string,string>`; emitted reads like
   `req.headers[k]` are `string` VALUES in expressions (print/compare/assign/`.length`).
   Whatever the container does internally, a READ must yield a `string` -> materialization
   is required at the read site. A pure span cannot be observed as a `string` without
   constructing one.
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

## R8.5 plateau assessment (next target)
The request-path structural wins are now largely exhausted: serializer (+8.4%), pump
copy (M +4.6%), last copy (N +2%), header construction (O), flat headers (R +3.4%), route
index (Q, scaling), cancellation (T ~0-2%). Remaining canonical cost per the R8.5-F/G/H/J
evidence is dominated by syscall/synchronisation/preemption (recv ~1.92, writev ~0.96,
eventfd ~0.96, futex ~1.34 per request; reactor involuntary csw ~0.44/req) and socket
wall-time -- not by a clean removable user-space layer. Candidate bounded experiments that
remain: (a) a single futex/dispatch change was already tried (R8.5-I, neutral + correct);
(b) deeper syscall batching risks the R8.5-A correctness class.

Recommendation: R8.5 is near its exit criterion B -- remaining measured bottlenecks
require disproportionately invasive redesign, and the obvious high-value architectural
work is done. Current same-session control: Strut ~mid/high-80%s of frozen Go at c=50
(healthy sessions), Go ~19-20k, Rust >=35k (generator-limited floor). Document and move on
unless a specific bounded syscall/sync experiment is chosen.