#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args, cwd, env=None):
    started = time.perf_counter_ns()
    result = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elapsed = (time.perf_counter_ns() - started) / 1e6
    if result.returncode:
        raise RuntimeError(f"{args} failed:\n{result.stdout}\n{result.stderr}")
    return elapsed, result.stdout


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def make_repo(root, name, dependencies):
    repo = root / name
    repo.mkdir()
    run(["git", "init", "--quiet"], repo)
    run(["git", "config", "user.email", "benchmark@strut.invalid"], repo)
    run(["git", "config", "user.name", "Strut Benchmark"], repo)
    write_json(repo / "strut.json", {"name": name, "version": "1.0.0", "entry": "main.p",
                                      "dependencies": dependencies})
    (repo / "main.p").write_text(f"function {name.replace('-', '_')}_value() -> int {{ return 1; }}\n")
    run(["git", "add", "."], repo)
    run(["git", "commit", "--quiet", "-m", "fixture"], repo)
    return repo, run(["git", "rev-parse", "HEAD"], repo)[1].strip()


def summary(values):
    ordered = sorted(values)
    return {"median": statistics.median(values), "min": ordered[0], "max": ordered[-1], "runs": values}


def main():
    parser = argparse.ArgumentParser(description="Profile warm-cache Strut package operations on a diamond graph.")
    parser.add_argument("--strut", default="../strut/build/strut")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--output", default="profiles/results/package-latency.json")
    args = parser.parse_args()
    compiler = Path(args.strut)
    compiler = compiler if compiler.is_absolute() else (ROOT / compiler).resolve()
    timings = {name: [] for name in ("locked_offline_install", "packages_json", "project_json")}
    with tempfile.TemporaryDirectory(prefix="strut-package-profile-") as temporary:
        root = Path(temporary)
        remotes = root / "remotes"; remotes.mkdir()
        common, common_rev = make_repo(remotes, "common", {})
        dep = lambda repo, rev: {"version": "^1.0.0", "git": str(repo), "rev": rev}
        package_a, a_rev = make_repo(remotes, "package-a", {"common": dep(common, common_rev)})
        package_b, b_rev = make_repo(remotes, "package-b", {"common": dep(common, common_rev)})
        project = root / "project"; project.mkdir()
        write_json(project / "strut.json", {"name": "app", "version": "0.1.0", "entry": "main.p",
                   "dependencies": {"package-a": dep(package_a, a_rev), "package-b": dep(package_b, b_rev)}})
        (project / "main.p").write_text("function main() -> int { return 0; }\n")
        env = os.environ.copy(); env["STRUT_HOME"] = str(root / "home")
        run([compiler, "update"], project, env)
        offline_env = env.copy(); offline_env["PATH"] = str(root / "no-network-tools")
        for _ in range(args.runs):
            elapsed, _ = run([compiler, "install", "--offline"], project, offline_env)
            timings["locked_offline_install"].append(elapsed)
            elapsed, output = run([compiler, "packages", "--json"], project, env)
            assert len(json.loads(output)["packages"]) == 3
            timings["packages_json"].append(elapsed)
            elapsed, output = run([compiler, "project", "--json"], project, env)
            assert json.loads(output)["graph_fully_resolved"]
            timings["project_json"].append(elapsed)
    result = {"schema_version": 1, "hostname": platform.node(), "runs": args.runs,
              "graph": "diamond, 3 unique transitive packages", "latency_ms": {k: summary(v) for k, v in timings.items()}}
    output = ROOT / args.output; output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
