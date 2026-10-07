# R8.5-E serializer — corrected (reserve fix + isolated A/B)

Supersedes the earlier provisional A/B in REACTOR-r85e-serializer.md (that one
compared 417e197 vs beed5ba+BUGGY serializer and is discarded as non-isolating).

## Reserve bug fixed (80556b4)
Old serializer reserved 160 + body_size/10 bytes for the response head -> a 1 GiB
Content-Length response would attempt ~107 MiB to build its header. Now reserves
192 + header/cookie name-value sizes + decimal-digit count of Content-Length:
O(header bytes), never O(body). Verified: HEAD /huge declares
Content-Length: 1073741824 and the server sits at ~5.3 MB RSS.

## Isolated A/B (exact beed5ba base vs beed5ba + fixed serializer)
Same node session, warmed (unrecorded run before each measured run), alternating
B/C, /plaintext:
- c=50 N=7 (B..C..): BASE med 20.76k [19.53k-22.36k]; CAND med 22.49k
  [21.09k-24.31k]; CAND > its adjacent BASE in ALL 7 pairs (+8.4% median).
- c=10 N=5: BASE med 13.34k; CAND med 13.07k (-2%, within noise; one outlier
  each side).
- c=1  N=5: BASE med 5.38k; CAND med 5.41k (neutral).

CLASSIFICATION: RETAINED. Full wall green (CTest 16/16 x4, 289/289 both modes),
semantics identical (289 regressions + focused 200/204/302/Content-Length/HEAD),
structurally cheaper (no ostringstream + out.str() copy per response), reserve
now body-size-independent. c=50 shows a consistent positive direction (paired);
c=1/c=10 neutral within node noise. Keep the caveat that node variance is large;
a controlled re-baseline is deferred until strut/Go/Rust are reset under stable
conditions.
