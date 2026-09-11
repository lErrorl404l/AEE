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

docker run --rm -v "$DOCKER/configs:/c" alpine rm -rf /c/profiles 2>/dev/null || true

clean_profiles() { docker run --rm -v "$DOCKER/configs:/c" alpine rm -rf /c/profiles 2>/dev/null || true; }
trap 'docker compose "${COMPOSE_FILES[@]}" down 2>/dev/null || true; clean_profiles' EXIT

# ── Map rotation mode ───────────────────────────────────────────────────────
# Runs the mission on several worlds and asserts the Koppen biome each
# world resolves to. Validates environment switching across biomes.
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
if [ "${1:-}" = "--maps" ]; then
    echo "==> map rotation test"
    MAPS=("Stratis:Csa" "Tanoa:Af" "Enoch:Dfb")
    FAILED=0
    for entry in "${MAPS[@]}"; do
        world="${entry%%:*}"
        expect="${entry##*:}"
        echo "==> world $world (expect biome $expect)"
        # the wrapper reads world/mission from env, not config.toml
        cat > "$DOCKER/docker-compose.$world.yml" << YAMLEOF
services:
  aee-test:
    environment:
      - ARMA3_SERVER__WORLD=$world
      - ARMA3_SERVER__MISSION=aee_test.$world
YAMLEOF
        cat > "$DOCKER/configs/server.cfg" << CFGEOF
hostname = "AEE Test";
password = "";
passwordAdmin = "";
maxPlayers = 8;
persistent = 1;
loopback = 1;
kickDuplicate = 0;
BattlEye = 0;
verifySignatures = 0;
class Missions {
    class AEETest {
        template = "aee_test.$world";
        difficulty = "custom";
    };
};
CFGEOF
        docker compose -f "$DOCKER/docker-compose.yml" -f "$DOCKER/docker-compose.$world.yml" up -d --force-recreate
        for _ in $(seq 1 36); do
            if docker compose -f "$DOCKER/docker-compose.yml" -f "$DOCKER/docker-compose.$world.yml" logs 2>/dev/null | grep -q "\[AEE-TEST\] DONE"; then break; fi
            sleep 5
        done
        docker compose -f "$DOCKER/docker-compose.yml" -f "$DOCKER/docker-compose.$world.yml" logs > "$DOCKER/run.$world.log" 2>&1
        biome=$(grep -oE "\[BIOME\] $world=[A-Za-z]+" "$DOCKER/run.$world.log" | tail -1 | cut -d= -f2)
        if [ "$biome" = "$expect" ]; then
            echo "  PASS: $world resolves to $biome (expected $expect)"
        else
            echo "  FAIL: $world biome = '${biome:-<none>}' (expected $expect)"
            FAILED=1
        fi
        docker compose -f "$DOCKER/docker-compose.yml" -f "$DOCKER/docker-compose.$world.yml" down 2>/dev/null || true
        rm -f "$DOCKER/docker-compose.$world.yml"
        rm -rf "$DOCKER/configs/profiles" 2>/dev/null || true
    done
    cat > "$DOCKER/configs/server.cfg" << CFGEOF
hostname = "AEE Test";
password = "";
passwordAdmin = "";
maxPlayers = 8;
persistent = 1;
loopback = 1;
kickDuplicate = 0;
BattlEye = 0;
verifySignatures = 0;
class Missions {
    class AEETestStratis { template = "aee_test.Stratis"; difficulty = "custom"; };
    class AEETestTanoa { template = "aee_test.Tanoa"; difficulty = "custom"; };
    class AEETestEnoch { template = "aee_test.Enoch"; difficulty = "custom"; };
};
CFGEOF
    if [ "$FAILED" -ne 0 ]; then
        echo "==> map rotation FAILED"
        exit 1
    fi
    echo "==> map rotation PASS"
    exit 0
fi

if [ ! -d "$MODS/@cba_a3" ]; then
    curl -fsSL "https://github.com/CBATeam/CBA_A3/releases/download/${CBA_VERSION}/CBA_A3_${CBA_VERSION}.zip" -o /tmp/cba.zip
    unzip -oq /tmp/cba.zip -d "$MODS"
    rm /tmp/cba.zip
    # the release zip extracts an uppercase folder; normalise for the
    # case-sensitive linux filesystem
    [ -d "$MODS/@CBA_A3" ] && mv "$MODS/@CBA_A3" "$MODS/@cba_a3"
fi

BASELINE=0
COMPOSE_FILES=(-f "$DOCKER/docker-compose.yml")
if [ "${1:-}" = "--baseline" ]; then
    BASELINE=1
    echo "==> baseline run (no AEE mod)"
    COMPOSE_FILES+=(-f "$DOCKER/docker-compose.baseline.yml")
fi

echo "==> docker compose up"
docker compose "${COMPOSE_FILES[@]}" up -d --force-recreate

echo "==> waiting for results (up to 180 s)"
for _ in $(seq 1 36); do
    if docker compose "${COMPOSE_FILES[@]}" logs 2>/dev/null | grep -q "\[AEE-TEST\] DONE"; then
        break
    fi
    sleep 5
done

echo "==> capturing log"
docker compose "${COMPOSE_FILES[@]}" logs > "$DOCKER/run.log" 2>&1

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

echo "==> done"
