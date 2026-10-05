#!/usr/bin/env python3
"""Structural checks on AEE's client-side per-frame loops.

`addons/mobility/XEH_postInit.sqf` runs five handlers at interval 0.05 s
(20 Hz, not every rendered frame).  Each handler caches a candidate list on a
refresh timer, and the turbulence loop does the same through a mission
variable.  Each list was built from `vehicles` with no radius test, so the
per-frame loop ran a distance check against every ground vehicle in the world.
Three per-frame world scans is a stutter.

The radius test has to live in the REFRESH, not in the per-frame loop.  This
reads the SOURCE, because a mirror of the loop would prove nothing about the
loop.  Comments are stripped before every search, so prose describing a
construct cannot satisfy an assertion about it.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_MOBILITY = REPO / "addons" / "mobility"
_POST_INIT = _MOBILITY / "XEH_postInit.sqf"
_TURBULENCE = _MOBILITY / "functions" / "fnc_applyFlightTurbulence.sqf"


def _code_only(text):
    """Blank out line comments so a search cannot match the prose."""
    out = []
    for line in text.split("\n"):
        cut = line.find("//")
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


class TestPerFrameRadiusFiltering(unittest.TestCase):
    """The radius belongs in the refresh, never in the per-frame body."""

    def setUp(self):
        self.post = _code_only(_POST_INIT.read_text(encoding="utf-8"))
        self.turb = _code_only(_TURBULENCE.read_text(encoding="utf-8"))

    def test_post_init_runs_five_per_frame_handlers(self):
        """Guard the premise: these loops are the per-frame cost."""
        count = len(
            re.findall(r"\}, 0\.05\] call CBA_fnc_addPerFrameHandler", self.post)
        )
        self.assertEqual(count, 5, f"expected 5 0.05 s handlers, found {count}")

    def test_rollover_radius_is_in_the_refresh(self):
        refresh = self.post.index("if ((time - GVAR(rolloverRefresh)) > 1) then")
        select = self.post.index("GVAR(rolloverVehicles) = vehicles select")
        body = self.post.index("} forEach GVAR(rolloverVehicles)")
        self.assertLess(refresh, select, "the refresh guard must precede the select")
        self.assertLess(select, body, "the select must precede the per-frame body")
        self.assertIn("distance _ref", self.post[select:body].split("};")[0])
        # Bound the search to THIS forEach block.  An unbounded tail reaches
        # into the terrain-drag block, whose refresh legitimately filters.
        open_at = self.post.rindex("{", 0, body)
        for_each_body = self.post[open_at : body + 1]
        self.assertNotIn(
            "distance", for_each_body, "the per-frame body still measures range"
        )

    def test_terrain_radius_is_in_the_refresh(self):
        refresh = self.post.index("if ((time - GVAR(terrainRefresh)) > 1) then")
        select = self.post.index("GVAR(terrainVehicles) = vehicles select")
        body = self.post.index("} forEach GVAR(terrainVehicles)")
        self.assertLess(refresh, select, "the refresh guard must precede the select")
        self.assertLess(select, body, "the select must precede the per-frame body")
        self.assertIn("distance _ref", self.post[select:body].split("};")[0])
        open_at = self.post.rindex("{", 0, body)
        for_each_body = self.post[open_at : body + 1]
        self.assertNotIn(
            "distance", for_each_body, "the per-frame body still measures range"
        )

    def test_turbulence_radius_is_cached_not_reselected(self):
        """Aircraft: radius in the cache, physics tests stay per frame."""
        cache = self.turb.index("_aircraft = vehicles select")
        self.assertIn("distance _refPos", self.turb[cache : cache + 400])
        candidates = self.turb.index("private _candidates = _aircraft select")
        segment = self.turb[candidates : self.turb.index("};", candidates)]
        self.assertNotIn(
            "distance", segment, "the per-frame candidate select still measures range"
        )
        # The tests that are genuinely per-frame physics must survive.
        for token in ("getPosATL", "speed _x", "alive _x"):
            self.assertIn(token, segment, f"{token} must stay per frame")


if __name__ == "__main__":
    unittest.main()
