#!/usr/bin/env bash
# Render build script — installs deps and prepares the app
set -o errexit

echo "=== Installing Python dependencies ==="
pip install --upgrade pip

# Disable Cargo telemetry to avoid read-only filesystem errors
export CARGO_NET_OFFLINE=false
export RUST_LOG=info

# Install with pre-built wheels only to avoid Rust compilation issues
pip install --only-binary :all: tokenizers==0.19.1 || pip install tokenizers==0.19.1

# Install all requirements
pip install -r requirements.txt

echo "=== Creating required directories ==="
mkdir -p /tmp/kyc_chroma_db
mkdir -p /tmp/flashrank

echo "=== Build complete ==="
