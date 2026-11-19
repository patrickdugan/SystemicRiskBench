#!/usr/bin/env bash
set -euo pipefail
: "${REV05_TMP:=/tmp/srb-rev05}"
mkdir -p "$REV05_TMP/server" "$REV05_TMP/models" artifacts/rev05-ci
url="https://github.com/ggml-org/llama.cpp/releases/download/b12248/llama-b12248-bin-ubuntu-x64.tar.gz"
curl -fL --retry 4 --retry-all-errors --connect-timeout 30 --max-time 400 "$url" -o "$REV05_TMP/llama.tar.gz"
echo "6b3a530b44f6b0a4ae4872d3b3c8d1edc2ac6bba7d8bd211329a4ba644c0dc65  $REV05_TMP/llama.tar.gz" | sha256sum -c -
tar -xzf "$REV05_TMP/llama.tar.gz" -C "$REV05_TMP/server"
server="$(find "$REV05_TMP/server" -type f -name llama-server | head -n 1)"
test -n "$server"
chmod +x "$server"
echo "LLAMA_SERVER=$server" >> "$GITHUB_ENV"
echo "LD_LIBRARY_PATH=$(dirname "$server")" >> "$GITHUB_ENV"
"$server" --help > "$REV05_TMP/server-help.txt" 2>&1
grep -q -- '--lora' "$REV05_TMP/server-help.txt"
grep -Eq -- '--device|--n-gpu-layers' "$REV05_TMP/server-help.txt"
echo "PASS: pinned Linux CPU llama.cpp build and server CLI options"
