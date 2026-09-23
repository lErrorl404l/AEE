#!/usr/bin/env bash
#
# Test the equipment resolver against a real gear mod's classnames.
#
# A gear mod ships thousands of classes, so the mod is NEVER fully
# extracted: that filled 19 GB of temporary space. Each PBO's binarised
# config.bin is read into memory with `armake cat`, derapified to a single
# scratch file, scanned for the clothing classnames, and the scratch is
# deleted at once. Only the classname list is kept, a few kilobytes.
#
# Run:  tools/validation/scan_gear_mod.sh <workshop-id>
#
set -euo pipefail

ID="${1:?usage: scan_gear_mod.sh <workshop-id>}"
WORKSHOP="/ext/SteamLibrary/steamapps/workshop/content/107410/${ID}"
OUT="$(mktemp -d)/gear_classes.txt"
SCRATCH="$(mktemp -d)"

if [ ! -d "$WORKSHOP" ]; then
    echo "ERROR: no workshop item at $WORKSHOP" >&2
    exit 1
fi

: >"$OUT"
for PBO in "$WORKSHOP"/*.pbo "$WORKSHOP"/addons/*.pbo; do
    [ -f "$PBO" ] || continue
    # Read config.bin into memory, then to one scratch file.
    armake cat "$PBO" config.bin >"$SCRATCH/one.bin" 2>/dev/null || continue
    [ -s "$SCRATCH/one.bin" ] || continue
    armake derapify "$SCRATCH/one.bin" "$SCRATCH/one.cpp" >/dev/null 2>&1 || continue
    grep -oE "class (U_|V_|H_|B_)[A-Za-z0-9_]+" "$SCRATCH/one.cpp" 2>/dev/null |
        sed 's/class //' >>"$OUT" || true
    rm -f "$SCRATCH/one.bin" "$SCRATCH/one.cpp"
done

sort -u "$OUT" -o "$OUT"
echo "classnames: $(wc -l <"$OUT")  written to $OUT"
echo "scratch: $(du -sh "$SCRATCH" | cut -f1)"
