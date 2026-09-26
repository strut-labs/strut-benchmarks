# Strut benchmark handover

This repository exists to measure Strut against C++, Rust and Go without changing the workload to suit a result.

## Rules

1. Equivalent programs must perform the same meaningful work and produce identical stdout.
2. Correctness is checked before timing is accepted.
3. Keep raw result JSON files when using a run as a published or optimisation baseline.
4. Record toolchain versions and host information with every run.
5. Do not tune one language with exotic flags while leaving the others on ordinary release settings.
6. Prefer core/standard-library workloads for the primary matrix. If a benchmark needs third-party packages, document and pin them for every affected language.
7. Never remove a benchmark merely because Strut performs poorly on it. Poor results identify profiling work.
8. When optimising Strut, rerun unchanged benchmark sources before and after the change.
9. Treat source bytes, nonblank LOC and approximate tokens as complementary verbosity measures, not one universal complexity score.
10. Separate implementation facts from interpretation. `results/*.json` is evidence; conclusions belong in analysis/reporting.

## Current initial matrix

- `hello`
- `arithmetic`
- `fibonacci`
- `vector_sum`
- `threads`
- `hot_loop`
- `lambda_map`
- `pointer_rc`

The runner is `run.py`; `run.sh` is a convenience wrapper. `benchmarks.json` is the workload/expected-output manifest.

## Future candidates

Useful future additions after the base matrix is stable include:

- maps/hash tables;
- string processing;
- JSON parse/stringify with equivalent libraries clearly disclosed;
- SQLite with equivalent bindings;
- HTTP client/server throughput;
- channels/message passing;
- async scheduling;
- allocation/reference-count stress (initial `pointer_rc` workload is now present; extend it further);
- larger multi-file compile and incremental-rebuild workloads.

Keep startup-scale microbenchmarks separate from sustained throughput workloads so process launch noise does not obscure hot-loop performance.

## Profiling kit

`PROFILING.md` and `profile.sh` cover compiler-stage timing, generated-C++ capture, incremental builds, Linux `perf`, assembly comparison, larger hot workloads, and feature-heavy JSON/async/SQLite/HTTP probes. Keep profile artifacts under `profiles/results/`; only `.gitkeep` is tracked there.
