#!/usr/bin/env bash
# Build the aee_dev extension and stage it under Arma's `_x64` names.
#
# Arma loads a 64-bit extension named <name>_x64.<ext> and a 32-bit extension
# named <name>.<ext>.  cargo names the Linux cdylib `libaee_dev.so` and the
# Windows cdylib `aee_dev.dll`; this script renames each to the engine name.
#
#   linux   -> dist/aee_dev_x64.so
#   windows -> dist/aee_dev_x64.dll  (via cargo-xwin, the MSVC target)
#
# Usage: build.sh [linux|windows]
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST="$DIR/dist"
mkdir -p "$DIST"

case "${1:-linux}" in
linux)
    cargo build --release --manifest-path "$DIR/Cargo.toml"
    cp "$DIR/target/release/libaee_dev.so" "$DIST/aee_dev_x64.so"
    ;;
windows)
    # cargo-xwin drives the MSVC linker (lld-link) and downloads the Windows
    # CRT/SDK when it is not already cached.
    cargo xwin build --release \
        --target x86_64-pc-windows-msvc \
        --manifest-path "$DIR/Cargo.toml"
    cp "$DIR/target/x86_64-pc-windows-msvc/release/aee_dev.dll" \
        "$DIST/aee_dev_x64.dll"
    ;;
*)
    echo "usage: $0 [linux|windows]" >&2
    exit 2
    ;;
esac

echo "staged:"
find "$DIST" -type f | sort
