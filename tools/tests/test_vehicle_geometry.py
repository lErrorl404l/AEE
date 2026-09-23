"""Vehicle geometry derived from the vehicle itself (issue #117).

The function reads the real wheel geometry rather than a class table, so
the tests check the SOURCE for the derivation and the safety rules.  A
Python mirror cannot test a config lookup or a model read, so it does not
try: it pins the rules that make the read safe.

Verified facts (BI wiki selectionNames/selectionPosition, BI's own
B_MRAP_01_F Memory LOD dump, the Cars Config Guidelines):
  - wheel_<side>_<station>_axis and _bound, SIDE FIRST (1 = left,
    2 = right, station 1 = front).  The Guidelines prose states the order
    the other way round; the model dump is authoritative.
  - The points are engine-required on every CarX vehicle.
  - selectionPosition returns [0,0,0] BOTH for a missing name and for a
    real point at the origin, so membership must be checked first.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEOM = ROOT / "addons" / "mobility" / "functions" / "fnc_getVehicleGeometry.sqf"
SSF = ROOT / "addons" / "mobility" / "functions" / "fnc_calculateSSF.sqf"
SOIL = ROOT / "addons" / "mobility" / "functions" / "fnc_calculateSoilStrength.sqf"
LIMITS = ROOT / "addons" / "mobility" / "functions" / "fnc_calculateTerrainLimits.sqf"


def code(src):
    """The SQF with the header block and // comments removed."""
    return "\n".join(
        l.split("//", 1)[0] for l in src.split("*/", 1)[-1].splitlines()
    )


class TestGeometrySource(unittest.TestCase):
    def setUp(self):
        self.src = GEOM.read_text(encoding="utf-8")
        self.body = code(self.src)

    def test_reads_the_config_route_first(self):
        # The primary source: real data, survives a model rename.
        self.assertIn('"CfgVehicles" >> _type >> "Wheels"', self.body)
        self.assertIn('>> "center"', self.body)
        self.assertIn('>> "boundary"', self.body)

    def test_reads_the_model_as_the_fallback(self):
        self.assertIn("selectionPosition", self.body)
        self.assertIn('"Memory"', self.body)

    def test_uses_the_side_major_names(self):
        # wheel_<side>_<station>, side first.
        for key in ("wheel_1_1", "wheel_2_1", "wheel_1_2", "wheel_2_2"):
            self.assertIn(key, self.body, f"{key} missing from the station list")

    def test_track_width_is_left_to_right(self):
        # The distance between the left and right axes at one station.
        self.assertIn("_fl vectorDistance _fr", self.body)
        self.assertIn("_rl vectorDistance _rr", self.body)

    def test_wheelbase_is_front_to_rear(self):
        self.assertIn("_fl vectorDistance _rl", self.body)
        self.assertIn("_fr vectorDistance _rr", self.body)

    def test_tyre_diameter_is_twice_axis_to_bound(self):
        self.assertRegex(self.body, r"vectorDistance.*\* 2|\) \* 2")

    def test_wheel_count_is_the_declared_stations(self):
        self.assertIn("_count = count _axisPos", self.body)

    def test_physical_bands_guard_every_value(self):
        # A misread point must be discarded, not used.
        self.assertIn("_track > 0.8 && _track < 4.0", self.body)
        self.assertIn("_base > 1.0 && _base < 8.0", self.body)
        self.assertIn("_tyre > 0.2 && _tyre < 2.0", self.body)

    def test_membership_is_checked_before_a_position_is_used(self):
        # selectionPosition returns [0,0,0] for a missing name as well as a
        # real origin point, so a name must be declared before its position
        # is trusted.  The function records only declared wheels.
        self.assertIn('isArray (_wc >> "center")', self.body)

    def test_the_steering_axis_resolves_to_the_wheel_it_steers(self):
        # ..._steering_axis also ends in "_axis", so the suffix strip must
        # leave "wheel_1_1_steering" -- NOT the bare name, and NOT the
        # whole string.  Either mistake changes what is counted, so the
        # arithmetic is evaluated here rather than pattern-matched.
        def strip(n):
            n_len = len(n)
            is_axis = n.find("_axis") == n_len - 5
            is_bound = n.find("_bound") == n_len - 6
            if not (is_axis or is_bound):
                return None
            suffix = [5, 6][1 if is_bound else 0]
            return n[: n_len - suffix]

        # A plain wheel and its bound strip to the bare station key.
        self.assertEqual(strip("wheel_1_1_axis"), "wheel_1_1")
        self.assertEqual(strip("wheel_2_1_bound"), "wheel_2_1")
        # The steering axis strips to a name that is NOT a station key, so
        # the membership test that follows rejects it.
        self.assertEqual(strip("wheel_1_1_steering_axis"), "wheel_1_1_steering")
        self.assertNotIn(
            strip("wheel_1_1_steering_axis"),
            ["wheel_1_1", "wheel_1_2", "wheel_2_1", "wheel_2_2"],
        )
        # And the SQF keeps the station list it is checked against.
        for key in ("wheel_1_1", "wheel_1_2", "wheel_2_1", "wheel_2_2"):
            self.assertIn(key, self.body)

    def test_no_hashmap_method_calls(self):
        # The repo uses no hashmap method calls and the parser rejects them.
        self.assertNotIn("containsKey", self.body)


class TestCallSitesUseGeometry(unittest.TestCase):
    """The class tables become the fallback, not the source."""

    def test_ssf_uses_the_real_track_width(self):
        body = code(SSF.read_text(encoding="utf-8"))
        self.assertIn("getVehicleGeometry", body)
        # The table must still exist as the fallback.
        self.assertIn("_trackTable", body)

    def test_soil_strength_uses_real_tyre_and_wheel_count(self):
        body = code(SOIL.read_text(encoding="utf-8"))
        self.assertIn("getVehicleGeometry", body)
        self.assertIn("_n = _geo select 3", body)

    def test_terrain_limits_uses_the_real_wheelbase(self):
        body = code(LIMITS.read_text(encoding="utf-8"))
        self.assertIn("getVehicleGeometry", body)
        self.assertIn("_wheelbase = _geo select 1", body)

    def test_geometry_wins_over_the_table(self):
        # Each call site applies the measured value only when it is real, so
        # a vehicle with no readable geometry keeps its table.  Either gate
        # form is correct: `if (x > 0)` or `if (x <= 0)` with the table in
        # the branch.
        for f in (SSF, SOIL, LIMITS):
            body = code(f.read_text(encoding="utf-8"))
            self.assertRegex(
                body,
                r"\(_geo select \d\) > 0|_track <= 0",
                f"{f.name} does not gate the geometry on a real value",
            )


if __name__ == "__main__":
    unittest.main()
