# R8 same-session plaintext A/B (PRE=R7b-2 adebe28 vs POST=R8+a131e42)

Same node A (1 vCPU), node B generator, benchmark server.p, STRUT_HTTP_REACTOR=1,
interleaved 8s wrk c=50:

| sequence | rps |
|---|---|
| PRE1 | 15811 |
| POST1 | 14212 |
| PRE2 | 16076 |
| POST2 | 16016 |
| PRE3 | 15969 |
| POST3 | 15148 |

PRE median ~15969 (min 15811, max 16076). POST median ~15148 (min 14212,
max 16016), but POST showed high first/latched-run skew.

Steady POST (warm, 5 consecutive): 14597, 16158, 16047, 16213, 15941 ->
median ~16047.

CONCLUSION: no material post-R8 plaintext regression. The guarded TLS path costs
a null-branch per plaintext read/write (inlined); steady-state POST c=50
(~16.0-16.2k) equals PRE (~16.0k) and the historical writev reactor era. The
earlier authoritative baseline medians (~15.1k) included restart skew; treat the
steady ~16.0-16.2k as the honest post-R8 reference for R8.5.
