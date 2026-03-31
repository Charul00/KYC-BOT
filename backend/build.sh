#!/usr/bin/env bash
# Render build script — installs deps and prepares the app
set -o errexit

echo "=== Installing Python dependencies ==="

# Use writable Rust/Cargo locations (Render system paths are read-only)
export CARGO_HOME=/tmp/.cargo
export RUSTUP_HOME=/tmp/.rustup
export PATH="$CARGO_HOME/bin:$PATH"
mkdir -p "$CARGO_HOME" "$RUSTUP_HOME"

# Ensure a usable Rust toolchain is available for packages that compile native extensions.
if ! command -v rustup >/dev/null 2>&1; then
	curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal --default-toolchain stable
fi

rustup toolchain install stable --profile minimal || true
rustup default stable

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
