#!/usr/bin/env bash
# Render build script — installs deps and prepares the app
set -o errexit

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Creating required directories ==="
mkdir -p /tmp/kyc_chroma_db
mkdir -p /tmp/flashrank

echo "=== Build complete ==="
