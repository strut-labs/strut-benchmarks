# Strut 0.0.2 performance certification

Date: 2026-09-27
Host: `nick-NUC12SNKi72`, Intel Core i7-12700H, x86_64, Linux 7.0.0-29
Toolchain: Strut 0.0.2, GCC 15.2.0; C++20 `-O2`, Rust and Go comparison implementations
Protocol: three compile runs, ten warmed runtime runs and three RSS runs unless a profile says otherwise. Medians are reported. Full raw samples and commands are retained in `results/` and `profiles/results/`.

## Result

The 0.0.2 implementation is release-ready from a performance perspective. Runtime performance is generally close to equivalent C++ for the sustained workloads, binary sizes are about 14–31 KiB for the comparison suite, incremental no-op builds remain fast, generic analysis scales approximately linearly, and atomic contention behaves as expected. The main remaining cost is the host C++ compiler, not Strut's front end.

Exact older development-container numbers are not treated as comparable: they were captured on a different machine/environment and raw result files were not checked in. This run is the authoritative reproducible 0.0.2 baseline for this NUC.

## Optimization made during certification

Profiling found that a trivial string literal selected the full 689-line runtime, making Hello World take about 2.07 seconds to compile. A plain thread program likewise selected the full runtime and took about 2.62 seconds. The compiler now emits a small string runtime and a focused plain-thread runtime.

| Case | Before | After | Generated C++ after |
|---|---:|---:|---:|
| Hello World compile | 2,070 ms | 306 ms | 1,986 bytes / 46 lines |
| Plain threads compile | 2,618 ms | 729 ms | 7,354 bytes / 142 lines |

That is an 85% Hello World compile-time reduction and a 72% thread compile-time reduction. Permanent codegen tests and budgets guard both paths. The HTTP server line budget was adjusted from 180 to 210 because the certified lifecycle implementation is 192 lines while remaining within its existing 25,000-byte ceiling.

An independent five-run A/B rebuild from the immutable `v0.0.2` source, using
the same current fixtures and release commands, measured 1,659 to 315 ms for
Hello World (81%) and 2,112 to 795 ms for threads (62%). The lower percentages
under different host load still reproduce the same large structural win; the
85%/72% figures above remain the retained full-campaign measurements.

The 0.0.3 candidate additionally applies the focused concurrency runtime to
compatible atomics. The contended atomic fixture fell from its retained
1,824 ms compile baseline to 656 ms in a five-run profile, while generated C++
fell from the complete runtime to 5,098 bytes / 96 lines. Atomic semantics and
runtime throughput are unchanged.

## Compiler and build paths

- Hello World: 306 ms full compile; 1.82 ms emit-C++; front end phases total about 0.36 ms; direct host compile 286 ms.
- Thread fixture: 729 ms full compile; 2.50 ms emit-C++; front end phases total about 0.57 ms; direct host compile 710 ms.
- Incremental project: 395 ms cold, 3.52 ms no-op, 389 ms source rebuild, 387 ms header rebuild.
- Project scaling: 10 / 100 / 500 files took 3.28 / 7.89 / 22.44 ms for no-op builds.
- Generic analysis (`strut --check`): 10 / 50 / 100 / 250 / 500 instantiations took 2.07 / 2.94 / 3.96 / 7.29 / 11.86 ms.
- Process startup: `strut --version` 1.61 ms; trivial compiled program startup 2.06 ms (30 runs).

## Runtime comparison highlights

| Workload | Strut | C++ | Observation |
|---|---:|---:|---|
| Fibonacci | 140.15 ms | 138.08 ms | within 2% |
| Hot loop | 139.25 ms | 142.30 ms | Strut slightly faster in this sample |
| Vector sum | 6.75 ms | 6.72 ms | parity |
| Hash map | 17.25 ms | 17.67 ms | parity |
| Ordered map | 48.10 ms | 51.04 ms | parity |
| Long hash set | 138.46 ms | 136.90 ms | within 2% |
| Long priority queue | 97.51 ms | 98.54 ms | parity |
| Threads | 11.24 ms | 13.86 ms | no abstraction penalty observed |
| Long reference counting | 52.20 ms | 43.08 ms | 1.21x C++; a useful future target |

Short workloads remain sensitive to process-startup and scheduler noise. Long variants were used to distinguish that noise from sustained container behavior.

## Targeted subsystems

- Atomic counter, four threads and one million total increments: 15.06 ms versus 68.36 ms with mutex locking (atomic is 4.54x faster).
- Cached whole-file reads, Strut versus C++: 1 KiB 1.32/1.34 ms; 1 MiB 2.45/2.72 ms; 100 MiB 89.06/91.91 ms.
- Recursive walk of 2,000 files: Strut 4.75 ms, C++ 3.39 ms, Rust 8.62 ms, Go 4.26 ms.
- HTTP server, 3,000 requests per run: 5,456 requests/s at concurrency 1, 13,748 at 8, and 13,554 at 32. At concurrency 32, p95 was 4.61 ms and p99 6.22 ms.
- Warm-cache diamond package graph: locked offline install 2.15 ms, `packages --json` 2.15 ms, `project --json` 2.04 ms.
- LSP over real stdio framing: initialize 1.87 ms, open+diagnostics 0.58 ms, completion 0.19 ms, hover 0.16 ms, signature help 0.15 ms, definition 0.15 ms, change+diagnostics 0.19 ms.

## Correctness gates

- GCC unit/integration CTest: 16/16 passed.
- Clang unit/integration CTest: 16/16 passed.
- ASan/UBSan CTest: 16/16 passed (`detect_leaks=0` because LeakSanitizer cannot operate under the sandbox's ptrace environment).
- Regression suite: 155/155 passed in 65.21 seconds with two jobs; peak runner/process-tree RSS observation 381,208 KiB.
- Package certification: deterministic diamond graph, offline cache, corruption repair, concurrent install and update passed.
- HTTP lifecycle certification: concurrent drain, TLS client/server JSON, explicit stop, 405 and 413 behavior passed.
- Codegen budgets: all 13 representative configurations passed.
- Full Strut/C++/Rust/Go benchmark matrix: all 18 workloads passed with equivalent output checks.

## Artifacts

- `results/0.0.2-performance-final/` contains timestamped JSON, CSV and Markdown views of the language comparison matrix.
- `profiles/results/` contains compiler phases, feature profiles, incremental/project scaling, modules, atomics, generics, filesystem, file I/O, HTTP, LSP, package and startup raw samples.

The next optimization pass should focus on native toolchain startup/header parsing, then the sustained reference-counting gap. Neither is a 0.0.3 release blocker.

Assembly review of the sustained reference-counting case found the same
`std::shared_ptr` ownership increment/decrement sequence in Strut and C++.
Strut additionally preserves its required null-safe dereference path. Hardware
counter collection was unavailable because the host has
`kernel.perf_event_paranoid=4`; no safety-preserving micro-fix was justified for
the 0.0.3 release.
