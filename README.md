# Strut Benchmarks

A reproducible local benchmark suite for comparing **Strut, C++, Rust, and Go** on the same small programs.

The first goal is not to manufacture a winner. It is to give us raw evidence we can use while dogfooding and profiling Strut: runtime performance, peak resident memory, release binary size, compile time, and source verbosity.

## What is measured

For every task/language pair the runner records:

- median release compile time;
- median wall-clock runtime;
- median peak RSS on Linux when GNU `time` is available;
- release executable size in bytes;
- source bytes;
- non-blank source lines;
- approximate lexical token count;
- all individual timing/RSS samples;
- exact compiler/toolchain versions and machine information.

The runner validates program stdout before accepting timing results. A benchmark that compiles but produces the wrong result is recorded as a failure, not timed as if it were valid.

## Initial workloads

| Benchmark | Purpose |
| --- | --- |
| `hello` | process startup, minimal output, binary-size floor |
| `arithmetic` | 50 million integer modulo/add iterations |
| `fibonacci` | recursive `fib(40)` and scalar function-call overhead |
| `vector_sum` | dynamic-array growth, traversal, integer accumulation |
| `threads` | four concurrent CPU workers and join/synchronisation overhead |
| `hot_loop` | longer scalar integer loop so process startup is negligible |
| `lambda_map` | dynamic-array growth plus higher-order lambda transform |
| `pointer_rc` | repeated safe-pointer ownership copies/dereferences |

Each implementation uses the same constants and must produce the exact same output.

The initial suite deliberately avoids third-party benchmark libraries. It uses the standard/core facilities of each language so the source-size and compile-time measurements do not quietly include a framework in one language but not another.

## Requirements

For the full matrix:

- Strut compiler;
- a C++ compiler (`g++` by default, or `CXX=clang++`);
- `rustc`;
- Go;
- Python 3;
- GNU `/usr/bin/time` on Linux for peak-RSS measurements.

Unavailable toolchains are skipped unless `--require-all` is supplied.

### Build Strut

From this repository's sibling workspace layout:

```bash
cmake -S ../strut -B ../strut/build -DCMAKE_BUILD_TYPE=Release
cmake --build ../strut/build -j
```

Then:

```bash
./run.sh --strut ../strut/build/strut
```

You can also set:

```bash
export STRUT_BIN=/path/to/strut
./run.sh
```

## Normal run

```bash
./run.sh --strut ../strut/build/strut
```

Defaults:

- 3 measured compile runs;
- 2 runtime warmups;
- 10 measured runtime runs;
- 3 peak-RSS runs;
- all available languages;
- all workloads.

A quick smoke run is:

```bash
./run.sh --strut ../strut/build/strut --quick
```

To require the complete four-language matrix:

```bash
./run.sh --strut ../strut/build/strut --require-all
```

Select workloads or languages:

```bash
./run.sh \
  --strut ../strut/build/strut \
  --languages strut,cpp,rust,go \
  --tasks arithmetic,fibonacci,vector_sum
```

Increase repetitions for a serious local run:

```bash
./run.sh \
  --strut ../strut/build/strut \
  --compile-runs 10 \
  --runtime-runs 30 \
  --memory-runs 5 \
  --warmup-runs 5 \
  --require-all
```

For a cleaner performance run, close browsers/IDEs and other background workloads first, keep the machine on AC power, and avoid running other compilers at the same time.

## Results

Every run writes:

```text
results/results-YYYYMMDD-HHMMSS.json
results/results-YYYYMMDD-HHMMSS.csv
results/results-YYYYMMDD-HHMMSS.md
```

and refreshes:

```text
results/latest.json
results/latest.csv
results/latest.md
```

The JSON file is the canonical raw result to send back for analysis. It contains the individual samples rather than only medians.

Generated results are ignored by Git by default; commit a result deliberately only when it is intended to become a published baseline.

## Release flags

The default commands are intentionally visible in `run.py`.

- Strut: `strut source.p --release -o output`
- C++: `-std=c++20 -O2 -DNDEBUG -pthread -s`
- Rust: `-C opt-level=2 -C strip=symbols`
- Go: `go build -ldflags="-s -w"`

These are meant to represent practical stripped release builds, not "maximum benchmark mode" for one compiler and normal release mode for another.

Strut currently lowers through its C++ bootstrap backend. Its compile-time result therefore intentionally measures the real user-visible Strut compilation path, including the native backend invocation.

## Interpreting the numbers

A few caveats matter:

- **Binary size** is the executable file itself. Dynamically linked library files are not added to that number.
- Rust's normal standard-library linkage, Go's runtime, and C++/Strut dynamic library choices differ. That is useful deployment evidence, but it is not a measurement of identical linkage strategies.
- **RSS** is peak resident memory reported by GNU `time` on Linux. On platforms where the runner cannot obtain a compatible measurement it is left blank rather than guessed.
- Compile times are warm-toolchain application builds: the output executable is removed before every measured run, but system/compiler caches are not flushed.
- Token count is a deliberately simple language-neutral lexical approximation. Use it alongside bytes and non-blank LOC rather than treating it as a compiler-token count.
- Concurrency abstractions differ. `threads` measures the natural supported mechanism in each implementation, not identical runtime internals.

## Adding a benchmark

1. Add equivalent source files under all four language directories:

```text
benchmarks/strut/name.p
benchmarks/cpp/name.cpp
benchmarks/rust/name.rs
benchmarks/go/name.go
```

2. Add the workload and exact expected stdout to `benchmarks.json`.
3. Keep constants/work performed semantically equivalent.
4. Avoid I/O inside the hot loop unless I/O itself is the benchmark.
5. Make the final observable output depend on the calculation so optimisers cannot simply discard it.
6. Run `./run.sh --quick --tasks name --require-all` before accepting it.

When an optimisation opportunity is found, keep the old raw result and rerun the exact same source workload after the change. That gives us defensible before/after evidence rather than moving the benchmark to suit the implementation.

## Profiling and optimisation

The normal matrix tells us **where** Strut differs. `PROFILING.md` and `tools/` are for finding **why**.

```bash
./profile.sh --runs 20
python3 tools/profile_hotspot.py vector_sum --strut ../strut/build/strut
python3 tools/compare_asm.py vector_sum --strut ../strut/build/strut
python3 tools/profile_features.py --strut ../strut/build/strut
```

The current Strut compiler also supports:

```bash
strut program.p --release --timings -o program
strut program.p --release --emit-cpp generated.cpp
```

This lets the suite separate Strut frontend work from generated-C++ compilation/linking instead of treating the bootstrap pipeline as one opaque compile-time number. See `PROFILING.md` for the files to send back after a local profiling run. The feature profiler separately exercises JSON, async, SQLite and local HTTP paths without pretending those are already dependency-equivalent cross-language comparisons.

### Collection-capacity fairness

Where a reference implementation explicitly reserves collection capacity before a fixed-size growth workload, the Strut implementation does the same using `array.reserve(...)`. Where the reference does not reserve, Strut does not either. This avoids attributing predictable reallocation differences to the language/runtime rather than to different source algorithms.

## Standard-library benchmarks

The manifest now includes hash-map, ordered-map, hash-set, queue, stack, and max-priority-queue workloads alongside the existing vector workload. C++ and Rust use their standard ordered/hash containers. Go has no standard ordered-map/tree-map type, so the `ordered_map` Go case is explicitly only its nearest built-in map baseline and must not be presented as an ordered-container equivalence.

Additional profiling tools:

- `tools/profile_modules.py` measures per-module compile time and generated C++ size.
- `tools/check_codegen_budget.py` trips on large accidental generated-runtime growth.
- `tools/profile_file_io.py` measures cached whole-file reads at 1 KiB, 1 MiB and 100 MiB by default.
- `tools/profile_filesystem.py` compares recursive directory traversal against C++/Rust/Go on a generated tree and records the environment caveat explicitly.
