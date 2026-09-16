#!/usr/bin/env python3
"""AEE test runner — runs every unit suite and the physics validation harness.

Usage:
    python3 tools/run_tests.py            # full sweep
    python3 tools/run_tests.py --fast     # unit suites only (no validation harness)
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd, cwd=ROOT):
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode


def main():
    fast = "--fast" in sys.argv
    suites = [
        "tools/tests/test_physics.py",
        "tools/tests/test_mobility.py",
        "tools/tests/test_physiology.py",
        "tools/tests/test_radio.py",
        "tools/tests/test_environmental.py",
        "tools/tests/test_atmos.py",
        "tools/tests/test_maritime.py",
        "tools/tests/test_thermal_optics.py",
        "tools/tests/test_astronomical.py",
        "tools/tests/test_biome.py",
        "tools/tests/test_propellant_temp.py",
        "tools/tests/test_sleep_model.py",
        "tools/tests/test_shooter_stability.py",
    ]
    # Only run suites that exist (module suites are added incrementally).
    existing = [s for s in suites if os.path.exists(os.path.join(ROOT, s))]
    if not existing:
        print("No test suites found under tools/tests/")
        return 1

    # Prefer the venv when present so the optional-library checks run.
    python = os.path.join(ROOT, "tools/validation/.venv/bin/python")
    if not os.path.exists(python):
        python = "python3"

    failed = 0
    for suite in existing:
        failed += run(f"{python} -m unittest {suite} -v")
    if not fast:
        print("\n--- Physics validation harness ---")
        failed += run(
            f"{python} {os.path.join(ROOT, 'tools/validation/validate_physics.py')}"
        )

    if failed:
        print("\nFAILED: one or more test suites exited non-zero.")
        return 1
    print("\nALL TESTS PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
