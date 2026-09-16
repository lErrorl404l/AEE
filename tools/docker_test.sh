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

# The Arma 3 server installation is provided by the tester, not bundled.
# Resolution order (no machine-specific path is committed):
#   1. $ARMA3_SERVER_ROOT if set (explicit override)
#   2. tests/docker/server_root if present (a gitignored one-line local
#      override, so each machine points at its own server without editing
#      this script)
#   3. tests/docker/server (bundled/bootstrap default)
if [ -z "${ARMA3_SERVER_ROOT:-}" ] && [ -f "$DOCKER/server_root" ]; then
    ARMA3_SERVER_ROOT="$(head -n1 "$DOCKER/server_root" | tr -d '[:space:]')"
fi
export ARMA3_SERVER_ROOT="${ARMA3_SERVER_ROOT:-$DOCKER/server}"
if [ ! -x "$ARMA3_SERVER_ROOT/arma3server_x64" ]; then
    echo "ERROR: no Arma 3 server at ARMA3_SERVER_ROOT=$ARMA3_SERVER_ROOT"
    echo "  Install the Arma 3 dedicated server (steamcmd app 233780) there,"
    echo "  set ARMA3_SERVER_ROOT, or write the path into"
    echo "  tests/docker/server_root (gitignored)."
    exit 1
fi
echo "==> server root: $ARMA3_SERVER_ROOT"

docker run --rm -v "$DOCKER/configs:/c" alpine rm -rf /c/profiles 2>/dev/null || true

clean_profiles() { docker run --rm -v "$DOCKER/configs:/c" alpine rm -rf /c/profiles 2>/dev/null || true; }
# Remove per-host/world compose overlay files left by FAIL paths
clean_overlays() { rm -f "$DOCKER"/docker-compose.{ace,acre2,tfar,kat,acm,Stratis,Tanoa,Enoch}.yml 2>/dev/null || true; }
trap 'docker compose "${COMPOSE_FILES[@]}" down 2>/dev/null || true; clean_profiles; clean_overlays' EXIT

# ── Map rotation mode ───────────────────────────────────────────────────────
# Runs the mission on several worlds and asserts the Koppen biome each
# world resolves to. Validates environment switching across biomes.
echo "==> server root: $ARMA3_SERVER_ROOT"
# A previous container run leaves root-owned profile state on the host
# mount (the server runs as root).  That dir blocks the hemtt build walk,
# so clean it BEFORE the build, not just in the EXIT trap.
clean_profiles
echo "==> hemtt build (clean — removes the incremental cache so a stale"
echo "    PBO can never slip into the test or a release)"
rm -rf "$ROOT/.hemttout/build" "$ROOT/.hemttout/bincache" "$ROOT/.hemttout/last_build.hsb"
(cd "$ROOT" && hemtt build >/dev/null)

echo "==> assemble @aee"
rm -rf "$MODS/@aee"
mkdir -p "$MODS/@aee/addons"
cp "$ROOT"/.hemttout/build/addons/*.pbo "$MODS/@aee/addons/"
cp "$ROOT"/.hemttout/build/mod.cpp "$MODS/@aee/mod.cpp"
cp "$ROOT"/.hemttout/build/meta.cpp "$MODS/@aee/meta.cpp"

echo "==> ensure @cba_a3"
# ── Host-mod compatibility mode ────────────────────────────────────────────
# Loads each supported host mod (downloaded by the operator into
# tests/docker/mods/@<folder>) with AEE and asserts the compat integration.
if [ "${1:-}" = "--hosts" ]; then
    echo "==> host compatibility test"
    declare -A HOSTS=(
        [ace]="mods/@ace"
        [acre2]="mods/@acre2"
        [tfar]="mods/@tfar"
        [kat]="mods/@kat_adv_medical"
        [acm]="mods/@acm"
    )
    FAILED=0
    MISSING=0
    # ACM ships uppercase PBO filenames. The Arma Linux server canonicalises
    # them to lowercase internally, then cannot open the uppercase file on a
    # case-sensitive filesystem. Create lowercase symlink aliases so the host
    # test can load ACM on Linux.
    if [ -d "$MODS/@acm/addons" ]; then
        (cd "$MODS/@acm/addons" && for f in ACM_*.pbo; do
            low=$(echo "$f" | tr 'A-Z' 'a-z')
            [ "$f" != "$low" ] && [ ! -e "$low" ] && ln -s "$f" "$low"
        done)
    fi
    for host in ace acre2 tfar kat acm; do
        moddir="${HOSTS[$host]}"
        if [ ! -d "$MODS/@${moddir#mods/@}" ]; then
            echo "  MISSING: $host mod not present at tests/docker/mods/@${moddir#mods/@}"
            MISSING=1
            continue
        fi
        echo "==> host $host"
        # the server loads the FIRST template in the Missions class, so
        # server.cfg must point at the compat mission (same as --maps)
        cat >"$DOCKER/configs/server.cfg" <<CFGEOF
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
        template = "compat_host.Stratis";
        difficulty = "custom";
    };
};
CFGEOF
        cat >"$DOCKER/docker-compose.$host.yml" <<YAMLEOF
services:
  aee-test:
    environment:
      - ARMA3_SERVER__PARAMS=-autoInit -noBattlEye -mod=mods/@aee;mods/@cba_a3;$moddir
      - ARMA3_SERVER__MISSION=compat_host.Stratis
YAMLEOF
        docker compose -f "$DOCKER/docker-compose.yml" -f "$DOCKER/docker-compose.$host.yml" up -d --force-recreate
        for _ in $(seq 1 36); do
            if docker compose -f "$DOCKER/docker-compose.yml" -f "$DOCKER/docker-compose.$host.yml" logs 2>/dev/null | grep -q "\[AEE-TEST\] DONE"; then break; fi
            sleep 5
        done
        docker compose -f "$DOCKER/docker-compose.yml" -f "$DOCKER/docker-compose.$host.yml" logs >"$DOCKER/run.$host.log" 2>&1
        case "$host" in
        ace) hostname="ACE3" ;;
        acre2) hostname="ACRE2" ;;
        tfar) hostname="TFAR" ;;
        kat) hostname="KAT" ;;
        acm) hostname="ACM" ;;
        esac
        if grep -q "\[HOST\] \[PASS\] $hostname" "$DOCKER/run.$host.log" 2>/dev/null; then
            echo "  PASS: $host compat integration"
        elif grep -q "\[HOST\] \[FAIL\]" "$DOCKER/run.$host.log"; then
            echo "  FAIL: $host - see tests/docker/run.$host.log"
            FAILED=1
        else
            echo "  FAIL: $host - no result (see tests/docker/run.$host.log)"
            FAILED=1
        fi
        docker compose -f "$DOCKER/docker-compose.yml" -f "$DOCKER/docker-compose.$host.yml" down 2>/dev/null || true
        rm -f "$DOCKER/docker-compose.$host.yml"
        rm -rf "$DOCKER/configs/profiles" 2>/dev/null || true
    done
    cat >"$DOCKER/configs/server.cfg" <<CFGEOF
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
    if [ "$MISSING" -ne 0 ]; then
        echo "==> some host mods are missing. Download from Steam Workshop and extract"
        echo "    into tests/docker/mods/@<folder>: @ace @acre2 @tfar @kat_adv_medical @acm"
    fi
    if [ "$FAILED" -ne 0 ]; then
        echo "==> host compat FAILED"
        exit 1
    fi
    echo "==> host compat PASS"
    exit 0
fi

if [ "${1:-}" = "--maps" ]; then
    echo "==> map rotation test"
    MAPS=("Stratis:Csa" "Tanoa:Af" "Enoch:Dfb")
    FAILED=0
    for entry in "${MAPS[@]}"; do
        world="${entry%%:*}"
        expect="${entry##*:}"
        echo "==> world $world (expect biome $expect)"
        # the wrapper reads world/mission from env, not config.toml
        cat >"$DOCKER/docker-compose.$world.yml" <<YAMLEOF
services:
  aee-test:
    environment:
      - ARMA3_SERVER__WORLD=$world
      - ARMA3_SERVER__MISSION=aee_test.$world
YAMLEOF
        cat >"$DOCKER/configs/server.cfg" <<CFGEOF
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
        docker compose -f "$DOCKER/docker-compose.yml" -f "$DOCKER/docker-compose.$world.yml" logs >"$DOCKER/run.$world.log" 2>&1
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
    cat >"$DOCKER/configs/server.cfg" <<CFGEOF
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
docker compose "${COMPOSE_FILES[@]}" logs >"$DOCKER/run.log" 2>&1

if [ "$BASELINE" = "1" ]; then
    echo "==> baseline captured to tests/docker/run.log (no verify gate)"
    echo "    phases in the baseline are expected to FAIL (no AEE loaded)"
else
    echo "==> verifying"
    python3 "$DOCKER/verify.py" "$DOCKER/run.log" ||
        {
            echo "harness failed; full log at tests/docker/run.log"
            exit 1
        }
fi

echo "==> teardown"
docker compose -f "$DOCKER/docker-compose.yml" down 2>/dev/null || true

echo "==> done"
