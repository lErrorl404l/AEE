#!/usr/bin/env bash
#
# Profile the environment tick on the docker dedicated server.
#
# Builds with ENABLE_PERFORMANCE_COUNTERS, runs the harness, and prints the
# per-phase ms/call that fnc_dumpPerformanceCounters writes to the RPT. The
# define is restored by a trap, so the working tree is left exactly as found
# even if the run fails.
#
# The counters measure wall time per phase, which is what decides whether a
# remaining candidate is worth changing. Static call counting cannot.
#
# Run:  bash tools/validation/profile_tick.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

DEBUG_HPP="addons/main/script_debug.hpp"
BACKUP="$(mktemp)"
cp "$DEBUG_HPP" "$BACKUP"

restore() {
    cp "$BACKUP" "$DEBUG_HPP"
    rm -f "$BACKUP"
    echo "==> script_debug.hpp restored"
}
trap restore EXIT

# Enable the counters. The define sits commented in the header.
sed -i 's|^//#define ENABLE_PERFORMANCE_COUNTERS$|#define ENABLE_PERFORMANCE_COUNTERS|' "$DEBUG_HPP"
if ! grep -q '^#define ENABLE_PERFORMANCE_COUNTERS' "$DEBUG_HPP"; then
    echo "ERROR: could not enable ENABLE_PERFORMANCE_COUNTERS" >&2
    exit 1
fi
echo "==> counters enabled"

# PHASE27 of the Stratis mission already invokes the dump function, so no
# mission patch is needed: enabling the define is enough. The counters are
# per machine and the server is the machine a milsim unit sizes hardware
# for, so the dedicated server is the right one to measure.

echo "==> running the harness (this takes a few minutes)"
bash tools/docker_test.sh >/dev/null 2>&1 || true

echo
echo "=== PER-PHASE COST (ms/call, heaviest first) ==="
sed -n '/=== AEE COUNTER RESULTS/,/=== END COUNTER RESULTS/p' tests/docker/run.log |
    sed 's/^.*| *//' |
    grep -E "ms/call" |
    head -25

echo
echo "=== phases failed / result ==="
grep -E "phases failed|RESULT" tests/docker/run.log | tail -2
