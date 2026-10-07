# R8.5-O — span-based request-head construction (drop fields vector + header string temporaries): KEPT

The Rust-inspired request/header architecture experiment (see design note
REACTOR-rust-gap-design-note.md). Lazy public materialization of `http_request.headers`
is NOT possible without changing the public member type (`std::unordered_map<strut_string,
strut_string>` is a plain member the generated code accesses directly) -> documented
blocker. Instead removed a whole redundant layer inside the existing representation:

- DROP `std::vector<strut_http_header_field> fields` from internal strut_http_request_head
  (was only used for the duplicate check + storage; nothing reads it after parse).
- Duplicate detection now uses the public headers map itself (`find`).
- Per-header parse builds name/lower/value directly from spans of the parser's stable
  head copy: in-place lowercase (no separate `lower` string), trimmed value constructed
  once (no substr temp + no strut_trim_ascii double copy), no `header` line temp.
- Map reserved before the loop (no bucket rehash), classification runs BEFORE the
  values are moved into the map (the earlier move-before-classify bug fixed -> 400).

Public API and public `http_request.headers` semantics unchanged (case-insensitive map,
duplicate rejection 400, Host/CL/TE/Connection/Upgrade/Cookie rules identical).

## Correctness — full wall (green)
- CTest 16/16 normal, 16/16 GCC -Werror, 16/16 Clang -Werror, 16/16 ASan/UBSan.
- Regressions 289/289 default, 289/289 STRUT_HTTP_REACTOR=1.
- Functional battery: 3x keep-alive reuse, /json, dup-Host 400, bad CL 400, TE+CL 400,
  Expect 417.

## Mechanism (perf uprobe malloc, 5 s, /plaintext c=50)
- BASE da4a8f2: 5.37 malloc-samples/request.
- O cand: 4.74 malloc-samples/request (-11.7% with ONE header; gap grows with header count).

## Isolated warmed identity-gated A/B (BASE = da4a8f2 = s_final, CAND = O)
| workload            | base median | O median | delta   | pairs |
|---------------------|-------------|----------|---------|-------|
| /plaintext (1 hdr)  | 16219.6     | 16482.6  | +1.6%   | 4/7   |
| /plaintext (8 hdrs) | 10648.3     | 13049.7  | +22.6%  | 5/5   |

The 8-header test is the decisive architectural signal: header-count scaling is exactly
where the representation change pays (consistent with Hyper's header-scaling design).
1-header c=50 barely moves (map-node cost dominates there; little wins because tiny
requests).

## Decision: KEEP
Committed as 51771f9. Retained alongside beed5ba, 87e00ff/80556b4, 73d379a, da4a8f2.

Next: same-session Strut (51771f9) vs frozen Go at the canonical /plaintext,
N>=7 if practical.