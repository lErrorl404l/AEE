#!/usr/bin/env bash
# Extract the latest released version section from root CHANGELOG.md
# into .hemtt/changelog.md for HEMTT Workshop publish.
#
# HEMTT extracts by version number (not "Unreleased"), so this script
# finds the first "## [x.y.z]" header and copies that section.

set -euo pipefail

ROOT="CHANGELOG.md"
OUT=".hemtt/changelog.md"

if [[ ! -f "$ROOT" ]]; then
    echo "ERROR: $ROOT not found" >&2
    exit 1
fi

# Find the first versioned header (skip [Unreleased])
VERSION_LINE=$(grep -m1 '^## \[[0-9]' "$ROOT" || true)

if [[ -z "$VERSION_LINE" ]]; then
    echo "ERROR: No versioned section found in $ROOT" >&2
    exit 1
fi

# Extract version number from header like "## [1.0.0] - 2026-09-11"
VERSION=$(echo "$VERSION_LINE" | sed 's/^## \[\([^]]*\)\].*/\1/')

echo "Latest version: $VERSION"

# Extract from this header to the next "## [" or end of file
awk -v ver="$VERSION" '
/^## \[/ {
    if (found) exit
    if ($0 ~ "^## \\[" ver "\\]") found=1
    next
}
found { print }
' "$ROOT" >/tmp/changelog_section.txt

if [[ ! -s /tmp/changelog_section.txt ]]; then
    echo "ERROR: No content found for version $VERSION" >&2
    exit 1
fi

cat >"$OUT" <<HEADER
# Changelog

## [$VERSION]

HEADER

cat /tmp/changelog_section.txt >>"$OUT"
rm -f /tmp/changelog_section.txt

echo "Generated $OUT from $ROOT (version $VERSION)"
