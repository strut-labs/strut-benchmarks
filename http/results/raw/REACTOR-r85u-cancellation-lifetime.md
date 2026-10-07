# R8.5-U — request cancellation token escape/lifetime: certified by source; deeper cancellation PARKED

Question: can a callback retain `request.cancellation` and observe it after the callback
returns / across keep-alive? Does shared ownership do real semantic work?

## Source audit (suggests escaping lifetime; NOT yet behaviorally certified)
- `strut_cancellation_token` copy = `shared_ptr<strut_cancellation_state>` share (token
  holds `state_`; `source.token()` returns a token sharing the source's state). Copies are
  cheap and share the SAME state; the existing `fixtures/concurrency/cancellation.p`
  already copies a token into a worker and observes cancellation across threads.
- Legacy path: `request_scope` dtor calls `source_->cancel()` when the request completes
  -> a retained token observes `cancelled()==true` after the callback returns.
- Reactor path: `conn->cancellation->cancel()` on client disconnect/error (line 1842) and
  on server stop (request_stop); each request dispatch allocates a NEW
  `make_shared<strut_cancellation_source>()`, so a token retained from request N keeps its
  own state and is NOT cancelled by keep-alive request N+1 (generation independence is
  natural, because the source is per-request, not per-connection).
=> The source STRONGLY SUGGESTS retained tokens are designed to survive their request
object (shared_ptr state, per-request source, legacy cancel-on-scope-exit), but this is a
capability inference, not yet a demonstrated language/runtime contract. A behavioral
escape fixture is required (below).

## Behavioral certification (deterministic escape fixture)
fixtures/concurrency/cancellation-escape.p: a callback does
`escaped.send(request.cancellation)` on a `channel<cancellation_token>`; the client runs
on its own thread; main receives the token and `client.join()`s (guaranteeing the request
completed) before inspecting. Result:
- reactor (STRUT_HTTP_REACTOR=1): status200, retained.cancelled()==0 after completion ->
  the token ESCAPES and stays VALID (no dangling); escape is real, not just a source
  capability.
- legacy (default mode): same program prints retained.cancelled()==1 (the `request_scope`
  dtor cancels the source on scope exit).

## DISCOVERED SEMANTIC DIVERGENCE (flagged; possible correctness bug)
Post-completion `cancelled()` on an escaped request token DIFFERS by mode:
- legacy: becomes cancelled (~ `request_scope` destructor calls source->cancel()).
- reactor: remains uncancelled (normal buffered completion does not cancel the per-request
  source; only disconnect(1842)/stop/stream cancel).
This is user-observable (retained token). Recorded, NOT hidden. It is a cancellation-
correctness question, out of the R8.5 performance scope; needs a decision (should reactor
match legacy, or is cancel-on-completion legacy-only?). No new behavior was designed
around it.

## Consequence for allocations #2/#3
The per-request `make_shared<strut_cancellation_source>` + its inner
`make_shared<state>` cannot be replaced by connection-embedded/reset state. A safe
reduction would need a SERVER-ONLY co-allocated source/state (one allocation, public
`cancellation_token` aliasing the state via an internal server owner), touching
`conn->cancellation`, the pump/worker/stream/stop paths. Expected benefit is one
allocation/request, which our campaign has repeatedly shown to be neutral-to-small for
throughput (R8.5-G/I/K flat; R8.5-T ~0-2% and now already banked).

## Decision: PARK deeper cancellation (reason: complexity vs evidence, not assumed payoff)
Bank the easy win (R8.5-T). The remaining #2/#3 allocations participate in shared
lifetime semantics; removing them safely appears disproportionately invasive
(server-only co-allocation / aliasing ownership / generation machinery) relative to the
current evidence, while other structural targets have stronger measured headroom. This
is a scope decision, NOT a claim that removing them would be neutral -- the campaign has
seen whole-layer allocation/ownership removals (serializer, M, N, O, R) produce real
wins.

## Next structural target (recommended)
Return to an open Rust-style gap with clearer headroom, e.g. the header path's still-owned
values for LONG/non-SSO headers (S0 showed real allocator growth + throughput decline as
values grow), or stable request-head backing with lazy value materialization, chosen by
current roadmap priority rather than reopening finished checkpoints (indexed router Q is
done).