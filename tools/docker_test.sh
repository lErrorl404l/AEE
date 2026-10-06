#!/bin/bash
# AEE headless docker test.
#
# Builds the mod PBOs, assembles @aee, downloads CBA if needed, runs the
# Arma 3 dedicated server (brettmayson/arma3server) with the test mission,
# captures the RPT output and verifies the phase results.
#
# Usage: tools/docker_test.sh [MODE] [options] [JOB..]
#
# Modes (default: the phase suite):
#   --baseline        run once without AEE, for comparison
#   --maps            run the mission on several worlds, assert each biome
#   --hosts           load each supported host mod and assert compat
#   --soak            long AI/wildlife soak (--soak-min N, default 20)
#   --stress          soak plus the saturation burst and agent churn
#   --parallel        run several modes at once and aggregate the verdict
#
# Isolation options:
#   --run-id ID       name this run (default: <worktree>-<pid>)
#   --run-dir DIR     run and log directory (isolated default: runs/<id>)
#   --isolate         force a per-run directory and a free port
#   --port N          force the game port (isolated default: a free port)
#   --jobs "MODE.."   the modes --parallel runs (default: "default maps").
#                     A maps job may name worlds: "maps:Tanoa maps:Enoch"
#
# Every run gets a unique compose project, so two runs never capture the same
# container.  A single run with no isolation flag keeps the historical paths
# (run.log in the docker directory) and port 2302.  --isolate, --parallel and
# --run-dir move the logs to tests/docker/runs/<id>/ and pick a free port.
#
# Environment equivalents: AEE_RUN_ID, AEE_RUN_DIR, AEE_GAME_PORT, AEE_PROFILE,
# COMPOSE_PROJECT_NAME, AEE_PORT_SLOT, AEE_SKIP_BUILD, AEE_PARALLEL_JOBS.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCKER="$ROOT/tests/docker"
MODS="$DOCKER/mods"
CBA_VERSION="v3.19.0"
ISOLATION="$ROOT/tools/docker_run_isolation.py"

# ── Argument parsing ────────────────────────────────────────────────────────
MODE="default"
SOAK_MIN=20
ISOLATE=0
RUN_ID="${AEE_RUN_ID:-}"
RUN_DIR="${AEE_RUN_DIR:-}"
GAME_PORT="${AEE_GAME_PORT:-}"
JOBS=()
while [ $# -gt 0 ]; do
    case "$1" in
    --baseline) MODE="baseline" ;;
    --maps) MODE="maps" ;;
    --hosts) MODE="hosts" ;;
    --soak) MODE="soak" ;;
    --stress) MODE="stress" ;;
    --parallel) MODE="parallel" ;;
    --isolate) ISOLATE=1 ;;
    --soak-min)
        shift
        SOAK_MIN="${1:-20}"
        ;;
    --soak-min=*) SOAK_MIN="${1#*=}" ;;
    --run-id)
        shift
        RUN_ID="${1:-}"
        ;;
    --run-id=*) RUN_ID="${1#*=}" ;;
    --run-dir)
        shift
        RUN_DIR="${1:-}"
        ;;
    --run-dir=*) RUN_DIR="${1#*=}" ;;
    --port)
        shift
        GAME_PORT="${1:-}"
        ;;
    --port=*) GAME_PORT="${1#*=}" ;;
    --jobs)
        shift
        read -r -a _j <<<"${1//,/ }"
        JOBS+=("${_j[@]}")
        ;;
    --jobs=*)
        _jstr="${1#*=}"
        read -r -a _j <<<"${_jstr//,/ }"
        JOBS+=("${_j[@]}")
        ;;
    --)
        shift
        JOBS+=("$@")
        break
        ;;
    -*)
        echo "ERROR: unknown option: $1" >&2
        exit 2
        ;;
    *) JOBS+=("$1") ;;
    esac
    shift
done
# A bare --parallel may carry its job list as trailing words or the env.
if [ "$MODE" = "parallel" ] && [ "${#JOBS[@]}" -eq 0 ]; then
    read -r -a JOBS <<<"${AEE_PARALLEL_JOBS:-default maps}"
fi

# ── Per-run isolation ───────────────────────────────────────────────────────
# Derived once, exported, and shared by every compose call: a unique project
# name, profile, run directory and game-port block.  See
# tools/docker_run_isolation.py for the derivation.
_isolate="$ISOLATE"
if [ "$MODE" = "parallel" ] || [ -n "$RUN_DIR" ] || [ -n "$GAME_PORT" ]; then
    _isolate=1
fi
_iso_args=(--docker "$DOCKER" --root-name "$(basename "$ROOT")" --pid "$$"
--slot "${AEE_PORT_SLOT:-10}")
if [ -n "$RUN_ID" ]; then _iso_args+=(--run-id "$RUN_ID"); fi
if [ "$_isolate" = 1 ]; then
    if [ -n "$RUN_DIR" ]; then _iso_args+=(--run-dir "$RUN_DIR"); fi
    if [ -n "$GAME_PORT" ]; then _iso_args+=(--port "$GAME_PORT"); fi
else
    _iso_args+=(--run-dir "$DOCKER" --port "${GAME_PORT:-2302}" --profile aeetest)
fi
eval "$(python3 "$ISOLATION" resolve "${_iso_args[@]}")"
AEE_CONFIGS_DIR="$AEE_RUN_DIR/configs"
export COMPOSE_PROJECT_NAME AEE_RUN_ID AEE_PROFILE AEE_GAME_PORT
export AEE_RUN_DIR AEE_PORT_SLOT AEE_CONFIGS_DIR
RUN_ID="$AEE_RUN_ID"
RUN_DIR="$AEE_RUN_DIR"
CONFIGS="$AEE_CONFIGS_DIR"
mkdir -p "$CONFIGS"
# Seed the committed server.cfg so a mode that does not rewrite it still gets
# one; a mode that does rewrite it writes into this run's directory only.
if [ ! -f "$CONFIGS/server.cfg" ]; then
    cp "$DOCKER/configs/server.cfg" "$CONFIGS/server.cfg" 2>/dev/null || true
fi

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

# The container runs as root, so a profiles dir it writes through the host
# bind mount is root-owned and blocks the host-side hemtt build walk.  The
# alpine volume removes it with root rights even when a plain rm -rf fails.
clean_profiles() { docker run --rm -v "$CONFIGS:/c" alpine rm -rf /c/profiles 2>/dev/null || true; }
# Remove per-host/world compose overlay files left by FAIL paths.  The base
# compose and the baseline overlay are kept.
clean_overlays() { find "$RUN_DIR" -maxdepth 1 -name 'docker-compose.*.yml' ! -name 'docker-compose.baseline.yml' -delete 2>/dev/null || true; }
COMPOSE_FILES=()
trap 'if [ "${#COMPOSE_FILES[@]}" -gt 0 ]; then docker compose "${COMPOSE_FILES[@]}" down 2>/dev/null || true; fi; clean_profiles; clean_overlays' EXIT

# Download CBA once, after the build.  Concurrent runs share one copy.
ensure_cba() {
    if [ -d "$MODS/@cba_a3" ]; then return 0; fi
    echo "==> ensure @cba_a3 (download)"
    curl -fsSL "https://github.com/CBATeam/CBA_A3/releases/download/${CBA_VERSION}/CBA_A3_${CBA_VERSION}.zip" -o /tmp/cba.zip
    unzip -oq /tmp/cba.zip -d "$MODS"
    rm /tmp/cba.zip
    # the release zip extracts an uppercase folder; normalise for the
    # case-sensitive linux filesystem
    [ -d "$MODS/@CBA_A3" ] && mv "$MODS/@CBA_A3" "$MODS/@cba_a3"
    return 0
}

# ── Concurrent runs ─────────────────────────────────────────────────────────
# Allocate a free game-port block for a run id, skipping blocks already handed
# to a sibling in this batch.
_alloc_port() {
    if [ -n "$2" ]; then
        python3 "$ISOLATION" port --run-id "$1" --slot "$AEE_PORT_SLOT" --reserve "$2"
    else
        python3 "$ISOLATION" port --run-id "$1" --slot "$AEE_PORT_SLOT"
    fi
}

# Run several suite modes at once, each in its own isolated container and run
# directory, then aggregate one verdict.  The parent builds once; each child
# skips the build and reuses the assembled @aee.
run_parallel() {
    local base="$RUN_DIR/parallel"
    local -a jobs=("${JOBS[@]}")
    local -a names=() pids=()
    local reserved="" idx=0 rc=0
    mkdir -p "$base"
    for job in "${jobs[@]}"; do
        local name="${job%%:*}"
        local arg=""
        if [ "$job" != "$name" ]; then arg="${job#*:}"; fi
        local flag=""
        local maponly=""
        case "$name" in
        default) flag="" ;;
        baseline) flag="--baseline" ;;
        maps)
            flag="--maps"
            maponly="$arg"
            ;;
        hosts) flag="--hosts" ;;
        soak) flag="--soak" ;;
        stress) flag="--stress" ;;
        *)
            echo "ERROR: unknown parallel job: $job" >&2
            return 2
            ;;
        esac
        local jid="$RUN_ID-$name-$idx"
        local jdir="$base/$name-$idx"
        local port
        port="$(_alloc_port "$jid" "$reserved")"
        reserved="${reserved:+$reserved,}$port"
        mkdir -p "$jdir/configs"
        cp "$DOCKER/configs/server.cfg" "$jdir/configs/server.cfg" 2>/dev/null || true
        echo "==> parallel job $idx: $name (project aee-$jid, port $port)"
        (
            export AEE_SKIP_BUILD=1
            export AEE_RUN_ID="$jid"
            export AEE_RUN_DIR="$jdir"
            export AEE_CONFIGS_DIR="$jdir/configs"
            export AEE_GAME_PORT="$port"
            export AEE_MAPS_ONLY="$maponly"
            exec "$0" $flag
        ) >"$jdir/console.log" 2>&1 &
        names+=("$jid")
        pids+=("$!")
        idx=$((idx + 1))
    done
    local i
    for i in "${!pids[@]}"; do
        if wait "${pids[$i]}"; then
            echo "  PASS: ${names[$i]}"
        else
            echo "  FAIL: ${names[$i]} (console: $base/*/console.log)"
            rc=1
        fi
    done
    if [ "$rc" -eq 0 ]; then
        echo "==> parallel PASS (${#jobs[@]} jobs)"
    else
        echo "==> parallel FAIL"
    fi
    return "$rc"
}

# A previous container run leaves root-owned profile state on the host mount
# (the server runs as root).  That dir blocks the hemtt build walk, so it is
# cleaned before the build, not only in the EXIT trap.
if [ "${AEE_SKIP_BUILD:-0}" != "1" ]; then
    clean_profiles
    echo "==> hemtt build (clean — removes the incremental cache so a stale"
    echo "    PBO can never slip into the test or a release)"
    rm -rf "$ROOT/.hemttout/build" "$ROOT/.hemttout/bincache" "$ROOT/.hemttout/last_build.hsb"
    (cd "$ROOT" && hemtt build >/dev/null)

    echo "==> assemble @aee"
    rm -rf "$MODS/@aee"
    mkdir -p "$MODS/@aee/addons"
    # The WHOLE build root, not three named files. Naming them dropped the logo,
    # LICENSE and README, and a dedicated server never renders the mod list so it
    # never asked for the logo and the harness could not report the omission.
    mkdir -p "$MODS/@aee"
    cp -a "$ROOT"/.hemttout/build/. "$MODS/@aee/"
else
    echo "==> reusing the built @aee (AEE_SKIP_BUILD=1)"
fi

# CBA is shared by every mode and every concurrent run, so fetch it once.
ensure_cba

# ── Parallel mode ───────────────────────────────────────────────────────────
# Several suite modes run at once, each isolated, then aggregate one verdict.
if [ "$MODE" = "parallel" ]; then
    if run_parallel; then exit 0; else exit 1; fi
fi

# ── Host-mod compatibility mode ────────────────────────────────────────────
# Loads each supported host mod (downloaded by the operator into
# tests/docker/mods/@<folder>) with AEE and asserts the compat integration.
if [ "$MODE" = "hosts" ]; then
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
        # Create lowercase symlink aliases idempotently.  The `|| true`
        # guards the last ln -s under set -euo pipefail: when every
        # symlink already exists the final test returns 1, which would
        # abort the whole host loop.
        (cd "$MODS/@acm/addons" && for f in ACM_*.pbo; do
            low=$(echo "$f" | tr 'A-Z' 'a-z')
            [ "$f" != "$low" ] && [ ! -e "$low" ] && ln -s "$f" "$low"
        done) || true
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
        cat >"$CONFIGS/server.cfg" <<CFGEOF
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
        cat >"$RUN_DIR/docker-compose.$host.yml" <<YAMLEOF
services:
  aee-test:
    environment:
      - ARMA3_SERVER__PARAMS=-autoInit -noBattlEye -mod=mods/@aee;mods/@cba_a3;$moddir
      - ARMA3_SERVER__MISSION=compat_host.Stratis
YAMLEOF
        docker compose -f "$DOCKER/docker-compose.yml" -f "$RUN_DIR/docker-compose.$host.yml" up -d --force-recreate
        for _ in $(seq 1 60); do
            if docker compose -f "$DOCKER/docker-compose.yml" -f "$RUN_DIR/docker-compose.$host.yml" logs 2>/dev/null | grep -q "\[AEE-TEST\] DONE"; then break; fi
            sleep 5
        done
        docker compose -f "$DOCKER/docker-compose.yml" -f "$RUN_DIR/docker-compose.$host.yml" logs >"$RUN_DIR/run.$host.log" 2>&1
        case "$host" in
        ace) hostname="ACE3" ;;
        acre2) hostname="ACRE2" ;;
        tfar) hostname="TFAR" ;;
        kat) hostname="KAT" ;;
        acm) hostname="ACM" ;;
        esac
        if grep -q "\[HOST\] \[FAIL\]" "$RUN_DIR/run.$host.log" 2>/dev/null; then
            echo "  FAIL: $host - see tests/docker/run.$host.log"
            FAILED=1
        elif grep -q "\[HOST\] \[PASS\] $hostname" "$RUN_DIR/run.$host.log" 2>/dev/null; then
            echo "  PASS: $host compat integration"
        else
            echo "  FAIL: $host - no result (see tests/docker/run.$host.log)"
            FAILED=1
        fi
        docker compose -f "$DOCKER/docker-compose.yml" -f "$RUN_DIR/docker-compose.$host.yml" down 2>/dev/null || true
        rm -f "$RUN_DIR/docker-compose.$host.yml"
        clean_profiles
    done
    cat >"$CONFIGS/server.cfg" <<CFGEOF
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

if [ "$MODE" = "maps" ]; then
    echo "==> map rotation test"
    # Workshop content root. Override AEE_WORKSHOP_DIR for another library.
    WORKSHOP="${AEE_WORKSHOP_DIR:-/ext/SteamLibrary/steamapps/workshop/content/107410}"
    VALIDATOR="$ROOT/tools/validation/validate_biome_plausible.py"

    # world|latitude|required-workshop-ids
    #   The latitude is a FACT read from the map's own CfgWorlds latitude
    #   (BIS stores it sign-inverted; the Koppen band is symmetric, so the
    #   MAGNITUDE is the value under test).  The rotation never knows the
    #   expected biome: it asks validate_biome_plausible.py whether the
    #   resolved biome is in the latitude band (ADR-002, no-hardcoding).
    #   The world is the CfgWorlds class name, not the mod name.
    MAPS=(
        "Stratis|35.097|"
        "Tanoa|17.698|"
        "Enoch|54|"
        "NorthTakistan|17.698|2829330653,583496184"
        "kunduz_valley|36.72|3078351739,583496184"
        "Mountains_ACR|34|583544987,583496184"
        "oski_corran|56.702|2214384530"
    )

    # Dependency check BEFORE the rotation.  A missing Workshop mod skips
    # its map and the run still exits 0: an absent local mod is not a
    # regression of the biome system.
    RUNNABLE=()
    for entry in "${MAPS[@]}"; do
        IFS='|' read -r world _lat mods <<<"$entry"
        missing=""
        if [ -n "$mods" ]; then
            IFS=',' read -ra ids <<<"$mods"
            for id in "${ids[@]}"; do
                if [ ! -d "$WORKSHOP/$id" ]; then
                    missing="$missing $id"
                elif [ ! -d "$WORKSHOP/$id/addons" ] && [ ! -d "$WORKSHOP/$id/Addons" ]; then
                    missing="$missing $id(no addons folder)"
                fi
            done
        fi
        if [ -n "$missing" ]; then
            echo "  MISSING: $world needs workshop mod(s)$missing in $WORKSHOP; skipping"
        else
            RUNNABLE+=("$entry")
        fi
    done
    echo "==> $((${#RUNNABLE[@]})) of $((${#MAPS[@]})) maps runnable"
    # A parallel job may restrict the rotation to named worlds.  Each selected
    # world then runs as its own isolated job, which is how the rotation is
    # split across concurrent containers.
    if [ -n "${AEE_MAPS_ONLY:-}" ]; then
        IFS=' ' read -ra _only <<<"${AEE_MAPS_ONLY//,/ }"
        _keep=()
        for entry in "${RUNNABLE[@]}"; do
            for _w in "${_only[@]}"; do
                if [ "${entry%%|*}" = "$_w" ]; then _keep+=("$entry"); fi
            done
        done
        RUNNABLE=("${_keep[@]}")
        echo "==> maps filter: $AEE_MAPS_ONLY (${#RUNNABLE[@]} selected)"
        if [ "${#RUNNABLE[@]}" -eq 0 ]; then
            echo "  FAIL: the maps filter selected no runnable world"
            echo "==> map rotation FAILED"
            exit 1
        fi
    fi

    FAILED=0
    for entry in "${RUNNABLE[@]}"; do
        IFS='|' read -r world lat mods <<<"$entry"
        echo "==> world $world (latitude $lat)"
        # Mount each required Workshop item inside the mods bind mount, then
        # add it to the load order.  The mount must be writable: Arma's mod
        # scanner resolves a Docker :ro bind mount as an empty mod, so a
        # read-only mount silently drops the map's dependencies.  The engine
        # does not write to the mount (verified: no file is modified).
        # Some Workshop mods ship an uppercase Addons folder; Arma's Linux
        # scanner needs lowercase 'addons', so the real folder is mounted at
        # the lowercase name.  The entrypoint symlinks every @* folder into
        # the game dir.
        modparam="mods/@aee;mods/@cba_a3"
        overlay_volumes=""
        if [ -n "$mods" ]; then
            IFS=',' read -ra ids <<<"$mods"
            for id in "${ids[@]}"; do
                modparam="$modparam;mods/@$id"
                addons_src="$WORKSHOP/$id/addons"
                [ -d "$addons_src" ] || addons_src="$WORKSHOP/$id/Addons"
                overlay_volumes="$overlay_volumes      - $addons_src:/arma3/server/mods/@$id/addons
"
            done
        fi
        # the wrapper reads world/mission/params from env, not config.toml
        {
            echo "services:"
            echo "  aee-test:"
            echo "    environment:"
            echo "      - ARMA3_SERVER__WORLD=$world"
            echo "      - ARMA3_SERVER__MISSION=aee_test.$world"
            echo "      - ARMA3_SERVER__PARAMS=-autoInit -noBattlEye -mod=$modparam"
            if [ -n "$overlay_volumes" ]; then
                echo "    volumes:"
                printf '%s' "$overlay_volumes"
            fi
        } >"$RUN_DIR/docker-compose.$world.yml"
        cat >"$CONFIGS/server.cfg" <<CFGEOF
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
        clean_profiles
        docker compose -f "$DOCKER/docker-compose.yml" -f "$RUN_DIR/docker-compose.$world.yml" up -d --force-recreate
        for _ in $(seq 1 60); do
            if docker compose -f "$DOCKER/docker-compose.yml" -f "$RUN_DIR/docker-compose.$world.yml" logs 2>/dev/null | grep -q "\[AEE-TEST\] DONE"; then break; fi
            sleep 5
        done
        docker compose -f "$DOCKER/docker-compose.yml" -f "$RUN_DIR/docker-compose.$world.yml" logs >"$RUN_DIR/run.$world.log" 2>&1
        biome=$({ grep -oE "\[BIOME\] $world=[A-Za-z]+" "$RUN_DIR/run.$world.log" || true; } | tail -1 | cut -d= -f2)
        if [ -z "$biome" ]; then
            echo "  FAIL: $world - no [BIOME] line (see tests/docker/run.$world.log)"
            FAILED=1
        elif python3 "$VALIDATOR" "$lat" "$biome"; then
            echo "  PASS: $world lat=$lat -> $biome (plausible)"
        else
            echo "  FAIL: $world lat=$lat -> $biome rejected by the band gate"
            FAILED=1
        fi
        docker compose -f "$DOCKER/docker-compose.yml" -f "$RUN_DIR/docker-compose.$world.yml" down 2>/dev/null || true
        rm -f "$RUN_DIR/docker-compose.$world.yml"
        clean_profiles
    done
    cat >"$CONFIGS/server.cfg" <<CFGEOF
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

# ── Soak and stress modes ───────────────────────────────────────────────────
# A long run of the soak mission drives the pure AI and wildlife kernels and
# samples them.  --stress adds the saturation burst and the bounded agent
# churn.  Both modes need the built PBO and CBA, so they sit after the build.
SOAK_MODE=""
case "$MODE" in
soak) SOAK_MODE=soak ;;
stress) SOAK_MODE=stress ;;
esac
if [ -n "$SOAK_MODE" ]; then
    SOAK_STRESS=false
    if [ "$SOAK_MODE" = "stress" ]; then
        SOAK_STRESS=true
    fi
    SOAK_OVERLAY="$RUN_DIR/docker-compose.soak.yml"
    SOAK_CFG_BAK="$CONFIGS/server.cfg.soakbak"
    SOAK_CFG_FILE="$RUN_DIR/soak_config.sqf"
    COMPOSE_FILES=(-f "$DOCKER/docker-compose.yml" -f "$SOAK_OVERLAY")

    echo "==> soak mode=$SOAK_MODE minutes=$SOAK_MIN stress=$SOAK_STRESS"

    # Keep the committed server.cfg so the default run is unchanged after this
    # mode.  The soak mission is the only entry in the Missions class, because
    # the wrapper launches with -autoInit and no -mission and so picks the
    # first entry, exactly as the map rotation mode relies on.
    cp "$CONFIGS/server.cfg" "$SOAK_CFG_BAK"

    {
        echo "services:"
        echo "  aee-test:"
        echo "    environment:"
        echo "      - ARMA3_SERVER__WORLD=Stratis"
        echo "      - ARMA3_SERVER__MISSION=aee_soak.Stratis"
        echo "      - ARMA3_SERVER__PARAMS=-autoInit -noBattlEye -mod=mods/@aee;mods/@cba_a3"
        # The soak config is per run, so two concurrent soaks never share it.
        echo "    volumes:"
        echo "      - $SOAK_CFG_FILE:/arma3/server/mpmissions/aee_soak.Stratis/soak_config.sqf"
    } >"$SOAK_OVERLAY"

    cat >"$CONFIGS/server.cfg" <<CFGEOF
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
    class AEESoak { template = "aee_soak.Stratis"; difficulty = "custom"; };
};
CFGEOF

    cat >"$SOAK_CFG_FILE" <<CFGEOF
AEE_SOAK_MINUTES = $SOAK_MIN;
AEE_SOAK_STRESS = $SOAK_STRESS;
CFGEOF

    clean_profiles
    docker compose "${COMPOSE_FILES[@]}" up -d --force-recreate

    SOAK_WAIT=$((SOAK_MIN * 60 + 180))
    echo "==> waiting for the soak (up to ${SOAK_WAIT} s)"
    for _ in $(seq 1 $((SOAK_MIN * 12 + 36))); do
        if docker compose "${COMPOSE_FILES[@]}" logs 2>/dev/null | grep -q "\[AEE-SOAK\] DONE"; then
            break
        fi
        sleep 5
    done

    echo "==> capturing soak log"
    docker compose "${COMPOSE_FILES[@]}" logs >"$RUN_DIR/run.soak.log" 2>&1

    echo "==> verifying soak"
    if ! python3 "$DOCKER/verify_soak.py" "$RUN_DIR/run.soak.log"; then
        echo "soak harness failed; full log at tests/docker/run.soak.log"
        docker compose "${COMPOSE_FILES[@]}" down 2>/dev/null || true
        cp "$SOAK_CFG_BAK" "$CONFIGS/server.cfg" 2>/dev/null || true
        rm -f "$SOAK_CFG_BAK" "$SOAK_OVERLAY" "$SOAK_CFG_FILE"
        clean_profiles
        exit 1
    fi

    docker compose "${COMPOSE_FILES[@]}" down 2>/dev/null || true
    cp "$SOAK_CFG_BAK" "$CONFIGS/server.cfg" 2>/dev/null || true
    rm -f "$SOAK_CFG_BAK" "$SOAK_OVERLAY" "$SOAK_CFG_FILE"
    clean_profiles
    echo "==> soak done"
    exit 0
fi

BASELINE=0
COMPOSE_FILES=(-f "$DOCKER/docker-compose.yml")
if [ "$MODE" = "baseline" ]; then
    BASELINE=1
    echo "==> baseline run (no AEE mod)"
    COMPOSE_FILES+=(-f "$DOCKER/docker-compose.baseline.yml")
fi

echo "==> docker compose up"
docker compose "${COMPOSE_FILES[@]}" up -d --force-recreate

echo "==> waiting for results (up to 300 s)"
for _ in $(seq 1 60); do
    if docker compose "${COMPOSE_FILES[@]}" logs 2>/dev/null | grep -q "\[AEE-TEST\] DONE"; then
        break
    fi
    sleep 5
done

echo "==> capturing log"
docker compose "${COMPOSE_FILES[@]}" logs >"$RUN_DIR/run.log" 2>&1

if [ "$BASELINE" = "1" ]; then
    echo "==> baseline captured to $RUN_DIR/run.log (no verify gate)"
    echo "    phases in the baseline are expected to FAIL (no AEE loaded)"
else
    echo "==> verifying"
    python3 "$DOCKER/verify.py" "$RUN_DIR/run.log" ||
        {
            echo "harness failed; full log at $RUN_DIR/run.log"
            exit 1
        }
fi

echo "==> teardown"
docker compose -f "$DOCKER/docker-compose.yml" down 2>/dev/null || true

echo "==> done"
