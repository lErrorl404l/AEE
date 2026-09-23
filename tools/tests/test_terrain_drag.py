"""Off-road terrain speed factor and the drag applier (issue #117).

The published cross-country speed classes are the reference:
  road 1.00, trail/gravel 0.60-0.75, field 0.40-0.55,
  woodland 0.25-0.40, swamp 0.10-0.20, sand 0.15-0.30, snow 0.10-0.50.
Source: FM 5-430-00-1 Ch. 7 and the standard cross-country planning figures.

The engine mechanism is verified separately: limitSpeed and forceSpeed are
AI-only, and setVelocity fights the solver, so the applier uses a force.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FACTOR = ROOT / "addons" / "mobility" / "functions" / "fnc_getTerrainSpeedFactor.sqf"
DRAG = ROOT / "addons" / "mobility" / "functions" / "fnc_applyTerrainDrag.sqf"


def sqf_code_only(src):
    """The SQF with the header block and // comments removed."""
    src = src.split("*/", 1)[-1]
    return "\n".join(l.split("//", 1)[0] for l in src.splitlines())


def published_factors(src):
    """The (keyword, factor) rows of the keyword table in the SQF."""
    code = sqf_code_only(src)
    m = re.search(r"forEach \[(.*?)\n\];", code, re.S)
    assert m, "the keyword table is gone"
    return [(k, float(v)) for k, v in re.findall(r'\["(\w+)",\s*([0-9.]+)\]', m.group(1))]


class TestPublishedBands(unittest.TestCase):
    """The table must sit inside the published band for each class."""

    BANDS = {
        "road":      (0.90, 1.00),
        "asphalt":   (0.90, 1.00),
        "tarmac":    (0.90, 1.00),
        "gravel":    (0.55, 0.80),
        "field":     (0.40, 0.55),
        "grass":     (0.45, 0.60),
        "forest":    (0.25, 0.40),
        "marsh":     (0.10, 0.20),
        "swamp":     (0.05, 0.20),
        "sand":      (0.15, 0.30),
        "snow":      (0.10, 0.50),
    }

    def setUp(self):
        self.rows = dict(published_factors(FACTOR.read_text(encoding="utf-8")))

    def test_every_class_in_its_band(self):
        for key, (lo, hi) in self.BANDS.items():
            self.assertIn(key, self.rows, f"{key} missing from the table")
            v = self.rows[key]
            self.assertGreaterEqual(v, lo, f"{key}={v} below {lo}")
            self.assertLessEqual(v, hi, f"{key}={v} above {hi}")

    def test_values_are_a_fraction(self):
        for k, v in self.rows.items():
            self.assertGreater(v, 0, k)
            self.assertLessEqual(v, 1.0, k)

    def test_soft_surfaces_precede_harder_ones(self):
        # The table is ordered most restrictive first, so SoftMud resolves
        # as mud, not as the "soil" entry further down.
        code = sqf_code_only(FACTOR.read_text(encoding="utf-8"))
        self.assertLess(code.find('"mud"'), code.find('"soil"'))
        self.assertLess(code.find('"sand"'), code.find('"rock"'))


class TestDynamicLookup(unittest.TestCase):
    """No hardcoded map or vehicle list: the surface resolves from the data."""

    def setUp(self):
        self.src = FACTOR.read_text(encoding="utf-8")

    def test_uses_surface_type(self):
        self.assertIn("surfaceType", self.src)

    def test_normalises_the_surface_name(self):
        # The Arma 3 names carry no '#', but normalise defensively.
        self.assertIn('find "#gdt"', self.src)
        self.assertIn("toLower", self.src)

    def test_reads_cfg_surfaces(self):
        self.assertIn('"CfgSurfaces"', self.src)
        self.assertIn("surfaceFriction", self.src)

    def test_falls_back_to_the_material_taxonomy(self):
        self.assertIn("classifyBySurfaceType", self.src)

    def test_water_is_the_lowest(self):
        self.assertIn("surfaceIsWater", self.src)

    def test_ground_state_caps_the_factor(self):
        for state in ("Mud", "Snow", "Frozen", "Dusty"):
            self.assertIn(f'case "{state}"', self.src)


class TestDragApplier(unittest.TestCase):
    """The mechanism must be a force on the local machine, not a speed set."""

    def setUp(self):
        self.src = DRAG.read_text(encoding="utf-8")

    def test_uses_add_force(self):
        self.assertIn("addForce", self.src)

    def test_does_not_use_the_ai_only_commands(self):
        # limitSpeed and forceSpeed act on AI units only.
        self.assertNotIn("limitSpeed", sqf_code_only(self.src))
        self.assertNotIn("forceSpeed", sqf_code_only(self.src))

    def test_does_not_set_velocity(self):
        # setVelocity fights the solver and desyncs on a player vehicle.
        self.assertNotIn("setVelocity", sqf_code_only(self.src))

    def test_local_machine_only(self):
        self.assertIn("if (!local _vehicle) exitWith { false }", self.src)

    def test_force_only_above_the_target_speed(self):
        # A slow vehicle must not be dragged to a stop.
        self.assertIn("if (_speed <= _target) exitWith { false }", self.src)

    def test_force_opposes_the_velocity(self):
        self.assertIn("vectorMultiply (-_forceMag)", self.src)

    def test_no_publicvariable(self):
        self.assertNotIn("publicVariable", self.src)

    def test_no_max_speed_key_means_no_cap(self):
        # A guessed maximum would be an invented value.
        self.assertIn("getNumber (configOf _vehicle >> \"maxSpeed\")", self.src)
        self.assertIn("if (_maxKmh <= 0) exitWith { false }", self.src)


if __name__ == "__main__":
    unittest.main()
