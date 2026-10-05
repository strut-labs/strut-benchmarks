#!/usr/bin/env bash
# Provision the two benchmark Linodes. Requires the local Linode CLI to be
# authenticated via the environment (LINODE_CLI_TOKEN). This script NEVER
# embeds or prints the token.
set -euo pipefail
REGION="${REGION:-us-east}"
TYPE="${TYPE:-g6-nanode-1}"
IMAGE="${IMAGE:-linode/ubuntu24.04}"
PUBKEY="$(cat "${SSH_PUBKEY:-$HOME/.ssh/id_ed25519.pub}")"
label_a="${LABEL_A:-strutbench-a}"
label_b="${LABEL_B:-strutbench-b}"

create() {
    local label="$1"
    if linode-cli linodes list --json | jq -e --arg l "$label" '.[]|select(.label==$l)' >/dev/null; then
        echo "exists: $label"; return 0
    fi
    local rp; rp="$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24)"
    linode-cli linodes create --region "$REGION" --type "$TYPE" --image "$IMAGE" \
        --label "$label" --tags strut-http-bench \
        --authorized_keys "$PUBKEY" --root_pass "$rp" --json >/dev/null
    echo "created: $label"
}
create "$label_a"
create "$label_b"
linode-cli linodes list --json | jq -r '.[]|select(.label|test("strutbench"))|"\(.id)\t\(.label)\t\(.status)\t\(.ipv4[0])"'
