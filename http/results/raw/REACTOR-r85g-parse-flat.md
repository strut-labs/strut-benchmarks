# R8.5-G — request-head parse copy reduction: A/B NEUTRAL -> REVERTED

Candidate from R8.5-F ranking: parse was the largest pure user-space request-fixed
phase (~11.4us). Implemented in a temporary worktree at 80556b4 (never committed):

- `strut_parse_http_request_head(bytes, head_len, ...)`: head-passed by length so the
  reactor call site no longer builds `conn->input.substr(0,header_end+2)` per request.
- Removed the intermediate `line`/`target` full-string temporaries (direct slices);
  bounded all `\r\n`/space searches to head_len.
- `fields.reserve(8)`.
- All validation, fail codes, and final request state preserved (functionally identical).

## Correctness (candidate, local)
- CTest 16/16 (incl. `strut_codegen_tests` 50s, server-slice bound) on the candidate build.
- HTTP parity battery vs BASE on 15 variants: valid, /json, malformed request line,
  duplicate Host, HTTP/1.0, Content-Length+Transfer-Encoding, TE-not-chunked, Expect,
  HTTP/9.9 (505), HTTP/x (400), oversized CL (413), folded header (400), bad CL digits
  (400), control-char in value (400) — all status lines identical to BASE.
- /plaintext = "Hello, World!", /json = JSON body (200).

## Isolated warmed A/B (Linode, STRUT_HTTP_REACTOR=1, wrk -t2 -c50 -d15s, identity-gated)
Note: the first BASE binary was built with a stale `build-clang` compiler (1200 rps —
rejected). BASE was rebuilt from main 80556b4 (`/tmp/main-build`) and redeployed.

| round | BASE rps | CAND rps |
|-------|----------|----------|
| 1     | 14832.00 | 15687.20 |
| 2     | 15771.53 | 14269.56 |
| 3     | 15364.48 | 15401.65 |
| 4     | 16135.05 | 16026.12 |
| median| 15567.7  | 15543.9  |

Median CAND/BASE ≈ -0.14%; ranges overlap completely. **No measurable effect** — parse
wall was mostly 1-vCPU preemption/scheduling, not removable copy cost.

## Decision: REVERT (neutral)
R8.5-G is not committed; main repo stays pristine at 80556b4. Worktree (/tmp/r85g-wt)
removed. Per campaign rule the change is abandoned.

## Implication
No single clean user-space phase is large enough to move throughput alone. The
remaining lever is the kernel/synchronization budget outside the scoped profile:
eventfd ~0.96, futex ~1.51, recv ~1.92, writev ~0.96 per request (plus timer/deadline).
That is the documented next investigation area (batch/wake/syscall fusion), informed by
the earlier R8.5-A/B experiments.