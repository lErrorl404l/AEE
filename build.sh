#!/usr/bin/env bash
set -euo pipefail

# Convenience wrapper around hemtt + the verification gate.
# Usage: ./build.sh [check|build|release|launch|test <profile>]
#
#   check    hemtt check -p -e (static + lint gate)
#   build    hemtt build
#   release  hemtt release  (preceded by the full gate: check + unit tests)
#   test     unit tests + docker integration test (needs an Arma 3 server;
#            path from $ARMA3_SERVER_ROOT, tests/docker/server_root, or
#            tests/docker/server — see tools/docker_test.sh)
#   launch   hemtt launch <profile>
#
# The pre-commit hook already runs check + unit tests on every commit;
# `release` re-runs them so a release is always gated, and `test` adds the
# dedicated-server integration pass.

ACTION="${1:-build}"
PROFILE="${2:-default}"

gate() {
    echo "==> gate: hemtt check -p -e"
    hemtt check -p -e
    echo "==> gate: unit tests"
    python3 tools/run_tests.py
}

case "$ACTION" in
check) hemtt check -p -e ;;
build) hemtt build ;;
release)
    gate
    hemtt release
    ;;
test)
    gate
    echo "==> docker integration test"
    tools/docker_test.sh
    ;;
launch) hemtt launch "$PROFILE" ;;
*)
    echo "Usage: $0 [check|build|release|launch|test <profile>]" >&2
    exit 1
    ;;
esac
