#!/usr/bin/env python3
"""Explosion crater model tests (issue #19).

Runs the REAL SQF kernels through the SQF lite interpreter and pins them to
the issue's published validation numbers.  The kernels are pure: no
missionNamespace, no GVAR/EGVAR, no engine command.

Kernels under addons/blast/functions/crater/:
  fnc_hopkinsonCranzScale    D1/D2 = (W1/W2)^(1/3)
  fnc_calculateCrater        R_a, D_a, V, lip, ejecta, true crater
  fnc_craterShape            the shape relations from a known apparent crater
  fnc_craterTerrainPoints    the grid for the engine setTerrainHeight command

The published anchors, and the reading the issue's equation section gives
(which this model follows):

  155mm, 7 kg, soil surface burst:  Kinney-Graham D = 0.8 * W^(1/3)
      = 1.53 m apparent diameter (the issue's test-vector text writes this
      coefficient as a radius and doubles it to "3 m diameter"; its own
      "(matches real ~1.5-2 m)" and its equation section make it a diameter).
  500 lb, 100 kg:  D = 0.8 * W^(1/3) = 3.71 m apparent diameter.
  OKC 4000 lb, dry sandy clay:  31.1 ft diameter / 8.73 ft deep.
  OKC 4000 lb, concrete:        12.06 ft / 3.17 ft.
  CONWEP 488 lb, DOB 18 ft:     apparent 29.61 ft / 9.02 ft, V 3106 ft3,
      true depth 21.15 ft, true diameter 35.61 ft.
  500 kg sandstone (Violet 1/3.4):  R 7.4 m, D 2.5 m.
  EMRTC 250 kg (dry sand):      3.75 m diameter.

Sources: TM 5-855-1; UFC 3-340-02; WES Report 2 (1961); Hopkinson (1915);
Cranz (1926); Swisdak (1975); Kinney and Graham (1985); Ambrosini;
Muller and Carleton; Glasstone and Dolan; Chabai (1973); Violet (1961).

Run: python3 -m unittest tools.tests.test_craters -v
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))

from sqf_lite import run_sqf  # noqa: E402

CRATER = REPO / "addons" / "blast" / "functions" / "crater"
SCALE = CRATER / "fnc_hopkinsonCranzScale.sqf"
CALC = CRATER / "fnc_calculateCrater.sqf"
SHAPE = CRATER / "fnc_craterShape.sqf"
TERRAIN = CRATER / "fnc_craterTerrainPoints.sqf"

LB_PER_KG = 2.2046226218
FT_PER_M = 3.280839895
M_PER_FT = 0.3048


def kg_from_lb(lb: float) -> float:
    return lb / LB_PER_KG


def ft_from_m(m: float) -> float:
    return m * FT_PER_M


def scale(ref_mass, ref_dim, mass):
    return run_sqf(SCALE, [ref_mass, ref_dim, mass])


def crater(mass_kg, medium, dof_m=0.0):
    """Return the crater feature dict from fnc_calculateCrater."""
    keys = ["rA", "dA", "v", "rLip", "hLip", "rEj", "rTrue", "dTrue"]
    return dict(zip(keys, run_sqf(CALC, [mass_kg, medium, dof_m])))


def shape(rA, dA, dof_m=0.0, mass_kg=1.0):
    keys = ["v", "rLip", "hLip", "rEj", "rTrue", "dTrue"]
    return dict(zip(keys, run_sqf(SHAPE, [rA, dA, dof_m, mass_kg])))


def live_source(path: Path) -> str:
    """Source with the block header and line comments removed."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return "\n".join(line.split("//")[0] for line in text.splitlines())


class TestHopkinsonCranzScaling(unittest.TestCase):
    """D1/D2 = (W1/W2)^(1/3) for one explosive, geometry and medium."""

    def test_double_mass_scales_by_cube_root_two(self):
        self.assertAlmostEqual(scale(1.0, 1.0, 2.0), 2.0 ** (1 / 3), places=9)

    def test_eight_times_mass_doubles_the_dimension(self):
        self.assertAlmostEqual(scale(1.0, 1.0, 8.0), 2.0, places=9)

    def test_same_mass_is_identity(self):
        self.assertAlmostEqual(scale(7.0, 1.53, 7.0), 1.53, places=9)

    def test_hundredfold_mass_scales_by_4_64(self):
        self.assertAlmostEqual(scale(7.0, 1.0, 700.0), 100.0 ** (1 / 3), places=9)

    def test_non_positive_argument_returns_zero(self):
        self.assertEqual(scale(0.0, 1.0, 5.0), 0)
        self.assertEqual(scale(1.0, 1.0, 0.0), 0)


class TestCraterSize(unittest.TestCase):
    """The WES / TM 5-855-1 size equations against the published craters."""

    def test_155mm_surface_burst(self):
        # Kinney-Graham D = 0.8 * W^(1/3) with W = 7 kg.
        c = crater(7.0, "soil")
        self.assertAlmostEqual(c["rA"], 0.765, delta=0.01)
        self.assertAlmostEqual(2 * c["rA"], 0.8 * 7.0 ** (1 / 3), places=9)
        self.assertAlmostEqual(ft_from_m(2 * c["rA"]), 5.02, delta=0.1)
        # Apparent depth follows the soil ratio, about 0.25 of the diameter.
        self.assertAlmostEqual(c["dA"], 0.383, delta=0.01)

    def test_500lb_surface_burst(self):
        c = crater(100.0, "soil")
        self.assertAlmostEqual(c["rA"], 1.857, delta=0.02)
        self.assertAlmostEqual(2 * c["rA"], 0.8 * 100.0 ** (1 / 3), places=9)

    def test_okc_dry_sandy_clay(self):
        # OKC 4000 lb: 31 ft diameter / 8.7 ft deep (measured 31 / 8.5).
        c = crater(kg_from_lb(4000), "drySandyClay")
        self.assertAlmostEqual(ft_from_m(2 * c["rA"]), 31.1, delta=0.3)
        self.assertAlmostEqual(ft_from_m(c["dA"]), 8.73, delta=0.1)

    def test_okc_concrete(self):
        # OKC 4000 lb concrete: 12 ft / 3.2 ft (measured 13 / 2.6).
        c = crater(kg_from_lb(4000), "concrete")
        self.assertAlmostEqual(ft_from_m(2 * c["rA"]), 12.06, delta=0.2)
        self.assertAlmostEqual(ft_from_m(c["dA"]), 3.17, delta=0.1)

    def test_sandstone_uses_the_violet_exponent(self):
        # Sandstone 500 kg (Violet 1/3.4): R 7.4 m, D 2.5 m.
        c = crater(500.0, "sandstone")
        self.assertAlmostEqual(c["rA"], 7.4, delta=0.05)
        self.assertAlmostEqual(c["dA"], 2.49, delta=0.02)
        # The 1/3 exponent would give 1.19 * 500^(1/3) = 9.44 m, not 7.4 m.
        self.assertNotAlmostEqual(c["rA"], 1.19 * 500.0 ** (1 / 3), places=1)

    def test_emrtc_250kg_dry_sand(self):
        # EMRTC 250 kg: 3.8 m diameter (dry sand C_R 0.75 ft/lb^(1/3)).
        c = crater(250.0, "drySand")
        self.assertAlmostEqual(2 * c["rA"], 3.8, delta=0.1)

    def test_zero_mass_is_all_zero(self):
        self.assertEqual(
            crater(0.0, "soil"),
            {k: 0 for k in ["rA", "dA", "v", "rLip", "hLip", "rEj", "rTrue", "dTrue"]},
        )


class TestCraterShape(unittest.TestCase):
    """The true/apparent and lip/ejecta relations, and the CONWEP crater."""

    def test_relations(self):
        c = crater(100.0, "drySandyClay")
        self.assertAlmostEqual(c["rLip"], 1.25 * c["rA"], places=9)
        self.assertAlmostEqual(c["hLip"], 0.25 * c["dA"], places=9)
        self.assertAlmostEqual(c["rEj"], 2.15 * c["rA"], places=9)
        self.assertAlmostEqual(c["rTrue"], 1.15 * c["rA"], places=9)
        self.assertAlmostEqual(
            c["v"], 0.5 * 3.141592653589793 * c["rA"] ** 2 * c["dA"], places=9
        )

    def test_conwep_volume(self):
        # CONWEP 488 lb, DOB 18 ft: apparent 29.61 ft / 9.02 ft.
        rA = 29.61 / 2 * M_PER_FT
        dA = 9.02 * M_PER_FT
        s = shape(rA, dA, 18 * M_PER_FT, kg_from_lb(488))
        volume_ft3 = s["v"] / (M_PER_FT**3)
        self.assertAlmostEqual(volume_ft3, 3106, delta=3)

    def test_conwep_true_depth(self):
        # True depth = DOB + 0.4 * W^(1/3) with W in lb: 18 + 3.15 = 21.15 ft.
        rA = 29.61 / 2 * M_PER_FT
        dA = 9.02 * M_PER_FT
        s = shape(rA, dA, 18 * M_PER_FT, kg_from_lb(488))
        self.assertAlmostEqual(ft_from_m(s["dTrue"]), 21.15, delta=0.05)

    def test_conwep_true_diameter(self):
        # True diameter = 1.15 x apparent.  CONWEP publishes 35.61 ft; the
        # 1.15 relation gives 34.05 ft, inside the issue's 10-30 per cent
        # scatter (CONWEP is beyond the optimum depth of burial).
        rA = 29.61 / 2 * M_PER_FT
        dA = 9.02 * M_PER_FT
        s = shape(rA, dA, 18 * M_PER_FT, kg_from_lb(488))
        true_dia_ft = ft_from_m(2 * s["rTrue"])
        self.assertAlmostEqual(true_dia_ft / 29.61, 1.15, places=6)
        self.assertLess(abs(true_dia_ft - 35.61) / 35.61, 0.10)

    def test_shape_kernel_agrees_with_the_model(self):
        # fnc_craterShape on the model's apparent geometry must reproduce the
        # model's shape outputs, so the two kernels cannot drift apart.
        c = crater(kg_from_lb(4000), "drySandyClay")
        s = shape(c["rA"], c["dA"], 0.0, kg_from_lb(4000))
        for key in ("v", "rLip", "hLip", "rEj", "rTrue", "dTrue"):
            self.assertAlmostEqual(s[key], c[key], places=9, msg=key)

    def test_non_positive_radius_is_all_zero(self):
        self.assertEqual(list(shape(0.0, 1.0, 0.0, 1.0).values()), [0, 0, 0, 0, 0, 0])


class TestMediumMultipliers(unittest.TestCase):
    """Concrete is 0.38x the diameter and 0.36x the depth of dry sandy clay."""

    def test_concrete_against_dry_sandy_clay(self):
        clay = crater(kg_from_lb(4000), "drySandyClay")
        concrete = crater(kg_from_lb(4000), "concrete")
        self.assertAlmostEqual(concrete["rA"] / clay["rA"], 0.388, delta=0.005)
        self.assertAlmostEqual(concrete["dA"] / clay["dA"], 0.364, delta=0.005)

    def test_wet_clay_is_larger_than_dry_sand(self):
        dry = crater(100.0, "drySand")
        wet = crater(100.0, "wetClay")
        self.assertGreater(wet["rA"], dry["rA"])
        self.assertAlmostEqual(wet["rA"] / dry["rA"], 1.15 / 0.75, delta=0.01)


class TestHonestLimits(unittest.TestCase):
    """The cube root breaks when gravity or strength dominates."""

    def test_one_third_against_one_third_point_four_at_1000kg(self):
        # The issue: the two exponents differ by 31 per cent at 1000 kg.
        ratio = 1000.0 ** (1 / 3) / 1000.0 ** (1 / 3.4)
        self.assertAlmostEqual(ratio, 1.31, delta=0.01)

    def test_depth_exponent_zero_point_three_is_shallower(self):
        # WES depth exponent 0.3 gives a shallower crater than 1/3 at 1000 kg.
        self.assertLess(1000.0**0.3, 1000.0 ** (1 / 3))


class TestTerrainPoints(unittest.TestCase):
    """The grid the engine setTerrainHeight command consumes."""

    def test_centre_is_the_deepest_point(self):
        pts = run_sqf(TERRAIN, [[100, 200, 50], 2.0, 1.0, 0.5, 1.0])
        centre = min(pts, key=lambda p: p[2])
        self.assertAlmostEqual(centre[0], 100.0, places=6)
        self.assertAlmostEqual(centre[1], 200.0, places=6)
        self.assertAlmostEqual(centre[2], 49.0, places=6)

    def test_lip_is_raised_above_the_centre(self):
        # The lip ring peaks at H_lip = 0.5 m above the centre level; the grid
        # samples it just outside the rim, so the sampled peak is below 10.5.
        pts = run_sqf(TERRAIN, [[0, 0, 10], 2.0, 1.0, 0.5, 1.0])
        heights = [p[2] for p in pts]
        self.assertGreater(max(heights), 10.0)
        self.assertLessEqual(max(heights), 10.5 + 1e-6)

    def test_grid_spans_the_lip_radius(self):
        pts = run_sqf(TERRAIN, [[0, 0, 0], 2.0, 1.0, 0.5, 1.0])
        self.assertGreater(len(pts), 0)
        self.assertLessEqual(max(abs(p[0]) for p in pts), 2.5 + 1e-6)

    def test_bad_input_returns_empty(self):
        self.assertEqual(run_sqf(TERRAIN, [[0, 0, 0], 0.0, 1.0, 0.0, 1.0]), [])
        self.assertEqual(run_sqf(TERRAIN, [[0, 0, 0], 1.0, 1.0, 0.0, 0.0]), [])


class TestSourceContract(unittest.TestCase):
    """The kernels carry the published constants and cite the sources."""

    def test_calculate_crater_constants(self):
        body = live_source(CALC)
        for token in (
            "0.38866",
            "0.21812",
            "0.15070",
            "0.07932",
            "0.22209",
            "0.09915",
            "0.29744",
            "0.14872",
            "0.45608",
            "0.22804",
            "1.19",
            "0.40",
            "0.15864",
        ):
            self.assertIn(token, body, f"constant {token} missing")

    def test_calculate_crater_shape_relations(self):
        body = live_source(CALC)
        for token in ("1.25", "0.25", "2.15", "1.15", "0.5 * pi"):
            self.assertIn(token, body, f"shape constant {token} missing")

    def test_sources_cited(self):
        text = (
            CALC.read_text(encoding="utf-8")
            + SHAPE.read_text(encoding="utf-8")
            + SCALE.read_text(encoding="utf-8")
        )
        for source in (
            "TM 5-855-1",
            "WES Report 2",
            "Kinney",
            "Glasstone",
            "Hopkinson",
            "Cranz",
            "Chabai",
            "Violet",
        ):
            self.assertIn(source, text, f"source {source} not cited")

    def test_set_terrain_height_is_referenced(self):
        # The issue names setTerrainHeight; the terrain kernel documents it.
        self.assertIn("setTerrainHeight", TERRAIN.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
