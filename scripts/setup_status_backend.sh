#!/bin/bash
# Start status-backend with proper library path
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BIN_DIR="$PROJECT_DIR/bin"
DATA_DIR="$PROJECT_DIR/data"

mkdir -p "$DATA_DIR"

PORT="${1:-12345}"

echo "Starting status-backend on 127.0.0.1:$PORT..."
echo "Data dir: $DATA_DIR"
echo "Press Ctrl+C to stop"

DYLD_LIBRARY_PATH="$BIN_DIR" "$BIN_DIR/status-backend" --address "127.0.0.1:$PORT"
