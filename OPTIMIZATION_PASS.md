# Compile/runtime optimisation pass

This note records the development-container smoke results that motivated the current profiling handoff. They are not publication-quality benchmark claims; rerun the suite on the target development machine and use `results/latest.json` as the canonical evidence.

## Changes

- simple generated translation units no longer include JSONIC or the full filesystem/process/network/HTTP/SQLite runtime unless those facilities are used;
- the minimal runtime is feature-sensitive for scalar, collection/lambda and safe-pointer support;
- direct one-file release builds omit LTO because there is no cross-translation-unit optimisation opportunity;
- `.strut` project/object builds retain the multi-object optimisation path;
- dynamic arrays expose `reserve`, and `lambda_map` now matches the C++ reference's explicit one-million-element reserve;
- recursive safe pointer types and references-to-pointer bindings are supported.

## Development-container smoke comparison

On the container used for this pass, representative cold release compile medians moved from roughly 1.8–2.2 seconds before runtime pruning to approximately:

| workload | Strut | C++ reference |
| --- | ---: | ---: |
| hot_loop | 283 ms | 286 ms |
| lambda_map | 433 ms | 343 ms |
| pointer_rc | 381 ms | 363 ms |

Representative runtime medians in the same short smoke run were 185.6/186.1 ms (`hot_loop` Strut/C++), 4.17/4.34 ms (`lambda_map`), and 30.7/31.5 ms (`pointer_rc`). Run-to-run noise at these sizes is significant; local profiling on the real development machine is the next source of truth.

`profile_compile.py` also showed the generated C++ shrink substantially: `hot_loop` was 16 lines / 773 bytes, while `lambda_map` was about 36 lines / 1.9 KiB. The Strut frontend itself remained sub-millisecond; host C++ compilation/linking is still the dominant cold-build cost.

## Follow-up pass after NUC profiling

The returned NUC profile confirmed that parse, semantic analysis and IR lowering are sub-millisecond and that native C++ compilation dominates cold build time. An apparent ~0.24 s vs ~1.9 s discrepancy was not a compiler-path discrepancy: the numbers being compared came from different machines. Profiling output now embeds host/toolchain identity to prevent that mistake.

The minimal runtime include set is now feature-granular rather than treating every collection use as requiring vector, array, optional, type traits, utility, algorithm and exceptions. Dynamic-vector-only programs emit only the vector header; higher-order helpers add only the headers they need; pointer programs no longer emit nullable support unless nullability is actually used. In development-container medians this reduced `lambda_map` cold Strut compile time from roughly 436 ms to 372 ms and `vector_sum` from roughly 417 ms to 351 ms, with essentially unchanged runtime. Treat those figures as smoke data only; rerun on the NUC for canonical before/after results.

The profiling kit was also corrected so `host_direct_compile_ms` mirrors the normal one-file release backend. Project-style LTO object and link measurements are retained but explicitly labelled separately. Hotspot profiling now records failed `perf` permissions/recording instead of trying to report zero-byte data, and emits GCC vectorisation diagnostics when available.

Assembly/vectorisation inspection of `vector_sum` found no Strut-specific bounds-check or abstraction loop in the hot path. GCC's `-O2` vectorisation diagnostics for the generated program and handwritten C++ reference show the same broad blockers, so no runtime semantic change was made merely to chase that microbenchmark. Safe-pointer RC code was likewise left semantically intact pending evidence from a larger workload.

## Next profiling pass additions

- `pointer_rc_long`: 50M safe shared-pointer copies/dereferences to suppress process-startup noise.
- same-machine benchmark defaults: 5 compile, 10 runtime, 3 RSS, 3 warmup samples.
- Rust is included in the default comparison set when available.
- `profile_project_scale.py`: 10/100/500-file include graphs, measuring cold/no-op/touched-leaf builds.
- feature profiling records generated C++ size/line count for heavy-runtime compile-cost diagnosis.
- safe pointer null-failure branches are marked `[[unlikely]]`; safety behavior is unchanged.
