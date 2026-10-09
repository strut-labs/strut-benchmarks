#!/usr/bin/env bash
# Build the three benchmark servers on the server node (node A).
# Assumes strut bin at /root/bench/strut-bin and share/strut/jsonic alongside it.
set -euo pipefail
export PATH=/usr/local/go/bin:/root/.cargo/bin:$PATH
cd /root/bench
/root/bench/strut-bin --release strut/server.p -o strut_server
echo "strut build mode: release -O2 -flto -ffunction-sections -fdata-sections (compiled by host CXX)"
(cd go && go build -o /root/bench/go_server .)
(cd rust && cargo build --release)
echo "built: strut_server go_server rust/target/release/strutbench-http"
