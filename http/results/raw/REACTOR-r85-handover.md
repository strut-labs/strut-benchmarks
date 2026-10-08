# R8.5 final handover

**R8.5 CLOSED — closure fully accepted.** The campaign exhausted the currently evidenced bounded structural candidates. Further HTTP work would need a new architectural hypothesis or substantially more invasive redesign without sufficient current evidence. This does not mean HTTP performance is solved, that Strut cannot reach Rust, or that no further optimization exists. Stop R8.5 here.

## Final state

- Retained compiler: **`0e95d0d5062f55a7a3c051e7311e26acc2e90a44`** (Strut 0.0.3).
- Existing retained-main certification: **294/294 default + 294/294 reactor**; authoritative, not rerun for this administrative handover.
- Final independent experiment/evidence: **`2cb02d3`** in `strut-benchmarks`.
- Earlier final campaign report/evidence: **`1b28c09`**; preserved. The independent review is an addendum/final challenge, not a replacement for the DeepSeek campaign.
- No immediate-write production change retained. Candidate patch reversed; reverted isolated compiler emits byte-identical corrected BASE source.
- Legacy remains default; reactor uses `STRUT_HTTP_REACTOR=1`.

## Major retained architecture

| Retained work | Commits / evidence |
| --- | --- |
| Route matcher cleanup | `beed5ba` |
| Direct response-head serializer, bounded reserve | `87e00ff`, `80556b4`; +8.4% canonical in its measured pairs |
| Request ownership/move cleanup, removal of pump and buffered deep copies | `73d379a`, `da4a8f2` |
| Direct/range-guided request-head construction, redundant header representation removed | `51771f9` |
| Indexed exact router + parameter trie, registration-order semantics preserved | `56ea341`; removes large-route linear collapse |
| Specialized flat request headers, generic map semantics certified | `5c647bf`, `a08fea5` |
| Internal request cancellation placeholder avoids one eager allocation; public default-token semantics preserved | `0e95d0d` fix-forward |

Earlier vectored response write/writev remains retained. The listed commits remain in retained compiler ancestry; no history rewritten.

## Negative evidence and parked directions

| Direction | Outcome / evidence |
| --- | --- |
| Read-once | Neutral, reverted (R8.5-B; final report) |
| Wake batching/suppression | Incorrect empty-to-nonempty suppression rejected; corrected batching neutral, reverted (A/I) |
| Cached reactor clock | Mechanism reduced clock calls, canonical neutral, reverted (L) |
| Compiled-but-linear router | Still O(N), weak gain, reverted (P); actual indexed router retained (Q) |
| Stable-backed/lazy header values on canonical path | Parked: short/SSO values give poor expected payoff; more invasive lowering needed (S0/V) |
| Deeper cancellation ownership | Parked: escaped-token/stack-source lifetime constraints; no safe simple allocation removal (T/U) |
| W: buffered callback executes on reactor | +6.7%, 7/7; diagnostic only, loses blocking-handler isolation |
| X: worker directly arms EPOLLOUT | −10.5%, 1/7 wins; reverted |
| Immediate-write: worker callbacks and completion batching retained; reactor flushes during completion drain | −0.46% median ratio, −0.55% median paired delta, 5/10 wins; neutral/noisy, reverted |

W is evidence about its particular inline variant, not a mathematical upper bound on every scheduler topology. X did not test optimistic writes. The defensible synthesis is that none of the bounded production-compatible scheduler/write-transition candidates identified in this campaign delivered a compelling canonical win.

Immediate-write mechanism succeeded: matched local trace **epoll_ctl 308 -> 207**, **writev 102 -> 102**; separate diagnostic checkpoint **300,000 completions, 300,000 no-fallback attempts, zero EPOLLOUT fallback arms**. Removing the avoidable writable-readiness transition did not materially improve canonical throughput on this workload. Do not rescue the result through mechanism elegance, another concurrency/duration, or another scheduler tweak.

Canonical measurement used ten alternating pairs, fresh processes, warm 10 s / measured 15 s, wrk t=2/c=50, exact identity gates and zero reported socket/non-2xx errors. BASE median **21,583.23**, CAND **21,484.305** RPS. All valid runs retained, including large negative/positive pair swings. N=7 was already negative/noisy (−1.11%, 3/7 wins). A stale initial local BASE was detected and rebuilt from exact retained source before any timed remote run; source-only candidate diff, hashes and raw ordering remain visible in the evidence.

The losing candidate did not require a full retention wall or a fresh Go control. Existing retained-main certification stands.

## Parked semantic and workload notes

- **Cancellation completion divergence:** an escaped request token becomes cancelled after ordinary completion in legacy mode; normal buffered reactor completion leaves it uncancelled. This unresolved API/correctness decision was not changed. See `REACTOR-r85u-cancellation-lifetime.md` and cancellation-escape fixtures.
- **Stable-backed/lazy header values:** remain possible if future header-heavy/long-value workload evidence warrants the representation and semantics work. Parked, not disproved universally.
- **Rust gap:** unresolved; the campaign did not establish a single architectural explanation or reach the historical Rust floor.

## Historical benchmark standing

Healthy canonical Strut is roughly **high-teens / low-20k RPS depending session**. Frozen Go is roughly **19–21k in historical healthy controls**. Rust is **>=35k historical, generator-limited floor**.

No fresh cross-language ratio is inferred. The final session's ~21.6k BASE uses the same retained compiler as earlier ~17–18k sessions; it is not evidence of a code improvement. The final candidate decision rests on same-session BASE/CAND. Go/Rust controls were not remeasured in that session.

## Evidence to carry forward

- [Final campaign report](REACTOR-r85-final-report.md).
- [Independent Crow/Drogon/oatpp architecture review](REACTOR-r85-independent-architecture-review.md).
- [Final immediate-write result and closure](REACTOR-r85-immediate-write-result.md).
- [Raw pairs, identities, hashes, counters, patch and cleanup](r85-independent/).

Drogon/Trantor provides a concrete example of the architectural difference; current Crow's synchronous Asio writes are likewise a source observation. Neither establishes that the observed write policy causes that framework's performance. The Strut analogue was separately implemented, mechanism-checked and measured.

## Infrastructure, preservation and stop boundary

Both retained Linodes remain **preserved and idle**: server `96.126.107.155`, generator `96.126.107.181`. Final experiment cleanup verified no :8080 listeners, no r85iw services/processes, and no wrk process. No new remote work was performed for this handover.

Preserve `stash@{0}`, `dogfood/__pycache__/`, `tools/__pycache__/`, and `/tmp/strut-site-main`. No reset/clean/rebase/history rewrite, direct .git changes, `pkill -f`, or Linode deletion.

**No further R8.5 candidate or HTTP/reactor performance investigation.** Do not start R9, R10, FFI, comptime or freestanding work without explicit direction to the next roadmap item.
