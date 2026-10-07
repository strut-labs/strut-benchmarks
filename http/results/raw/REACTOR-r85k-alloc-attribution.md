# R8.5-K — malloc call-site attribution (perf uprobe, /plaintext c=50)

Method: `perf probe -x /usr/lib/x86_64-linux-gnu/libc.so.6 malloc`, then
`perf record -e probe_libc:malloc -g -p <server-pid> -- sleep 5` under c=50 wrk.
352,166 malloc samples, 5 s. Canonical server /root/bench/strut_base (80556b4),
identity-gated. This is attribution, not a throughput baseline.

## Share of malloc samples by caller (collapsed call tree)

Reactor/main path (~68.0%):
| caller                                 | share  |
|----------------------------------------|--------|
| parse_http_request_head (total)        | 39.05% |
|   substr copies                        | 10.65% |
|   headers unordered_map[] build        | 7.10%  |
|   basic_string copy (field strings)    | 7.10%  |
|   vector<hdr_field>::push_back         | 3.55%  |
|   head_result ctor -> make_shared<cancellation_state> | 3.55% |
|   strut_http_target                    | 3.55%  |
|   strut_trim_ascii                     | 3.55%  |
| request copy ctor (pump prep `req=conn->head.request`) | 10.65% |
| cancellation make_shared<cancellation_source> (conn)   | 7.10%  |
| head/request assignment (headers deep copy)            | ~7.2%  |

App-worker path (~32.0%):
| caller                               | share |
|--------------------------------------|-------|
| request copy ctor `req=conn->head.request` (worker) | 21.30% |
| fn(req) by-value param construction  | 3.55%  |
| serializer `reserve` (head string)   | 3.55%  |
| strut_http_text / response construct | ~3.6%  |

## Category roll-up (shares of malloc uPROBE SAMPLES in the diagnostic window)
These are sample-share percentages, not exact allocations/request. Roughly half of
observed malloc samples were associated with header/request representation and
copying:
- Header unordered_map representation + its ~3-4 deep copies per request
  (parse build 7.1 + pump copy 10.7 + worker copy 21.3 + assigns 7.2 + fn-param copy
  ~3.6)  ~= half of observed samples
- Parser string/copy churn (substr/trim/target/vector/field strings) ~28%
- Cancellation shared_ptr (state via head ctor + source via conn) ~10.7%
- Response construction + serializer head reserve ~10.7%
- Route/params, completion/deque, allocator internals: not material.

## Chosen single candidate (largest clean general-purpose source)
The buffered app-worker handoff deep-copies `conn->head.request` once (21.3%) and the
`conn->fn(req)` call deep-copies it again into the by-value callback parameter. After
dispatch, the buffered path reads only conn->head.version/persistent/framing (separate
fields), never conn->head.request, so BOTH copies can be elided by moving:
`strut_server_request req=std::move(conn->head.request);` then
`conn->fn(std::move(req));`. Behavior is identical for the app (callback owns the request
by value). Stream/websocket paths are untouched (not exercised by the buffered benchmark).
Implementation in a temporary worktree; CTest + functional parity; then warmed
identity-gated A/B N>=5 with malloc-count re-measurement.