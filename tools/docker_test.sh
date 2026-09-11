#!/bin/bash
# AEE headless docker test.
#
# Builds the mod PBOs, assembles @aee, downloads CBA if needed, runs the
# Arma 3 dedicated server (brettmayson/arma3server) with the test mission,
# captures the RPT output and verifies the phase results.
#
# Usage: tools/docker_test.sh [--baseline]
#   --baseline  run once without the AEE mod and report the mission boot,
#               for comparison against the modded run
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCKER="$ROOT/tests/docker"
MODS="$DOCKER/mods"
CBA_VERSION="v3.19.0"

# The Arma 3 server install. Prefer the existing local install, else a
# tests/docker/server directory (bootstrap it yourself with steamcmd).
if [ -d /ext/a3sql-docker/server ]; then
    export ARMA3_SERVER_ROOT=/ext/a3sql-docker/server
else
    export ARMA3_SERVER_ROOT="${ARMA3_SERVER_ROOT:-$DOCKER/server}"
fi

rm -rf "$DOCKER/configs/profiles"

clean_profiles() { docker run --rm -v "$DOCKER/configs:/c" alpine rm -rf /c/profiles 2>/dev/null || true; }
trap 'docker compose -f "$DOCKER/docker-compose.yml" down 2>/dev/null || true; clean_profiles' EXIT

echo "==> server root: $ARMA3_SERVER_ROOT"
echo "==> hemtt build"
(cd "$ROOT" && hemtt build >/dev/null)

echo "==> assemble @aee"
rm -rf "$MODS/@aee"
mkdir -p "$MODS/@aee/addons"
cp "$ROOT"/.hemttout/build/addons/*.pbo "$MODS/@aee/addons/"
cp "$ROOT"/.hemttout/build/mod.cpp "$MODS/@aee/mod.cpp"
cp "$ROOT"/.hemttout/build/meta.cpp "$MODS/@aee/meta.cpp"

echo "==> ensure @cba_a3"
if [ ! -d "$MODS/@cba_a3" ]; then
    curl -fsSL "https://github.com/CBATeam/CBA_A3/releases/download/${CBA_VERSION}/CBA_A3_${CBA_VERSION}.zip" -o /tmp/cba.zip
    unzip -oq /tmp/cba.zip -d "$MODS"
    rm /tmp/cba.zip
    # the release zip extracts an uppercase folder; normalise for the
    # case-sensitive linux filesystem
    [ -d "$MODS/@CBA_A3" ] && mv "$MODS/@CBA_A3" "$MODS/@cba_a3"
fi

BASELINE=0
if [ "${1:-}" = "--baseline" ]; then
    BASELINE=1
    echo "==> baseline run (no AEE mod)"
    sed 's|mods/@aee;mods/@cba_a3|mods/@cba_a3|' "$DOCKER/config.toml" > "$DOCKER/config.toml.baseline"
    mv "$DOCKER/config.toml" "$DOCKER/config.toml.modded"
    mv "$DOCKER/config.toml.baseline" "$DOCKER/config.toml"
fi

echo "==> docker compose up"
docker compose -f "$DOCKER/docker-compose.yml" up -d --force-recreate

echo "==> waiting for results (up to 180 s)"
for _ in $(seq 1 36); do
    if docker compose -f "$DOCKER/docker-compose.yml" logs 2>/dev/null | grep -q "\[AEE-TEST\] DONE"; then
        break
    fi
    sleep 5
done

echo "==> capturing log"
docker compose -f "$DOCKER/docker-compose.yml" logs > "$DOCKER/run.log" 2>&1

if [ "$BASELINE" = "1" ]; then
    echo "==> baseline captured to tests/docker/run.log (no verify gate)"
    echo "    phases in the baseline are expected to FAIL (no AEE loaded)"
else
    echo "==> verifying"
    python3 "$DOCKER/verify.py" "$DOCKER/run.log" \
        || { echo "harness failed; full log at tests/docker/run.log"; exit 1; }
fi

echo "==> teardown"
docker compose -f "$DOCKER/docker-compose.yml" down 2>/dev/null || true
if [ "$BASELINE" = "1" ]; then
    mv "$DOCKER/config.toml.modded" "$DOCKER/config.toml"
fi
echo "==> done"
