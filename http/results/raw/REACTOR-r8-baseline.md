# Post-R8 1-vCPU baseline (authoritative reference for R8.5)

Node: strutbench-a (1 vCPU), load strutbench-b. Compiler: R8 (a131e42).
STRUT_HTTP_REACTOR=1; buffered-only benchmark server (strut/server.p).

## plaintext
| config | runs (req/s) | median | min | max |
|---|---|---|---|---|
| c=50 (N=6) | 13809, 15554, 15300, 15366, 14408, 14863 | 15082 | 13808 | 15554 |
| c=10 | 9038 | - | - | - |
| c=1  | 3887 | - | - | - |

## json
- c=50: 14639

## Assessment
Median c=50 ~15.1k is within the campaign's observed same-node session variance
(~14.4k-16.9k across R7-era runs); the guarded TLS path adds only a null-branch
per plaintext read/write. Classification: no material post-R8 plaintext
regression. R8.5 will A/B every retained optimization against this baseline.

## TLS thread/resource model (1-vCPU)
- TLS reactor server idle: 6 threads (reactor + 1 app + 4 stream), matching the
  plaintext reactor model; no per-connection TLS threads. (Remote idle-connection
  open was blocked by the fixture binding loopback; architecture bounds idle TLS
  conns to the reactor + fixed pools by construction.)
