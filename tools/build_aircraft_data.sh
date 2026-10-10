#!/usr/bin/env bash
#
# Build the verified aircraft catalogue and its runtime projection.
#
# One command, no network. Fetching a new source document is a separate act
# that adds a source to the registry; this script only reads the corpus.
#
# The order is not arbitrary. The validator is the oracle for provenance, so
# it gates the corpus before anything downstream reads it. The coverage guard
# and the generator both read the validated corpus. The freshness checks prove
# the committed outputs are current, so a stale projection fails the build.
#
# Run:  tools/build_aircraft_data.sh
#
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
V="tools/validation"

step() {
    printf '\n==> %s\n' "$1"
    shift
    "$PYTHON" "$@"
}

# The gate: no value without a source, no config number, no unsourced runtime
# field. It runs first because a corpus that fails here must not be projected.
step "gate: aircraft data contract" "$V/validate_aircraft_data.py"

# The coverage guard reads the four air tokens and writes coverage.json with
# the audit and the two gap reports. It runs before the projection so the
# reports describe the corpus the projection was built from.
step "coverage: air tokens and gaps" "$V/gen_aircraft_coverage.py"

# The generators write the runtime SQF projections from the validated corpus.
# The four-value row and the systems row are separate lookups. Neither reads a
# source registry at runtime.
step "runtime: aircraft projection" "$V/gen_aircraft_data.py"
step "runtime: aircraft systems lookup" "$V/gen_aircraft_systems.py"

# The config projection writes the one CfgVehicles block, the aircraft keys
# and the land physics surface. It is the sole owner of that block.
step "config: load-time CfgVehicles projection" "$V/gen_physics_config.py"

# The freshness checks re-run each writer with --check. They write nothing and
# exit 1 when a committed output does not match the corpus.
step "check: coverage freshness" "$V/gen_aircraft_coverage.py" --check
step "check: projection freshness" "$V/gen_aircraft_data.py" --check
step "check: systems freshness" "$V/gen_aircraft_systems.py" --check
step "check: config freshness" "$V/gen_physics_config.py" --check

printf '\naircraft data: complete\n'
