#!/usr/bin/env bash
# Render build script — installs deps and prepares the app
set -o errexit

echo "=== Installing Python dependencies ==="

# Use writable Rust/Cargo locations (Render system paths are read-only)
export CARGO_HOME=/tmp/.cargo
export RUSTUP_HOME=/tmp/.rustup
mkdir -p "$CARGO_HOME" "$RUSTUP_HOME"

# Create pip config to prefer wheels but allow source fallback when needed
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
prefer-binary = True
timeout = 180

[install]
no-cache-dir = True
EOF

pip install --upgrade pip

# Install dependencies (source build allowed for packages lacking cp314 wheels)
pip install --prefer-binary --no-cache-dir -r requirements.txt

echo "=== Creating required directories ==="
mkdir -p /tmp/kyc_chroma_db
mkdir -p /tmp/flashrank

echo "=== Build complete ==="
