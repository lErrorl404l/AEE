#!/usr/bin/env python3
"""Complaint-landscape validator (issue #159).

Locks the roadmap mapping in docs/wiki/research/player-complaints-
landscape.md against the live issue tracker: every referenced issue
must still be open (or the doc's status column must match).  A closed
issue referenced as an OPEN target, or an issue that no longer exists,
means the doc has drifted and must be corrected.

The shipped/not-built claims are also verified against the codebase
(the ballistics addon is real; the setAnimSpeedCoef coupling is not
yet built).
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
DOC = REPO / "docs/wiki/research/player-complaints-landscape.md"


class TestRoadmapMapping(unittest.TestCase):
    def test_referenced_issues_exist_and_are_open(self):
        text = DOC.read_text(encoding="utf-8")
        nums = sorted({int(m) for m in re.findall(r"#(\d{2,3})", text)})
        # status column: which issues the doc calls OPEN
        open_nums = []
        # walk the mapping table: lines with | #N ( | ... | OPEN |
        for line in text.splitlines():
            m = re.match(r"\|\s*#(\d+)\s*\|.*\|\s*(OPEN|CLOSED|SHIPPED)\s*\|", line)
            if m:
                if m.group(2) == "OPEN":
                    open_nums.append(int(m.group(1)))
        self.assertTrue(nums, "no issue references found in the doc")

        import subprocess

        for n in open_nums:
            r = subprocess.run(
                ["gh", "issue", "view", str(n), "--json", "state"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, f"issue #{n} does not exist (doc drift)")
            self.assertIn(
                '"state": "OPEN"',
                r.stdout,
                f"issue #{n} closed but doc marks it OPEN target",
            )

    def test_ballistics_shipped_verified(self):
        # The doc says ballistics depth is SHIPPED.  Verify the addon
        # and the two cited functions exist.
        self.assertTrue((REPO / "addons/ballistics").is_dir())
        for fn in ("fnc_calculateAirDensity.sqf", "fnc_calculateAmmoTemperature.sqf"):
            self.assertTrue(
                (REPO / "addons/ballistics/functions" / fn).exists(),
                f"ballistics {fn} missing - doc SHIPPED claim drifted",
            )

    def test_anim_coupling_not_built(self):
        # The doc says the setAnimSpeedCoef coupling is NOT built.
        # Verify no code calls it.
        hits = []
        for sqf in (REPO / "addons").rglob("*.sqf"):
            if "setAnimSpeedCoef" in sqf.read_text(encoding="utf-8"):
                hits.append(str(sqf))
        self.assertEqual(hits, [], f"setAnimSpeedCoef built without doc update: {hits}")

    def test_engine_fundamental_claims_present(self):
        # The do-not-claim section must list the five engine-fundamental
        # complaints (the credibility guard).
        text = DOC.read_text(encoding="utf-8")
        for claim in (
            "Single-threaded performance",
            "Netcode/desync",
            "Ragdoll feel",
            "Sound occlusion",
            "AI detection core",
        ):
            self.assertIn(claim, text)


if __name__ == "__main__":
    unittest.main()
