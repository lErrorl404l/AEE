"""Frost depth must drive the Frozen ground state (issues #35/#84).

The freeze/thaw model solves the Stefan freeze depth and publishes it as
aee_core_frozenDepth_m, but nothing consumed it, so a DRY cold snap never
classified the ground as Frozen: the old branch required recent RAIN
(aee_core_rainAccum > 0.05).  The physical test is frost in the ground.

These tests read the SOURCE, per the project's rule: a Python mirror of the
branch would encode the same bug and pass while the SQF stayed wrong.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GROUND = ROOT / "addons" / "mobility" / "functions" / "fnc_updateGroundState.sqf"
FREEZE = (
    ROOT
    / "addons"
    / "environmental"
    / "functions"
    / "terrain"
    / "fnc_calculateFreezeThawCycling.sqf"
)


class TestFrostFeedsGroundState(unittest.TestCase):
    def setUp(self):
        self.src = GROUND.read_text(encoding="utf-8")

    def test_frost_depth_is_read(self):
        self.assertIn(
            "frozenDepth_m",
            self.src,
            "the ground state does not read the Stefan freeze depth",
        )

    def test_frozen_branch_accepts_frost_without_rain(self):
        """The Frozen test must pass on frost depth OR recent rain.

        The old form required rain alone, which is wrong for a dry cold
        snap: the ground freezes with no precipitation recorded.
        """
        cond = re.search(
            r"if \(!isNil \"_T\" && \(_T < -2\)[^\n]*_groundFrozen[^\n]*\) then \{",
            self.src,
        )
        self.assertIsNotNone(cond, "the Frozen branch is gone or restructured")
        text = cond.group(0)
        self.assertIn(
            "_groundFrozen",
            text,
            "the Frozen branch still requires rain only",
        )

    def test_single_writer_is_preserved(self):
        """Adding a second writer to groundState is the defect class.

        The frost depth must FEED this decision, not write its own state.
        """
        writes = re.findall(r"setVariable \[QEGVAR\(core,groundState\)", self.src)
        self.assertEqual(
            len(writes),
            1,
            f"groundState has {len(writes)} writers in this function; "
            "the fix must feed the decision, not add a writer",
        )


class TestProducerStillPublishesWhatIsConsumed(unittest.TestCase):
    """The consumed variable must exist on the producer side."""

    def test_freeze_thaw_publishes_frozen_depth(self):
        src = FREEZE.read_text(encoding="utf-8")
        self.assertIn(
            "QEGVAR(core,frozenDepth_m)",
            src,
            "the freeze/thaw model no longer publishes frozenDepth_m, so the "
            "consumer reads the default 0 forever",
        )


if __name__ == "__main__":
    unittest.main()
