#!/usr/bin/env bash
# Build the aee_dev cdylib against the Arma dedicated-server glibc.
#
# The server image (ghcr.io/brettmayson/arma3server/arma3server:v3) is Debian 12
# with glibc 2.36. A build that links a newer glibc emits a GLIBC_2.39
# requirement from the Rust standard library (the weak pidfd_spawnp and
# pidfd_getpid references). The server then refuses the extension:
#
#   Call extension 'aee_dev' could not be loaded
#
# This script builds inside a Debian 12 container, so the result needs no glibc
# newer than the server. It stages dist/aee_dev_x64.so for the harness to
# mount.
#
# Usage: build-linux.sh
#
# Override the image with AEE_DEV_BUILD_IMAGE. The image must be Debian 12
# based, so its glibc is not newer than the server glibc.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST="$DIR/dist"
IMAGE="${AEE_DEV_BUILD_IMAGE:-rust:bookworm}"
mkdir -p "$DIST"

# Build as the calling user, so target/ and dist/ stay host-owned. Reuse the
# host cargo registry when it exists, so a repeat build needs no network for
# the dependencies. The container CARGO_HOME sits under the gitignored target/
# directory: mounting the whole host ~/.cargo would also apply the host cargo
# config (a clang/mold linker this image does not carry).
mounts=(-v "$DIR:/src" -w /src)
cargo_home="${CARGO_HOME:-$HOME/.cargo}"
container_cargo_home=/src/target/.cargo
if [ -d "$cargo_home/registry" ]; then
    mkdir -p "$DIR/target/.cargo/registry"
    mounts+=(-v "$cargo_home/registry:$container_cargo_home/registry")
fi

docker run --rm \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -e "CARGO_HOME=$container_cargo_home" \
    "${mounts[@]}" \
    "$IMAGE" \
    cargo build --release

cp "$DIR/target/release/libaee_dev.so" "$DIST/aee_dev_x64.so"

echo "staged $DIST/aee_dev_x64.so"
echo -n "highest glibc requirement (must not exceed the server glibc): "
objdump -T "$DIST/aee_dev_x64.so" | grep -oE 'GLIBC_2\.[0-9]+' | sort -uV | tail -1
