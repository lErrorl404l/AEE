#!/usr/bin/env python3
"""Contract test: every compat_ace3 function declares its direction (ADR-027).

AEE owns by declaration and load order, not by force.  A compat function that
carries no declared direction is a silent policy gap: it is not clear whether
AEE is the declared authority (the host stands down) or the host owns the
subsystem (AEE adapts).  This test fails when a compat_ace3 function has no
declared direction, and when the rendered integrations.qmd block drifts.

Run: python3 -m unittest tools.tests.test_compat_directions
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import gen_compat_directions as gcd  # noqa: E402


class TestCompatDirections(unittest.TestCase):
    def test_every_compat_function_has_a_declared_direction(self):
        manifest = gcd.load_manifest()
        declared = manifest["functions"]
        missing = sorted(gcd.functions_on_disk() - set(declared))
        self.assertEqual(
            missing,
            [],
            f"compat_ace3 function(s) with no declared direction: {missing}",
        )

    def test_no_orphan_direction_entries(self):
        manifest = gcd.load_manifest()
        on_disk = gcd.functions_on_disk()
        orphans = sorted(set(manifest["functions"]) - on_disk)
        self.assertEqual(
            orphans, [], f"direction entries for missing functions: {orphans}"
        )

    def test_directions_are_from_the_allowed_set(self):
        manifest = gcd.load_manifest()
        for fn, entry in manifest["functions"].items():
            self.assertIn(entry["direction"], gcd.ALLOWED, f"{fn} direction")

    def test_integration_functions_declare_a_two_way_direction(self):
        # An integration function must be an ownership claim or an adaptation.
        # `diagnostics` is the only non-integration direction.
        manifest = gcd.load_manifest()
        for fn, entry in manifest["functions"].items():
            if entry["direction"] == "diagnostics":
                self.assertGreaterEqual(len(entry.get("host_api", [])), 0)
            else:
                self.assertIn(entry["direction"], gcd.INTEGRATION, fn)

    def test_audit_reports_a_function_with_no_direction(self):
        # Negative control: a function on disk that the manifest omits is
        # reported, so the audit cannot pass vacuously.
        manifest = {"functions": {"fnc_known": {"direction": "adaptation"}}}
        errors = gcd.audit({"fnc_known", "fnc_undeclared"}, manifest)
        self.assertTrue(any("fnc_undeclared" in e for e in errors), errors)

    def test_audit_reports_an_orphan_entry(self):
        manifest = {"functions": {"fnc_gone": {"direction": "adaptation"}}}
        errors = gcd.audit({"fnc_live"}, manifest)
        self.assertTrue(any("fnc_gone" in e for e in errors), errors)

    def test_audit_accepts_a_complete_manifest(self):
        manifest = {"functions": {"fnc_a": {"direction": "ownership-claim"}}}
        self.assertEqual(gcd.audit({"fnc_a"}, manifest), [])

    def test_generated_block_is_current(self):
        manifest = gcd.load_manifest()
        self.assertEqual(
            gcd.audit(gcd.functions_on_disk(), manifest),
            [],
            "manifest drift: run tools/gen_compat_directions.py",
        )
        doc = gcd.DOC.read_text(encoding="utf-8")
        present = gcd.current_block(doc)
        self.assertIsNotNone(present, "integrations.qmd is missing the direction block")
        self.assertEqual(
            present,
            gcd.build_block(manifest),
            "integrations.qmd direction block is stale: run "
            "python3 tools/gen_compat_directions.py",
        )


if __name__ == "__main__":
    unittest.main()
