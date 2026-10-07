# Rust-gap design note — how Hyper/Axum avoid Strut's remaining request work

Sources inspected: hyper/src/proto/h1/role.rs, httparse, bytes, http::HeaderMap,
matchit (current masters). These are architectural evidence, NOT Strut promises.

## What Rust does differently

1. **Borrowed header views first.** httparse parses `Header<'a>` = borrowed `&str`
   name + `&[u8]` value inside the receive buffer; parsing does not allocate a
   string per header. Recorded as (name_start, name_end, value_start, value_end)
   index pairs into the buffer.
2. **Stack-backed uninitialized scratch.** `role.rs`:
   `SmallVec<[MaybeUninit<HeaderIndices>; DEFAULT_MAX_HEADERS=100]>` +
   `SmallVec<[MaybeUninit<httparse::Header>;100]>`, deliberately never zeroed.
   Source comment: "By not zeroing out the stack memory, this saves a good ~5% on
   pipeline benchmarks." `Builder::max_headers` doc warns: forcing headers onto the
   heap "will occur for each request, and there will be a performance drop of about
   5%."
3. **Shared immutable byte ownership.** After a complete head: `BytesMut::split_to
   (len)` (O(1) offset adjust) then `.freeze()` -> shared ref-counted `Bytes`; URIs,
   methods, and header values come from slices of that stable backing; copies across
   threads are refcount bumps, not byte copies.
4. **Move-only request ownership.** Axum consumes/moves the request
   (`into_parts()`); ownership design means no deep-copy of request state exists to
   begin with.
5. **Specialized header container.** `http::HeaderMap` = entries vector (name +
   first value) + Robin-Hood `indices` table of hash->entry index; rehash moves only
   index slots, not the header data; header names are a compact enum/static set;
   collision-adaptive hashing. Not a generic node-oriented
   `unordered_map<string,string>`.
6. **Compiled routing.** matchit: zero-copy radix trie with child-priority ordering;
   parameter routes share prefixes; matching is trie-traversal, params come out as
   slices/spans, not a fresh owned map per attempted route.

## Which ideas transfer cleanly to Strut (public API stable)
- Keeping the parser's copied head bytes as a stable OWNED backing and representing
  method/path/header values as offsets/spans into it (no dangling views into
  mutating `conn->input`). Materialize public `strut_string`s lazily.
- An internal compact header index (name/value spans + lowercase-on-demand) instead
  of build-a-string-per-header + an unordered_map per request; materialize the
  public `http_request.headers` map at the last responsible moment.
- Move-only request ownership on the buffered path (already partially landed via
  R8.5-M; remaining deep-copy sites are the work of R8.5-N).
- A route table that does not linearly scan all routes (matters at high route
  counts; the 2-route microbenchmark understates the win).

## Which do NOT
- string_view into `conn->input`: input is erased on keep-alive reuse -> UB. Any
  backed-by-buffer design needs its own owned/immutable backing with bounded
  lifetime through callback (shared_ptr / refcount / move-owned head buffer).
- Changing the public `http_request.headers` type or headers access semantics.
- Copying unsafe `MaybeUninit` tricks verbatim; Strut's generated code is C++ and
  the ~5% scratch-init cost is not the same magnitude as Strut's per-request
  allocation/copy chain.

## Evidence alignment from our own campaign
- Removed ostringstream response-serializer layer   -> +8.4% (R8.5-E)
- Removed pump request copy/copy-back layer          -> +4.6% (R8.5-M)
- Reduced reactor steady_clock reads 92%             -> ~0%
- Removed a parser temp/copy cleanup                 -> ~0%
- Read-once, pending-wake, worker-move(before M)     -> ~0%
=> Pattern: removing WHOLE ownership/construction/materialization layers moves
throughput; shaving one operation inside an existing layer does not.

## Prototype (R8.5-N)
RE-TEST the remaining buffered request deep-copy (worker -> by-value callback) as a
move NOW that the pump copy is gone. R8.5-K (worker move) was flat pre-M because the
pump copy still existed; post-M the request path can become a pure move chain. This
is ONE bounded change, public-API-safe, A/B-able, and measures whether the remaining
request-copy category is load-bearing.

Benchmarks: c=1/10/50, mechanism via malloc uprobe count + request-copy stack family;
retention wall (CTest 16/16 x4 + 289/289 default + reactor + focused keep-alive).
Route-scaling benchmark (1/10/100/1000 routes) is a separate future item.