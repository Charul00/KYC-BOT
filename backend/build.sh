#!/usr/bin/env bash
# Render build script — installs deps and prepares the app
set -o errexit

echo "=== Installing Python dependencies ==="

# Create pip config to force binary-only installs
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
only-binary = :all:
prefer-binary = True
timeout = 180

[install]
no-cache-dir = True
EOF

pip install --upgrade pip

# Install strictly from wheels so Render never attempts Rust/maturin source builds.
pip install --only-binary :all: --prefer-binary --no-cache-dir -r requirements.txt

echo "=== Creating required directories ==="
mkdir -p /tmp/kyc_chroma_db
mkdir -p /tmp/flashrank

echo "=== Build complete ==="
