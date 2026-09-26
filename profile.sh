#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

STRUT_DIR="${STRUT_DIR:-../strut}"
BUILD_DIR="${STRUT_BUILD_DIR:-$STRUT_DIR/build}"
STRUT_BIN="${STRUT_BIN:-$BUILD_DIR/strut}"
RUNS="${PROFILE_RUNS:-10}"
BUILD_JOBS="${STRUT_BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)}"
BENCH_LANGUAGES="${PROFILE_BENCH_LANGUAGES:-strut,cpp,rust,go}"
BENCH_TASKS="${PROFILE_BENCH_TASKS:-hot_loop,lambda_map,pointer_rc,pointer_rc_long,vector_sum,hash_map,ordered_map,hash_set,queue_ops,queue_ops_long,stack_ops,priority_queue_ops}"

# CMake caches absolute source paths. A build/ directory copied or extracted from
# another machine/workspace is not reusable and can leave Strut embedding stale
# dependency paths (notably JSONIC). Detect that case and recreate only build/.
CACHE="$BUILD_DIR/CMakeCache.txt"
if [[ -f "$CACHE" ]]; then
  cached_home="$(sed -n 's/^CMAKE_HOME_DIRECTORY:INTERNAL=//p' "$CACHE" | tail -n1)"
  wanted_home="$(cd "$STRUT_DIR" && pwd -P)"
  if [[ -n "$cached_home" && "$cached_home" != "$wanted_home" ]]; then
    echo "Stale/moved CMake build detected:"
    echo "  cached source: $cached_home"
    echo "  current source: $wanted_home"
    echo "Recreating $BUILD_DIR so embedded dependency paths match this workspace."
    rm -rf "$BUILD_DIR"
  fi
fi

echo "==> Configure/build Strut (Release)"
cmake -S "$STRUT_DIR" -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Release
cmake --build "$BUILD_DIR" -j "$BUILD_JOBS"

echo "==> Strut tests"
ctest --test-dir "$BUILD_DIR" --output-on-failure

STRUT_BIN="$(cd "$(dirname "$STRUT_BIN")" && pwd -P)/$(basename "$STRUT_BIN")"
if [[ ! -x "$STRUT_BIN" ]]; then
  echo "Strut compiler was not produced at $STRUT_BIN" >&2
  exit 2
fi

echo "==> Compiler profiles"
python3 tools/profile_compile.py --strut "$STRUT_BIN" --source benchmarks/strut/hot_loop.p --runs "$RUNS" --output profiles/results/compile-hot-loop.json
python3 tools/profile_compile.py --strut "$STRUT_BIN" --source benchmarks/strut/lambda_map.p --runs "$RUNS" --output profiles/results/compile-lambda-map.json
python3 tools/profile_compile.py --strut "$STRUT_BIN" --source benchmarks/strut/pointer_rc.p --runs "$RUNS" --output profiles/results/compile-pointer-rc.json
python3 tools/profile_compile.py --strut "$STRUT_BIN" --source benchmarks/strut/pointer_rc_long.p --runs "$RUNS" --output profiles/results/compile-pointer-rc-long.json

echo "==> Incremental profile"
python3 tools/profile_incremental.py --strut "$STRUT_BIN"

echo "==> Project scale profile"
python3 tools/profile_project_scale.py --strut "$STRUT_BIN"

echo "==> Feature profile"
python3 tools/profile_features.py --strut "$STRUT_BIN"

echo "==> Standard-library module profile"
python3 tools/profile_modules.py --strut "$STRUT_BIN"

echo "==> Generated-code size budget"
python3 tools/check_codegen_budget.py --strut "$STRUT_BIN"

if [[ "${PROFILE_SKIP_BENCHMARKS:-0}" != "1" ]]; then
  echo "==> Same-machine benchmark results (refreshes results/latest.{json,csv,md})"
  python3 run.py --strut "$STRUT_BIN" --compile-runs "${PROFILE_BENCH_COMPILE_RUNS:-5}" --runtime-runs "${PROFILE_BENCH_RUNTIME_RUNS:-10}" --memory-runs "${PROFILE_BENCH_MEMORY_RUNS:-3}" --warmup-runs "${PROFILE_BENCH_WARMUP_RUNS:-3}" --languages "$BENCH_LANGUAGES" --tasks "$BENCH_TASKS"
fi

echo
echo "Compiler/incremental/feature/module profiles complete."
echo "Fresh benchmark aliases are under results/latest.{json,csv,md}."
echo "For runtime hotspots run:"
echo "  python3 tools/profile_hotspot.py vector_sum --strut '$STRUT_BIN'"
echo "  python3 tools/profile_hotspot.py pointer_rc_long --strut '$STRUT_BIN'"
echo "  python3 tools/profile_hotspot.py lambda_map --strut '$STRUT_BIN'"
echo "  python3 tools/compare_asm.py vector_sum --strut '$STRUT_BIN'"
echo "  python3 tools/compare_asm.py lambda_map --strut '$STRUT_BIN'"
echo "  python3 tools/compare_asm.py pointer_rc_long --strut '$STRUT_BIN'"

echo "Optional heavier I/O profile:"
echo "  python3 tools/profile_file_io.py --strut '$STRUT_BIN'"
echo "  python3 tools/profile_filesystem.py --strut '$STRUT_BIN'"
