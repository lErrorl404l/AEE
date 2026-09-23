"""The engine `wind` command must carry AEE's final terrain-scaled vector.

Issue #78, Row 1 and Row 4.  ACE3 ballistics reads the engine `wind`
command, NOT a mission variable, so a shot over a ridge is deflected by the
engine's flat vector unless AEE pushes its terrain-scaled value.  Before
this change `setWind` ran only inside `if (_moduleMult != 1)`, so the
terrain speed-up (Taylor and Lee 1984) was computed, stored, and never
reached the engine.

These tests read the SOURCE.  A Python mirror of the branch would encode
the same bug and pass while the SQF stayed wrong, which is the TEST-MIRROR
trap this repository records.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIND = ROOT / "addons" / "atmos" / "functions" / "state" / "fnc_updateWind.sqf"
ANNEX = ROOT / "docs" / "wiki" / "annexes" / "annex-c-variable-reference.qmd"


class TestWindEnginePush(unittest.TestCase):
    def setUp(self):
        self.src = WIND.read_text(encoding="utf-8")

    def test_setwind_is_not_gated_on_the_module_multiplier(self):
        """The old defect: setWind inside `if (_moduleMult != 1)`.

        The terrain step runs AFTER that branch, so a gated call pushes the
        pre-terrain vector.  The push must sit outside any module-multiplier
        conditional.
        """
        gated = re.search(
            r"if \(_moduleMult != 1\) then \{(?:(?!\};).)*?setWind",
            self.src,
            re.S,
        )
        self.assertIsNone(
            gated,
            "setWind is gated on the module multiplier again: the terrain-"
            "scaled vector never reaches the engine",
        )

    def test_final_vector_is_pushed_after_the_terrain_speedup(self):
        """The push must come after `calculateTerrainWind` modified `_wind`."""
        terrain = self.src.find("calculateTerrainWind")
        push = self.src.find("setWind [")
        self.assertGreater(terrain, -1, "the terrain speed-up step is gone")
        self.assertGreater(push, -1, "the engine push is gone")
        self.assertGreater(
            push,
            terrain,
            "setWind runs before the terrain speed-up: it pushes a stale vector",
        )

    def test_push_is_change_guarded(self):
        """Calling setWind every tick resets the engine gust cycle."""
        self.assertIn("pushedWind", self.src, "no change guard on the push")
        guarded = re.search(r"if \(_windChanged\) then \{\s*setWind", self.src, re.S)
        self.assertIsNotNone(
            guarded,
            "setWind is not guarded by a change check: the gust cycle resets",
        )

    def test_pushed_variable_is_documented(self):
        """aee_core_pushedWind must be in annex-c or CI fails UNDOCUMENTED."""
        annex = ANNEX.read_text(encoding="utf-8")
        self.assertIn(
            "aee_core_pushedWind",
            annex,
            "aee_core_pushedWind is undocumented: CI will fail UNDOCUMENTED",
        )


if __name__ == "__main__":
    unittest.main()
