#!/usr/bin/env bash
# Run HEMTT with an open-file limit large enough for the marker set.
#
# HEMTT holds about one file descriptor per file it packs until the addon is
# written.  The optics addon alone holds the 5,516 marker .paa files, so the
# build needs a soft nofile limit far above the usual default (Docker ships
# 2048).  Raise the soft limit to the hard limit, then let the guard fail
# loudly when even that is too low.  Every HEMTT invocation in the repository
# goes through this wrapper.
#
# Override the target with AEE_NOFILE_LIMIT.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

hard="$(ulimit -Hn)"
target="${AEE_NOFILE_LIMIT:-1048576}"
if [ "$hard" != "unlimited" ] && [ "$target" -gt "$hard" ]; then
    target="$hard"
fi
# Raise the soft limit only: an unprivileged process may lift its soft limit
# up to the hard limit, but must not touch the hard limit itself.
ulimit -S -n "$target" 2>/dev/null || ulimit -S -n "$hard" 2>/dev/null || true

# Assert the achieved limit can hold the build; fails loudly otherwise.
python3 "$ROOT/tools/check_fd_limit.py"

exec hemtt "$@"
