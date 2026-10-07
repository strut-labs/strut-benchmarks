# R8.5-U — request cancellation token escape/lifetime: certified by source; deeper cancellation PARKED

Question: can a callback retain `request.cancellation` and observe it after the callback
returns / across keep-alive? Does shared ownership do real semantic work?

## Source-certified answer: YES, tokens escape and must stay meaningful
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
=> A retained token must outlive the callback/request; the state cannot be a resettable
connection-embedded object. Shared ownership is required.

## A runtime fixture was NOT added (documented limitation)
A DSL fixture that retains the token in a worker and waits for cancellation risks deadlock
(the worker must be joined; the request-scope cancel may run after the join) and the DSL
has no timed/optional channel receive, so it cannot be made hang-proof. Per the reviewer's
allowance, escape semantics are certified by source inspection + the existing
cancellation.p copy/observe fixture rather than an unsafe new test.

## Consequence for allocations #2/#3
The per-request `make_shared<strut_cancellation_source>` + its inner
`make_shared<state>` cannot be replaced by connection-embedded/reset state. A safe
reduction would need a SERVER-ONLY co-allocated source/state (one allocation, public
`cancellation_token` aliasing the state via an internal server owner), touching
`conn->cancellation`, the pump/worker/stream/stop paths. Expected benefit is one
allocation/request, which our campaign has repeatedly shown to be neutral-to-small for
throughput (R8.5-G/I/K flat; R8.5-T ~0-2% and now already banked).

## Decision: PARK deeper cancellation
Bank the easy win (R8.5-T). The remaining #2/#3 reduction needs a lifetime-sensitive
server-only ownership design for an expected small gain; not justified now. Revisit only
if cancellation shows up as a dominant cost in a future realistic profile.

## Next structural target (recommended)
Return to an open Rust-style gap with clearer headroom, e.g. the header path's still-owned
values for LONG/non-SSO headers (S0 showed real allocator growth + throughput decline as
values grow), or stable request-head backing with lazy value materialization, chosen by
current roadmap priority rather than reopening finished checkpoints (indexed router Q is
done).