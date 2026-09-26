# Strut profiling kit

This repository includes the profiling side of the optimisation campaign so profiling can happen on the real development machine without modifying benchmark sources between runs.


## One-command profiling run

From `strut-benchmarks/`, run:

```bash
./profile.sh
```

`profile.sh` now configures and builds the adjacent `../strut` tree in Release mode, runs the Strut CTest suite, then runs compiler, incremental and feature profiles. It also runs the same-machine quick benchmark for `hot_loop`, `lambda_map` and `pointer_rc`, refreshing `results/latest.json`, `results/latest.csv` and `results/latest.md`.

CMake caches absolute source paths. If the workspace has been moved/copied/extracted and `../strut/build/CMakeCache.txt` points at a different source tree, `profile.sh` automatically removes that stale build directory before configuring. This is important because the Strut binary currently receives the JSONIC include directory from CMake at build time; reusing a binary built in another workspace can make feature-heavy generated C++ fail to find `json.h`. You therefore do not need to manually delete `build/` before normal runs.

Useful overrides:

```bash
PROFILE_RUNS=5 ./profile.sh                    # fewer compiler-profile samples
STRUT_BUILD_JOBS=8 ./profile.sh                # cap parallel build jobs
PROFILE_SKIP_BENCHMARKS=1 ./profile.sh         # profiles only; do not refresh latest.*
PROFILE_BENCH_LANGUAGES=strut,cpp,go ./profile.sh
PROFILE_BENCH_TASKS=hot_loop,lambda_map,pointer_rc ./profile.sh
```

## 1. Compiler pipeline

Build the current Strut compiler, then run:

```bash
./profile.sh
```

or directly:

```bash
python3 tools/profile_compile.py \
  --strut ../strut/build/strut \
  --source benchmarks/strut/vector_sum.p \
  --runs 20
```

`profile_compile.py` records the host identity/toolchain alongside timings so results from different machines are not accidentally compared as one pipeline. It records:

- complete user-visible Strut compile time;
- Strut load/parse time;
- semantic-analysis time;
- IR-lowering time;
- generated-C++ emission time;
- generated C++ source size/line count;
- matching direct one-file host-C++ compile time (`host_direct_compile_ms`);
- project-style host-C++ object compilation time with LTO;
- project-style LTO link time.

The direct host number is the apples-to-apples comparison for normal `strut file.p --release -o app`; the object/link numbers diagnose the incremental multi-object project path and should not be added together to explain a direct compile.

The compiler now accepts `--timings` and `--emit-cpp <path>` specifically so this split is measured rather than guessed.

The wrapper now profiles `hot_loop`, `lambda_map`, and `pointer_rc` separately. Send back `profiles/results/compile-hot-loop.json`, `compile-lambda-map.json`, and `compile-pointer-rc.json`.

## 2. Incremental builds

```bash
python3 tools/profile_incremental.py --strut ../strut/build/strut --release
```

This creates an isolated project and measures cold build, no-op build, changed source and changed header/dependency behaviour while recording the compiler's verbose reuse/rebuild explanation. Send back `profiles/results/incremental-profile.json`.

## 3. Runtime hotspots

Linux with `perf`:

```bash
python3 tools/profile_hotspot.py vector_sum --strut ../strut/build/strut
python3 tools/profile_hotspot.py pointer_rc --strut ../strut/build/strut
python3 tools/profile_hotspot.py lambda_map --strut ../strut/build/strut
```

Each command emits a profile-friendly `-O2 -g -fno-omit-frame-pointer` binary from Strut's generated C++, an equivalent C++ binary, `perf stat`, `perf record/report`, disassembly, and (when GCC is detected) `*-vectorization.txt` diagnostics under `profiles/results/<task>/`.

If Linux perf permissions reject recording, the profiler now records the failure and stderr in `profile-meta.json` / `*-perf-report.txt` instead of leaving a misleading zero-byte perf data file. The binaries, disassembly, and GCC vectorisation diagnostics remain useful. Typical local testing command is `perf stat ./binary`; do not change system perf security settings just for this suite unless you are comfortable doing so.

## 4. Assembly comparison

```bash
python3 tools/compare_asm.py vector_sum --strut ../strut/build/strut
```

This writes full Intel-syntax assembly for Strut-generated C++ and the hand-written C++ reference. The first targets worth inspecting are `vector_sum`, `pointer_rc`, `lambda_map`, and `hot_loop`.

## 5. Comparative benchmark matrix

The normal benchmark suite now contains short startup-oriented programs plus longer/hotter workloads. For a serious run:

```bash
./run.sh \
  --strut ../strut/build/strut \
  --compile-runs 10 \
  --runtime-runs 30 \
  --memory-runs 5 \
  --warmup-runs 5 \
  --require-all
```

Send back `results/latest.json` rather than only the Markdown table so individual samples and toolchain metadata remain available.

## Optimisation order

The current investigation intentionally follows this order:

1. split Strut frontend cost from generated-C++ compile/link cost;
2. measure cold/no-op/source/header incremental builds;
3. inspect generated C++ for every outlier;
4. profile `vector_sum` first;
5. compare generated assembly with C++;
6. identify refcount/copy/bounds-check costs;
7. check auto-vectorisation and inlining blockers;
8. inspect thread/concurrency overhead and verbosity separately;
9. use `hot_loop`/larger workloads so process startup is negligible;
10. extend into maps, strings, JSON, async, SQLite and HTTP once the basic hot paths are understood.

Do not optimise from a single wall-clock number. Keep the before/after raw JSON and profile artifacts for every change we decide to keep.

## 6. Feature-heavy Strut paths

The cross-language matrix should stay conservative about external dependencies. Strut-specific profiling for features that need JSONIC, SQLite, the async runtime, or the HTTP server is therefore kept separate:

```bash
python3 tools/profile_features.py --strut ../strut/build/strut
```

It records release compile time, runtime, RSS and binary size for JSON parsing/stringification, async scheduling and SQLite, plus sequential local HTTP throughput/latency. Send back `profiles/results/feature-profile.json` with the other raw profile files.

These measurements are for finding Strut hot paths, not for claiming cross-language wins. Equivalent cross-language JSON/SQLite/HTTP workloads should only be added once dependencies and configurations are pinned fairly for every language.

## What to send back

The most useful bundle for the first optimisation pass is:

- `profiles/results/compile-hot-loop.json`
- `profiles/results/compile-lambda-map.json`
- `profiles/results/compile-pointer-rc.json`
- `profiles/results/incremental-profile.json`
- `profiles/results/feature-profile.json`
- `results/latest.json`
- the relevant `profiles/results/<task>/perf-stat*.txt`, `perf-report*.txt`, generated C++, assembly and disassembly for any runtime outlier

That gives us enough evidence to separate frontend/compiler work from generated-C++ work and runtime/codegen work before changing implementation strategy.

## Current compile-time optimisation pass

The bootstrap backend now has a feature-minimal code-generation path for ordinary scalar, array/lambda and safe-pointer programs. Simple programs no longer unconditionally include JSONIC or emit the full filesystem/process/network/HTTP/SQLite runtime into the generated C++ translation unit. Direct one-file release builds also omit LTO because there is only one translation unit; project/object builds keep LTO for cross-object optimisation.

This means the next local profile is especially useful as a before/after check. Pay attention to `generated_cpp_bytes`, `host_object_ms`, `host_link_ms`, and the complete user-visible compile time for `hot_loop`, `lambda_map`, and `pointer_rc`.
