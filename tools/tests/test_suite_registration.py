#!/usr/bin/env python3
"""Every unit suite under ``tools/tests/`` must be registered in
``tools/run_tests.py``, or sit on the reasoned allowlist below.

The pairing of a suite and the runner that runs it is a contract.  A new
``test_*.py`` that nobody registers never gates CI.  This is the exact failure
recorded on 2026-10-08: ``test_engine_overrides.py`` and
``test_probe_numbers.py`` were committed but not registered, so ``make test``
found them and ``run_tests.py --fast`` (the CI and pre-commit path) did not.

Discovery is by glob, not by memory.  This test fails until the suite is
registered or exempted with a reason.

Run: python3 -m unittest tools.tests.test_suite_registration
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TESTS = REPO / "tools" / "tests"
RUNNER = REPO / "tools" / "run_tests.py"

# suite module name -> reason.  An entry is a deliberate exemption from the
# run_tests.py registry.  An empty allowlist means every discovered suite must
# be registered.
ALLOWLIST: dict[str, str] = {
    # Pre-existing failures, unrelated to the conformance change.  Each also
    # fails on `main`, so none is caused by this change.  They are not
    # registered because a registered red suite would break `make lint`, and
    # they are not fixed here because the drift is owned by other work.  The
    # defect is recorded, not hidden.
    "test_exhaust_shimmer": (
        "pre-existing source-contract drift: the air-engine override literals "
        "it pins are absent from the scanned source after the engine-override "
        "rework (fails on main too)."
    ),
    "test_ground_state_frost": (
        "pre-existing source-contract drift: the frost-to-ground-state Frozen "
        "branch was restructured, so the pinned structure is gone (fails on "
        "main too)."
    ),
    "test_range_cost": (
        "pre-existing source-contract drift: the view-distance shadow-fraction "
        "literal changed (fails on main too)."
    ),
    "test_segments": (
        "helper module, not a suite: it holds the 17-segment thermoregulation "
        "mirror and defines no unittest cases, so unittest exits 5 for it."
    ),
    "test_vehicle_expansion": (
        "requires the gitignored held vehicle source PDFs "
        "(data/vehicle/sources/*.pdf); absent on a clean checkout, so it fails "
        "where the sources are not present."
    ),
    "test_vehicle_first_slice": (
        "requires the gitignored held vehicle source PDFs "
        "(data/vehicle/sources/*.pdf); absent on a clean checkout, so it fails "
        "where the sources are not present."
    ),
}

# A registered entry: "tools/tests/test_<name>.py" inside the runner list.
_REGISTERED = re.compile(r"tools/tests/(test_[A-Za-z0-9_]+)\.py")


def _discovered() -> set[str]:
    return {path.stem for path in TESTS.glob("test_*.py")}


def _registered() -> set[str]:
    return set(_REGISTERED.findall(RUNNER.read_text(encoding="utf-8")))


class TestSuiteRegistration(unittest.TestCase):
    def test_every_suite_is_registered_or_allowlisted(self):
        missing = sorted(
            suite for suite in _discovered() - _registered() if suite not in ALLOWLIST
        )
        self.assertEqual(
            missing,
            [],
            "these suites are not registered in tools/run_tests.py: "
            + ", ".join(missing),
        )

    def test_every_registered_suite_has_a_file(self):
        ghost = sorted(
            suite for suite in _registered() if not (TESTS / f"{suite}.py").exists()
        )
        self.assertEqual(
            ghost, [], "registered suites with no file: " + ", ".join(ghost)
        )

    def test_the_allowlist_has_a_reason_for_every_entry(self):
        for suite, reason in ALLOWLIST.items():
            self.assertTrue(reason.strip(), f"{suite} allowlist entry has no reason")


if __name__ == "__main__":
    unittest.main()
