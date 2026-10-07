# R8.5-M — pump-side request deep-copy elimination: KEPT (c=50 +4.6%, c=10 +8%)

Candidate (from R8.5-K malloc attribution, ~10.7% pump prep copy family): the pump's
`if(!conn->early_routed)` block deep-copied `conn->head.request` into a temporary,
routed (mutating the temp's params), then copy-backed — plus a redundant reassign in
the websocket branch. Rerouted directly against the connection-owned request instead:

    auto& req = conn->head.request;   // was: strut_server_request req = conn->head.request
    ...
    conn->early_routed = true;        // was: conn->early_routed = true; conn->head.request = req;
    (websocket)                       // dropped: conn->head.request = req;

Ownership/lifetime check (semantics preserved by construction): route loop calls
`req.params.clear()` at the START of every candidate, so params never leak between
candidates; keep-alive re-parse replaces the whole head (`conn->head = parsed.head`),
so params can't leak across requests; no code retains a reference into the temp; all
post-route consumers (stream/websocket workers) read `conn->head.request`, which now
holds exactly what the old copy-back wrote; 404/405/close paths return without reading
request params. Pure-sync routing, no yields. Buffered + stream + websocket all on the
same block.

## Full retention wall (green)
- CTest 16/16 normal, 16/16 GCC -Werror, 16/16 Clang -Werror, 16/16 ASan/UBSan.
- Local functional battery on CAND: 3 keep-alive /plaintext on ONE connection, /json on
  the same connection, 404, duplicate-Host 400, POST->405 — all correct.

## Isolated warmed identity-gated A/B (STRUT_HTTP_REACTOR=1)
c=50 (wrk -t2 -c50 -d15s, warm 10s, alternating):
| metric        | BASE (80556b4) | CAND (pump-direct) |
|---------------|----------------|--------------------|
| n             | 10             | 11                 |
| median rps    | 14913.8        | 15603.5            |
| range         | 14338-15763    | 14202-16336        |
| delta         | --             | +4.6% median       |
| paired rounds | 10             | CAND wins 7 (70%)  |

c=10 (wrk -t1 -c10, 4 clean pairs): cand wins 4/4 (+4%, +8%, +10%, +13%), median ~+8%.
c=1: RTT-dominated, ~flat (2 usable pairs, 1/1-ish), inconclusive.

## Mechanism note
Intended change verified in source (pump copy-out + copy-back + websocket reassign
removed). The -g malloc perf trace on CAND failed to symbolize in-session (perf mapping
quirk), so the per-stack reduction was not re-measured directly; the throughput signal
(+4.6%/+8%) plus the code-level elimination is the accepted evidence.

## Decision: KEEP
Committed to strut main as 73d379a. Retained alongside beed5ba + 87e00ff/80556b4.
Compiler head now 73d379a. Following step: same-session Strut vs frozen-Go.