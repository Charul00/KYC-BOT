#!/usr/bin/env bash
# Render build script — installs deps and prepares the app
set -o errexit

echo "=== Installing Python dependencies ==="
pip install --upgrade pip

# Force pre-built wheels to avoid Rust compilation on Render
# Render has read-only filesystem restrictions that break maturin builds
export PIP_NO_BUILD_ISOLATION=1
export CRYPTOGRAPHY_DONT_BUILD_RUST=1

# Install with --no-build-isolation to use only pre-built wheels
pip install --no-build-isolation --only-binary :all: -r requirements.txt || \
pip install -r requirements.txt

echo "=== Creating required directories ==="
mkdir -p /tmp/kyc_chroma_db
mkdir -p /tmp/flashrank

echo "=== Build complete ==="
