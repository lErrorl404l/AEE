#!/usr/bin/env bash
# Build the standalone dev harness into @aee_dev.
#
# This project lives outside addons/ and optionals/, so the main project's
# hemtt build and hemtt release cannot see it (HEMTT builds only those two
# directories). The dev PBO is therefore impossible in a release by
# construction.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"

# Shared include mirror: HEMTT resolves an include of \x\... from the
# project's include/ directory. The dev addon reuses the vendored CBA
# headers, so mirror them into this project rather than copy them.
mkdir -p "$DIR/include/x"
ln -sfn "$ROOT/include/x/cba" "$DIR/include/x/cba"

cd "$DIR"
"$ROOT/tools/hemtt.sh" build

# Stage the built mod as @aee_dev. Keep it out of git (see .gitignore).
rm -rf "$DIR/@aee_dev"
mkdir -p "$DIR/@aee_dev"
cp -a "$DIR/.hemttout/build/." "$DIR/@aee_dev/"

echo "built @aee_dev:"
find "$DIR/@aee_dev" -type f | sort
