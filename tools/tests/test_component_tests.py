#!/usr/bin/env python3
"""The AEE-native in-engine component test layer.

Pins the runner contract (``aee_diagnostics_fnc_test``), the five per-surface
``test.sqf`` files and their headless-safety.

The runner mirrors CBA_fnc_test with AEE's mount root: it execVM's
``\\z\\aee\\addons\\<component>\\test.sqf`` and returns the failure count the
file published to ``aee_test_failures_<component>`` (0 on success, -1 when the
file is absent).  Each test file asserts the live merged config and pure
kernels only, so a dedicated server runs it with no interface and no camera.

Run: python3 -m unittest tools.tests.test_component_tests
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"
RUNNER = ADDONS / "diagnostics" / "functions" / "fnc_test.sqf"
PREP = ADDONS / "diagnostics" / "XEH_PREP.hpp"
POST_INIT = ADDONS / "diagnostics" / "XEH_postInit.sqf"

COMPONENTS = ("cartography", "symbology", "thermal_display", "nightvision", "lighting")

# A test.sqf must run on a dedicated server, so it must not name a command that
# needs an interface, a display or a camera.
CLIENT_ONLY = (
    "hasInterface",
    "cameraOn",
    "camCreate",
    "createCamera",
    "switchCamera",
    "cutText",
    "titleText",
    "createDialog",
    "createDisplay",
    "ctrlCreate",
    "ctrlSetText",
    "diag_captureFrame",
)

# The literal mount path the runner must build (CBA_fnc_test's AEE form).
PATH_FORMAT = r"\z\aee\addons\%1\test.sqf"

_DEFINE = r"#define\s+AURORA_{name}\s+\[([^\]]+)\]"


def _test_text(component: str) -> str:
    return (ADDONS / component / "test.sqf").read_text(encoding="utf-8")


class TestComponentTestRunner(unittest.TestCase):
    def test_the_runner_exists(self):
        self.assertTrue(RUNNER.exists(), f"missing runner {RUNNER}")

    def test_the_runner_builds_the_aee_mount_path(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn(PATH_FORMAT, text, "the runner must build the AEE mount path")
        self.assertIn("fileExists", text, "the runner must guard a missing test file")

    def test_the_runner_returns_the_published_failure_count(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn(
            "aee_test_failures_%1",
            text,
            "the runner must read the published failure count",
        )
        self.assertIn("-1", text, "an absent test file must return -1")

    def test_the_runner_compiles_the_test_rather_than_waiting_on_a_handle(self):
        # execVM returns the PATH STRING for an addon file with a runtime
        # #include, so scriptDone on that value never fires and the runner
        # hangs.  The runner must preprocess-and-call instead.
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn(
            "preprocessFileLineNumbers",
            text,
            "the runner must preprocess the test file",
        )
        self.assertNotIn(
            "waitUntil",
            text,
            "the runner must not wait on an execVM handle for an addon file",
        )

    def test_the_runner_is_registered_in_the_prep(self):
        self.assertIn("PREP(test)", PREP.read_text(encoding="utf-8"))

    def test_the_cba_familiar_public_name_is_exposed(self):
        text = POST_INIT.read_text(encoding="utf-8")
        self.assertIn('"AEE_fnc_test"', text, "the public alias must be set")
        self.assertIn("FUNC(test)", text, "the alias must point at the runner")


class TestComponentTestFiles(unittest.TestCase):
    def test_every_component_has_a_test_file(self):
        missing = [c for c in COMPONENTS if not (ADDONS / c / "test.sqf").exists()]
        self.assertEqual(
            missing, [], "components with no test.sqf: " + ", ".join(missing)
        )

    def test_every_test_file_includes_the_component_header(self):
        for component in COMPONENTS:
            self.assertIn(
                '#include "script_component.hpp"',
                _test_text(component),
                f"{component}/test.sqf must include script_component.hpp",
            )

    def test_every_test_file_logs_the_cba_style_result(self):
        for component in COMPONENTS:
            text = _test_text(component)
            self.assertIn(
                '"TEST: OK - %1"', text, f"{component}/test.sqf must log TEST: OK"
            )
            self.assertIn(
                '"TEST: FAIL - %1: %2"',
                text,
                f"{component}/test.sqf must log TEST: FAIL",
            )
            self.assertIn(
                f"[AEE-TEST] {component} DONE",
                text,
                f"{component}/test.sqf must end with the DONE line",
            )

    def test_every_test_file_publishes_its_failure_count(self):
        for component in COMPONENTS:
            self.assertIn(
                f'"aee_test_failures_{component}"',
                _test_text(component),
                f"{component}/test.sqf must publish aee_test_failures_{component}",
            )

    def test_every_test_file_is_headless_safe(self):
        for component in COMPONENTS:
            text = _test_text(component)
            for token in CLIENT_ONLY:
                self.assertNotIn(
                    token,
                    text,
                    f"{component}/test.sqf names the client-only command {token}",
                )


class TestAuroraColourContract(unittest.TestCase):
    """The lighting test asserts the runtime macros; pin the literals too."""

    def _colour(self, name: str) -> list[float]:
        header = (ADDONS / "lighting" / "script_component.hpp").read_text(
            encoding="utf-8"
        )
        match = re.search(_DEFINE.format(name=name), header)
        self.assertIsNotNone(match, f"AURORA_{name} not defined in the header")
        return [float(part) for part in match.group(1).split(",")]

    def test_green_is_dominant_in_green(self):
        r, g, b = self._colour("GREEN")
        self.assertGreater(g, r, "aurora green must be G-dominant over R")
        self.assertGreater(g, b, "aurora green must be G-dominant over B")

    def test_red_is_dominant_in_red(self):
        r, g, b = self._colour("RED")
        self.assertGreater(r, g, "aurora red must be R-dominant over G")
        self.assertGreater(r, b, "aurora red must be R-dominant over B")


if __name__ == "__main__":
    unittest.main()
