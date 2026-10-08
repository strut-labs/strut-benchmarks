# R8.5 independent architecture review

Date: 2026-10-08. Retained compiler: `0e95d0d5062f55a7a3c051e7311e26acc2e90a44`.

**Final verdict: CLOSE R8.5.** The independent review initially recommended one final candidate: optimistic reactor-local writes during the ordinary completion batch drain. It was tested after explicit upload approval: N=10 alternating canonical pairs gave −0.46% median RPS, 5/10 paired wins. Candidate reverted; compiler main unchanged. Full result: [immediate-write experiment](REACTOR-r85-immediate-write-result.md).

## Evidence and scope

Read the final report, H CPU/wall, J futex/context switches, K allocation attribution and rejected move, L clock, O head construction, P/Q routing, R headers, T cancellation repair, W inline diagnostic, X direct arm, and the handover. Retained findings stand: wall attribution is preemption-sensitive; clock/wake tweaks are exhausted; indexed routing fixed the actual scaling defect; flat headers preserve map semantics; default public cancellation semantics must remain intact. No repeated profiler campaign or second candidate.

Current framework source fetched once into `/tmp/r85-frameworks`, with these immutable revisions:

| Source | Inspected revision |
| --- | --- |
| Crow | `539a2671be720c1fd539cece08777628a71a005a` |
| Drogon | `4d078eeab6805c82e8e109479bc52beda4c0a2db` |
| Trantor (transport inspected separately) | `a9e15161d092301d49e67e89ae3c29ca4f05c27e` |
| oatpp | `f83d648fd82dc222ef88aabbafb68efbd7d7bf50` |

These are branch heads fetched on the review date, not a matched Drogon release and its pinned Trantor submodule. Transport conclusions describe the inspected Trantor revision. Framework throughput was not measured. No inference that C++ reaches the historical Rust floor is presented as a result.

## 1. Strut hot path

```text
reactor/main: accept -> connection(shared_ptr), nonblocking socket, epoll IN
  -> recv loop -> connection input string -> head substring/custom parser
  -> owned request strings + flat headers -> exact index / parameter trie
  -> disable socket interests (epoll MOD) -> ready deque / mutex / CV
app worker: move request -> ordinary synchronous callback -> response
  -> direct head serialization + body copy to connection
  -> completed deque / mutex -> eventfd wake
reactor: swap completion batch -> epoll MOD writable
  -> epoll_wait returns OUT -> writev head/body (offsets for partial writes)
  -> finish: close OR erase consumed input, reset flags, epoll MOD readable
  -> pump any already buffered next request
```

Exact source: `strut/src/generated_runtime.cpp`: reactor backend around 1140–1200; connection/state around 1417; `reactor_build_response` 1525; `reactor_finish_write`/`reactor_flush` 1552 onward; parser/routing/dispatch in `reactor_pump` 1570 onward; `reactor_worker_loop` 1783; completion drain 1829. Line references describe retained 0e95d0d.

One-vCPU normal reactor configuration has main/reactor + one ordinary worker + four stream workers = six threads (last four idle for plaintext). Connection/parser/output state stays in a shared connection; request ownership moves to the callback. The callback may block without blocking socket processing. Response writing stays on the reactor. Linux interest masks are level-triggered; no EPOLLET/EPOLLONESHOT. Normal tiny response pays three MODs: disable read for dispatch, arm write, restore read. Input/output strings are connection members, but request/header construction and moves do not preserve a reusable connection-local request header vector across calls. Two shared cancellation allocations remain for token escape/lifetime reasons.

## 2. Crow hot path

```text
accept io_context -> choose connection worker io_context
worker: async read -> embedded node/http-parser wrapper -> owned request
  -> routing trie -> ordinary handler on this io_context
  -> response header buffer vector + body swap
  -> do_write_general -> do_write_sync -> asio::write
  -> clear response/buffers/parser request -> next async read
```

Sources: [server](https://github.com/CrowCpp/Crow/blob/539a2671be720c1fd539cece08777628a71a005a/include/crow/http_server.h), [connection](https://github.com/CrowCpp/Crow/blob/539a2671be720c1fd539cece08777628a71a005a/include/crow/http_connection.h), [parser](https://github.com/CrowCpp/Crow/blob/539a2671be720c1fd539cece08777628a71a005a/include/crow/parser.h), [routing](https://github.com/CrowCpp/Crow/blob/539a2671be720c1fd539cece08777628a71a005a/include/crow/routing.h).

`app.h::concurrency` clamps to at least two; server runs concurrency-minus-one connection io_context workers plus the accept context, with additional maintenance activity. Thus setting one does not mean a single server thread. Accept assignment is a connection-level handoff, not reactor->callback->reactor on every request. Shared connection lifetime supports deferred completion. Normal callbacks run on the connection worker; blocking one stalls that worker's connections. Deferred responses do not automatically make arbitrary blocking callbacks safe.

Important current-source detail: `do_write_general` uses **synchronous** `asio::write` for normal small responses. The file also contains `do_write` using `async_write`, but that is not evidence that the ordinary tiny-body path always waits for EPOLLOUT. This is a direct write, with synchronous backpressure semantics, not the exact safe nonblocking fallback proposed for Strut. Do not copy that blocking behavior.

Parser feeds directly from read buffers but accumulates URL/header/body strings; it inserts owned header fields into the request container. `HTTPParser::clear` assigns `req = crow::request()`, rather than demonstrating reuse of all header allocations. Response/vector members are cleared and body ownership swapped. No universal arena/pool or zero-allocation request path was established. Routing uses a trie; Strut already has indexed routing. Asio backend masks and speculative-write behavior are dependency/platform details, so exact epoll MODs/request are not claimed from Crow source alone.

## 3. Drogon / Trantor hot path

```text
accept loop -> assign TCP connection to I/O event loop
owning loop: read into MsgBuffer -> connection HttpRequestParser
  -> custom parse, request from parser-local pool -> indexed/controller routing
  -> callback-style handler (may complete now or asynchronously)
  -> sendResponse/renderToBuffer -> TcpConnection::send
  -> same-loop sendInLoop -> immediate write when no outstanding output
  -> unsent bytes in buffer nodes; write interest on backpressure
  -> pool request after final reference release; parser reset; keep reading
```

Sources: [HTTP server](https://github.com/drogonframework/drogon/blob/4d078eeab6805c82e8e109479bc52beda4c0a2db/lib/src/HttpServer.cc), [request parser](https://github.com/drogonframework/drogon/blob/4d078eeab6805c82e8e109479bc52beda4c0a2db/lib/src/HttpRequestParser.cc), [request reset](https://github.com/drogonframework/drogon/blob/4d078eeab6805c82e8e109479bc52beda4c0a2db/lib/src/HttpRequestImpl.h), [response renderer](https://github.com/drogonframework/drogon/blob/4d078eeab6805c82e8e109479bc52beda4c0a2db/lib/src/HttpResponseImpl.cc), [TCP transport](https://github.com/an-tao/trantor/blob/a9e15161d092301d49e67e89ae3c29ca4f05c27e/trantor/net/inner/TcpConnectionImpl.cc).

Framework thread count defaults to one I/O loop thread (`threadNum_`), in addition to main-loop activity; database/plugin/logging configuration can add threads. It is not a guarantee of one total process thread. Parse, ordinary dispatch, and same-loop completion are connection-affine. A completion arriving elsewhere uses loop queuing. Trantor loop wakeup uses eventfd on Linux; no unconditional request handoff to a generic callback worker. Ordinary synchronous blocking user code still blocks the I/O loop. Async callbacks/coroutines allow suspension; blocking work must be explicitly arranged elsewhere. This is an execution contract difference, not evidence of an automatic public two-class handler scheduler in all three libraries.

`HttpRequestParser::makeRequestForPool` has a shared_ptr custom deleter: after the last reference, reset and return the request to that parser's pool. Off-loop release queues the reset on the owning loop. This safely handles escaping request references. Reset clears owned header/cookie/parameter containers and strings; pools do not remove all header-node or control-block allocations. Headers are owned `SafeStringMap<std::string>`, not universal borrowed spans. Custom parsing from MsgBuffer still materializes fields. Exact/controller route maps and parameter regex paths are not universally cheaper than Strut's trie.

`HttpServer::sendResponse` asserts loop ownership and calls render/send. `TcpConnectionImpl::sendInLoop` tries `writeInLoop` immediately if not already writing and no queued output; unsent bytes enter buffer nodes. EpollPoller uses normal level-triggered channel interests, not a universal edge/oneshot trick. Write registration follows buffered output; there is no mandatory fresh writable-readiness round trip for each tiny successful send. Request locality and optimistic sending are separate advantages.

Rendering allocates a MsgBuffer for ordinary uncached responses, assembles headers and copies body. Explicit cacheable responses may reuse serialized data (with Date handling). This is not a default free response template for arbitrary dynamic user output. Strut already avoids stream-based formatting and uses writev instead of concatenating head+body into one send buffer.

## 4. oatpp models

```text
simple: accept -> detached connection thread -> blocking read / custom header parser
  -> router endpoint handle -> outgoing Response::send -> keep-alive task loop
async: accept -> Executor submits HttpProcessor::Coroutine
  -> nonblocking buffered read/parse -> handleAsync -> sendAsync
  -> retry/action on I/O wait -> I/O worker readiness -> coroutine continuation
  -> onRequestDone -> clear request/response -> parse next request
```

Sources: [simple handler](https://github.com/oatpp/oatpp/blob/f83d648fd82dc222ef88aabbafb68efbd7d7bf50/src/oatpp/web/server/HttpConnectionHandler.cpp), [processor](https://github.com/oatpp/oatpp/blob/f83d648fd82dc222ef88aabbafb68efbd7d7bf50/src/oatpp/web/server/HttpProcessor.cpp), [executor](https://github.com/oatpp/oatpp/blob/f83d648fd82dc222ef88aabbafb68efbd7d7bf50/src/oatpp/async/Executor.cpp), [epoll worker](https://github.com/oatpp/oatpp/blob/f83d648fd82dc222ef88aabbafb68efbd7d7bf50/src/oatpp/async/worker/IOEventWorker_epoll.cpp), [HTTP types](https://github.com/oatpp/oatpp/blob/f83d648fd82dc222ef88aabbafb68efbd7d7bf50/src/oatpp/web/protocol/http/Http.hpp).

Simple mode has approximately one accept thread plus c connection threads (about 51 at c=50), even on one CPU; it preserves blocking-handler isolation per connection without a separate callback completion queue. Async mode separately configures processor, I/O, and timer workers. Suggested one-CPU counts resolve to one of each, plus server accept activity; it is not a single-loop locality model equivalent to Drogon. I/O worker handoffs use task queues/wakes; naive workers use condition variables; Linux event worker uses eventfd and EPOLLET|EPOLLONESHOT socket actions. Coroutine suspension avoids running blocking I/O on processor workers, but arbitrary blocking handler code still occupies a processor thread. An async endpoint is explicitly `handleAsync`, unlike the ordinary endpoint.

Request/response objects use shared ownership; per-connection buffered stream/readers are reused, and request/response pointers reset per request. `Headers` is `LazyStringMultimap<StringKeyLabelCI>` with MemoryLabel-related parser fields. The inspected blocking header reader accumulates into a buffer and calls parsing with null memory ownership; do not infer all stored headers are zero-copy long-lived socket views. Arena/pool savings depend on type/build configuration and are not measured here. Response sends immediately through stream abstraction; async actions defer on inability to progress rather than requiring Strut's blanket completion-arm-OUT sequence. This is a contrasting viable architecture, not proof EPOLLONESHOT saves syscalls: one-shot actions themselves require rearming.

## 5. Concrete architectural differences / ranking

| Rank | Strut current work / exact path | Competitor work / exact path | Extra work and target |
| --- | --- | --- | --- |
| **B, only experiment** | ordinary completion drain always `modify(false,true)` before `reactor_flush` | Trantor `sendInLoop` first writes; Crow `do_write_general` writes directly | avoid one MOD and OUT dispatch on successful tiny sends; canonical and scaling; plausible 3–10%, unmeasured |
| C | `reactor_worker_loop` always executes callbacks separately | Drogon loop-local dispatch; Crow connection io_context handler | queue/CV/mutex/eventfd, cache movement; workload/scaling redesign under explicit nonblocking contract |
| C | `reactor_pump` creates parsed head, assigns it; worker moves owned request away | Drogon `makeRequestForPool/reset` delays reuse until last shared reference | request storage/capacity churn; workload-specific, no strong >3% canonical evidence after O/R/T |
| C | parser copies head substring, owns eagerly normalized string headers | oatpp labels/lazy map; Drogon still owned headers; Crow string accumulation | header-heavy potential, already V/S0 territory and semantic complexity |
| C | response head formatted on each response | Drogon cacheable `renderToBuffer` reuses explicit cached response | cacheable endpoints only; cannot transparently cache arbitrary responses |
| D | `reactor_build_response` copies response body to out_body | Crow body swap; Drogon ordinary render appends body | large-body ownership opportunity, plaintext SSO copy too small for a new checkpoint |
| D | level-triggered epoll + dispatch-disable/read-restore | Drogon also level-triggered; oatpp event-worker oneshot | no evidence that flag swap alone reduces request syscalls; different state/ownership design |
| D | flat vector headers; direct serializer/writev; indexed exact/trie routes | competitors also retain allocations, maps, formatting, routing state | already sensible common-case implementation, no missing universal arena or parser magic |

No A candidate (>10% canonical) established. B is a plausibility category, not a predicted measured gain. Locality should not be dismissed as impossible, but it is too invasive and semantically constrained for this last bounded review. W measured +6.7% for its particular inline variant; it did not remove the mandatory writable event. It is strong evidence against explaining the whole Rust gap with callback handoffs, **not a mathematical upper bound on all event-loop architectures**. X's negative result does not test optimistic writes: it still arms OUT, moves MOD onto workers, and removes completion batching. Proposed candidate retains that batching and eventfd.

## 6. One candidate: mechanism, risks, validation

Isolated detached worktree: `/tmp/r85-immediate-write`, based on 0e95d0d. Patch: `r85-independent/immediate-write.patch`.

Change only ordinary worker completion drain: after confirming the connection is live, flush on reactor now; arm writable only when flush reports unsent output. Existing readiness-driven flush remains for backpressure. Make `reactor_flush` return whether it stopped with bytes remaining; callers elsewhere ignore its result. **Do not inspect conn->phase after finish**: keep-alive finish may pump pipelined input and dispatch another callback, which can publish another response concurrently. The explicit return reports the completed flush's outcome without that post-finish state read.

Expected removal: one epoll MOD and subsequent OUT event per immediate full ordinary response. No promised removal of recv/writev/eventfd/futex calls or allocations. Common-path MOD count changes from three to two. Callback dispatch stays on workers; no API change. Complexity low (one completion call site and internal flush result); semantic risk moderate: partial write/EAGAIN, close/disconnect, pipelined dispatch, stop and TLS must preserve existing paths. The same offset-aware nonblocking flush is reused; no synchronous blocking send added. Streams/WebSocket/status paths remain unchanged.

Local initial prototype trace, 100 plaintext keep-alive + JSON + 404:

| | epoll_ctl | writev | functional |
| --- | --- | --- | --- |
| BASE | 308 | 102 | pass |
| CAND | 207 | 102 | pass |

The 101-call reduction corresponds to 100 plaintext + one JSON ordinary completion; 404 uses the unchanged status path. `strace -f` counts include listener/connection setup/teardown. This proves mechanism, not performance. Raw result in `r85-independent/local-mechanism.json`. Prototype was then hardened with the explicit flush return described above; final rerun recorded separately below.

Candidate Release build and CTest: 16/16 initial prototype. Focused local network fixtures: 27/27 reactor prototype. Initial sandboxed network runs failed because sockets were prohibited; socket-enabled rerun passed. Final patch checks are recorded in the validation note. No claim of full retention wall or canonical A/B success.

Required next measurement: same source/base SHA, same server toolchain/options for both emitted programs, warm and alternating seven or more c=50 pairs on existing server/generator. Gate listener PID/executable identity, six threads, response headers/body, no competitor service running, zero errors; preserve all raw wrk output and server binary hashes. Canonical small writes should improve if this layer matters; slow readers/large responses should fall back without correctness loss. Do not interpret localhost throughput or strace throughput as canonical.

If material repeatable win, run full strict GCC/Clang/-Werror/sanitizer and both full regressions before retention; otherwise discard candidate and close R8.5. No second speculative candidate.

## 7. Rust comparison sanity check

Inspected frozen `http/rust/src/main.rs`, Cargo.toml and benchmark PLAN/environment. Same GET paths/body, ordinary HTTP/1.1 keep-alive, no TLS/compression, release build; Rust plaintext returns `&'static str`, Strut constructs owned response and copies its body into connection output. Rust uses async handler futures rather than an arbitrary synchronous callback worker. Tokio macro requests multithreaded runtime; on the documented one-vCPU node it normally chooses one runtime worker, plus main thread; blocking pool threads can be demand-created. Exact historical process thread count was not independently measured here.

Rust LTO/codegen-units=1/opt-level=3 vs Strut generated -O2 is a build asymmetry, documented rather than normalized away. Header sets are not byte-identical (framework-specific content type/date/connection/server defaults); inspect wire output in any rerun. Axum/Hyper socket options cannot be certified from the benchmark main alone. Rust plaintext static-body construction differs from owned Strut strings; JSON remains ordinary per-call serialization in both. No demonstrated major behavior mismatch invalidates the historical >=35k floor, but it is historical and generator-limited, not a new paired measurement or evidence of how much any single difference contributes. Existing raw matrix/config controls must accompany any renewed numerical comparison.

## 8. Experiment status and closure

During the first review turn, upload of generated BASE/CAND source to `root@96.126.107.155:/root/bench/` was rejected twice by automatic approval review. The stated reason was private source transfer to a public/unverified IP without sufficiently specific payload/destination authorization, despite environment.json and existing campaign identifying it as server Linode 107498466. No transfer occurred in that turn; no workaround attempted. On the follow-up turn the user explicitly approved the exact payload/destination and execution; approved source transfer and canonical measurement then proceeded. See the candidate result report for the final decision.

Both Linodes preserved. SSH read-only check found server :8080 idle. No remote services started. Main remains 0e95d0d; no reset/clean/rebase, no public API redesign, no R9/R10/FFI/comptime/freestanding. The one permitted A/B is now complete and the candidate patch was reversed in its isolated worktree. **Endorse final closure: canonical-neutral/noisy; no further candidate.**

### Final hardened patch validation

- Final Release rebuild and CTest: **16/16 passed** (`r85-independent/r85-ctest-final.log`).
- Focused network fixtures: **27/27 default**, **27/27 reactor**, socket-enabled runs. Final reactor run occurred after the explicit flush-result change; default response path is unchanged.
- Final local strace repeats **308 -> 207 epoll_ctl**, **102 -> 102 writev**, same functional pass. Raw traces retained (`r85-base.trace`, `r85-cand.trace`).
- Additional final generated-code stress check: 8 MiB body with delayed reader, 50 pipelined JSON requests, disconnect during large output followed by successful new request: **passed**. Initial stress assertion assumed compact JSON whitespace and failed; corrected to parse Content-Length and JSON values, then passed. No server code changed for that harness correction.
- Stress build uses the same emitted candidate with only plaintext body changed to 8 MiB and port to 18080. This is a correctness probe, not another performance candidate. Reproduction scripts retained in `r85-independent/` with paths explicitly pointing to temporary generated artifacts.
- `git diff --check` clean. Production main still 0e95d0d. Worktree has only the candidate runtime change. Full strict retention wall intentionally omitted after the neutral/noisy canonical result; no retention candidate remains.

### Baseline provenance correction before canonical measurement

The initial local BASE emitted by the existing `strut/build/strut` was stale: it did not contain all retained O/R/T changes despite source main being 0e95d0d. Before benchmarking, rebuilt exact 0e95d0d in `/tmp/r85-retained-base`; generated BASE/CAND diff now contains **only the candidate**. Recompiled BASE locally and on Linode, reran the matched local trace: same 308 -> 207 epoll_ctl and 102 -> 102 writev. Those matched traces supersede initial local BASE evidence. Source hashes and generated diff retained in `r85-independent/`. All canonical results use the corrected baseline.

### Final canonical decision

N=7 had −1.11% median RPS and 3/7 paired wins; extended to N=10 per user instruction. Final BASE median 21,583.23, CAND 21,484.305 RPS: **−0.46%, 5/10 paired wins; REVERT**. Full individual runs/min/max/paired deltas and cleanup/provenance notes in the result report. Main remains 0e95d0d, isolated patch reversed, evidence banked. No additional R8.5 candidate.

Separate post-A/B remote mechanism diagnostic reached 300,000 ordinary completions: 300,000 attempts with no writable fallback, zero EPOLLOUT fallback arms (cumulative checkpoint, not exact final wrk denominator). This reinforces mechanism success despite neutral throughput.
