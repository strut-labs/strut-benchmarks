#!/usr/bin/env bash
# Bootstrap a benchmark node. No Linode API token required.
# Usage: bootstrap.sh server|generator
set -euo pipefail
ROLE="${1:?usage: bootstrap.sh server|generator}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends ca-certificates curl git build-essential pkg-config

if [ "$ROLE" = "server" ]; then
    # Swap so the 1 GB node can compile Rust/Strut-generated C++.
    if ! swapon --show | grep -q /swapfile; then
        fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
    # Go toolchain (tarball keeps a current version rather than the distro's).
    if ! command -v go >/dev/null 2>&1; then
        GOARCH_VER="go1.26.0"
        curl -fsSL "https://go.dev/dl/${GOARCH_VER}.linux-amd64.tar.gz" -o /tmp/go.tgz
        rm -rf /usr/local/go
        tar -C /usr/local -xzf /tmp/go.tgz
        ln -sf /usr/local/go/bin/go /usr/local/bin/go
        ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt
    fi
    # Rust toolchain.
    if ! command -v cargo >/dev/null 2>&1; then
        curl -fsSL https://sh.rustup.rs -o /tmp/rustup.sh
        sh /tmp/rustup.sh -y --profile minimal --default-toolchain stable
        ln -sf /root/.cargo/bin/cargo /usr/local/bin/cargo || true
        ln -sf /root/.cargo/bin/rustc /usr/local/bin/rustc || true
    fi
    echo "server bootstrap complete"
else
    # Load generator: wrk built from source.
    apt-get install -y --no-install-recommends libssl-dev
    if ! command -v wrk >/dev/null 2>&1; then
        cd /tmp
        rm -rf wrk
        git clone --depth 1 https://github.com/wg/wrk.git
        make -C wrk -j"$(nproc)"
        install -m 0755 wrk/wrk /usr/local/bin/wrk
    fi
    echo "generator bootstrap complete"
fi

echo "--- versions ---"
command -v go >/dev/null 2>&1 && go version || true
command -v rustc >/dev/null 2>&1 && rustc --version || true
command -v cargo >/dev/null 2>&1 && cargo --version || true
command -v g++ >/dev/null 2>&1 && g++ --version | head -1 || true
command -v wrk >/dev/null 2>&1 && wrk --version 2>&1 | head -1 || true
