#!/usr/bin/env python3
"""Contract test: the engine-class ownership sentinels (ADR-027).

ADR-027 detects the silent load-order loss with a sentinel: one declared
property per engine class AEE owns, read at init and compared to AEE's value.
This test pins the registry, the generated SQF, and the wiring into
fnc_dumpState, so a sentinel cannot drift from the config it guards.

Run: python3 -m unittest tools.tests.test_ownership_sentinels
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import gen_ownership_sentinels as gos  # noqa: E402

DUMP = ROOT / "addons" / "diagnostics" / "functions" / "fnc_dumpState.sqf"
PREINIT = ROOT / "addons" / "core" / "XEH_preInit.sqf"

# The engine classes AEE owns that must carry a sentinel.
REQUIRED_ROOTS = {
    "CfgWorlds",
    "CfgCloudlets",
    "CfgWeapons",
    "CfgMarkerColors",
    "CfgMarkers",
    "CfgVehicles",
    "RscMapControl",
}


class TestSentinelRegistry(unittest.TestCase):
    def test_registry_audits_clean(self):
        errors = gos.audit(gos.load_registry())
        self.assertEqual(errors, [], "\n".join(errors))

    def test_generated_sqf_is_current(self):
        generated = gos.build(gos.load_registry())
        self.assertTrue(gos.OUT.exists(), "ownership_sentinels.sqf is missing")
        self.assertEqual(
            gos.OUT.read_text(encoding="utf-8"),
            generated,
            "ownership_sentinels.sqf is stale: run tools/gen_ownership_sentinels.py",
        )

    def test_covers_every_owned_class_root(self):
        registry = gos.load_registry()
        roots = {entry["path"][0] for entry in registry["sentinels"]}
        self.assertEqual(
            REQUIRED_ROOTS - roots,
            set(),
            f"engine class(es) with no sentinel: {sorted(REQUIRED_ROOTS - roots)}",
        )

    def test_audit_detects_evidence_drift(self):
        # Negative control: an expected value that no longer appears in the
        # named source is reported, so the registry cannot drift silently.
        bad = {
            "sentinels": [
                {
                    "id": "x",
                    "path": ["CfgWorlds"],
                    "property": "starEmissivity",
                    "type": "number",
                    "expected": 999,
                    "source": "addons/environmental/config.cpp",
                    "evidence": "starEmissivity = 999;",
                }
            ]
        }
        self.assertTrue(gos.audit(bad))

    def test_audit_detects_duplicate_id(self):
        bad = {
            "sentinels": [
                {
                    "id": "dup",
                    "path": ["A"],
                    "property": "p",
                    "type": "number",
                    "expected": 1,
                    "source": "addons/core/config.cpp",
                    "evidence": "interval = 0.005;",
                },
                {
                    "id": "dup",
                    "path": ["B"],
                    "property": "p",
                    "type": "number",
                    "expected": 2,
                    "source": "addons/core/config.cpp",
                    "evidence": "interval = 0.01;",
                },
            ]
        }
        self.assertTrue(any("duplicate" in e for e in gos.audit(bad)))

    def test_dumpstate_reads_the_registry(self):
        text = DUMP.read_text(encoding="utf-8")
        self.assertIn("QEGVAR(core,ownershipSentinels)", text)
        self.assertIn("getNumber _entry", text)
        self.assertIn("getArray _entry", text)
        self.assertIn("_mismatches", text)

    def test_preinit_loads_the_generated_sqf(self):
        text = PREINIT.read_text(encoding="utf-8")
        self.assertIn("data\\ownership_sentinels.sqf", text)
        self.assertIn("QGVAR(ownershipSentinels)", text)


if __name__ == "__main__":
    unittest.main()
