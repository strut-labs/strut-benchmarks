# R8.5-T — null-safe default cancellation_token (remove eager per-request state alloc): KEPT

Audit (a08fea5): per ordinary buffered request the runtime allocated cancellation state
~3x even though the `/plaintext` callback never observes `req.cancellation`:
1. parse: `strut_http_head_result`/`strut_server_request` default-constructs
   `strut_cancellation_token` -> `make_shared<strut_cancellation_state>` (then
   overwritten by the connection token in the worker);
2. pump dispatch: `conn->cancellation = make_shared<strut_cancellation_source>()`;
3. that source's ctor: another `make_shared<strut_cancellation_state>`.
User code may also construct `cancellation_source`/`cancellation_token` as STACK VALUES
(fixtures do), so a merge of source+state via `shared_from_this` is UNSOUND
(`bad_weak_ptr` when a stack source calls token()) -- that approach was tried and
reverted.

Bounded T (safe): a default-constructed `strut_cancellation_token` no longer allocates
(`state_` null); `cancelled()/wait()/throw_if_cancelled()/subscribe()` are null-safe.
This removes allocation #1 (eager state at parse time for every server request), which
was always immediately discarded. The connection token (source + its state) is
unchanged; request_stream/response_stream/WebSocket/disconnect/stop cancellation paths
untouched. (Merging source+state to remove allocation #3 is blocked by stack usage of
`cancellation_source`.)

## Correctness — full retention wall (green)
- CTest 16/16 normal, GCC -Werror, Clang -Werror, ASan/UBSan.
- Regressions 291/291 default + 291/291 STRUT_HTTP_REACTOR=1, incl. cancellation
  fixtures (unified cancellation source+token, cancellable blocking process streams) and
  stream/WebSocket fixtures.

## Mechanism
Default token no longer allocates a state: one cancellation-state allocation removed per
buffered request. (Exact allocator delta not separately re-measured this session;
mechanism is a direct code-path removal.)

## Throughput — same-session warmed identity-gated A/B (BASE a08fea5)
| workload                  | base median | T median | delta | pairs |
|---------------------------|-------------|----------|-------|-------|
| /plaintext c=50 (n=10)    | ~16905      | ~17210   | +1.8% | 9/10  |

Consistent positive (9/10 paired wins); modest magnitude. Mechanism + simplicity +
consistency justify KEEP.

## Semantic repair (fix-forward 0e95d0d, Option B)
The first T (2337434) changed PUBLIC default `cancellation_token` semantics (null
state -> wait() returned immediately, subscribe() empty). Default construction is legal
in the DSL (`cancellation_token t;`) and observable. Fix-forward restores the allocating
default ctor (cancelled false, blocking wait, live subscribe) and adds an INTERNAL
`strut_cancellation_no_state_t` tag used ONLY by `strut_server_request`'s cancellation
placeholder (member initializer). The placeholder is replaced from
`conn->cancellation->token()` / `request_scope source_->token()` before any callback;
audited all 4 callback paths (buffered worker, request_stream, websocket, legacy
request_scope) + pump dispatch sets `conn->cancellation` first. No user-visible request
can observe the placeholder. Hot path is byte-identical to the original T (server
placeholder never allocated in either).

Certification after repair: full strict wall CTest 16/16 normal + GCC -Werror + Clang
-Werror + ASan/UBSan; regressions 292/292 default + 292/292 reactor (added
fixtures/concurrency/cancellation-default-token.p asserting default token cancelled()==false
and no throw). Coverage limitation (documented): (a) `token.subscribe(...)` is NOT
language-visible (runtime-internal), so no DSL fixture; (b) a default token's `wait()`
blocks forever (no source to cancel it) and the DSL has no timed/optional channel receive
without blocking, so proving default-wait blocking would hang the suite -- not safely
testable; the restored allocating constructor + cancellation.p (which proves wait()
blocks then returns on real cancellation) cover it as far as safely possible.

## Decision: KEEP (repaired)
Committed as 0e95d0d (main), superseding 2337434. Public semantics preserved; one eager
parse-time cancellation-state allocation removed per buffered request. Retained stack: beed5ba, 87e00ff/80556b4, 73d379a, da4a8f2,
51771f9, 56ea341, 5c647bf, a08fea5, 2337434.

## Remaining / next
- The per-request `make_shared<strut_cancellation_source>` (alloc #2+#3) still exists for
  buffered requests; eliminating it requires either connection-embedded cancellation
  (safe only if token retention/escape semantics allow reset/generation) or a
  codegen-aware lazy escape promotion -- a larger, lifetime-sensitive step.
- S remains deprioritized (long-value headroom, invasive proxy). Cross-language control
  unchanged (Strut mid/high-80%s of frozen Go, session-specific).