#!/usr/bin/env bash
# Install a built AEE into a mod folder. Copies the WHOLE build root.
#
# Why this exists. The first version of this was a hand-written command that
# copied addons/*.pbo, mod.cpp and meta.cpp. HEMTT also puts LICENSE,
# README.md and logo_aee_ca.paa in the build root, so the mod folder was
# missing its logo and Arma logged "Picture logo_aee_ca.paa not found" four
# times per session. No gate saw it, because a dedicated server never renders
# the mod list and so never asks for the logo. Copying the tree removes the
# class of fault rather than the instance.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.hemttout/build"
DEST="${1:-$HOME/Downloads/@aee}"

if [ ! -d "$SRC/addons" ]; then
    echo "no build at $SRC. Run: hemtt build" >&2
    exit 1
fi

rm -rf "$DEST"
mkdir -p "$DEST"
cp -a "$SRC/." "$DEST/"

pbos=$(find "$DEST/addons" -name '*.pbo' | wc -l)
echo "installed $pbos PBOs to $DEST"
echo "root files: $(find "$DEST" -maxdepth 1 -type f -printf '%f ' )"

# The logo is the file this script exists for, so check it by name.
for f in logo_aee_ca.paa mod.cpp meta.cpp; do
    if [ ! -f "$DEST/$f" ]; then
        echo "MISSING $f in $DEST" >&2
        exit 1
    fi
done
echo "verified: logo, mod.cpp and meta.cpp present at the mod root"
