#!/usr/bin/env bash
set -euo pipefail

# Convenience wrapper around hemtt.
# Usage: ./build.sh [check|build|release|launch <profile>]

ACTION="${1:-build}"
PROFILE="${2:-default}"

case "$ACTION" in
check) hemtt check -p -e ;;
build) hemtt build ;;
release) hemtt release ;;
launch) hemtt launch "$PROFILE" ;;
*)
    echo "Usage: $0 [check|build|release|launch <profile>]" >&2
    exit 1
    ;;
esac
