#!/usr/bin/env python3
"""RUSLE erosion and sediment transport checks (issue #21).

The kernels are EXECUTED, not mirrored: each SQF file is run through the
sqf_lite harness and held to the published value. The issue's vectors are
reproduced here, with one correction recorded: the issue text gives
e(25 mm/h) = 0.226, but the Brown and Foster (1987) form adopted in USDA
AH-703 gives 0.2302. The kernel follows the published form.

Sources: Wischmeier and Smith (1978) USDA AH-537; Renard et al. (1997)
USDA AH-703; Brown and Foster (1987); McCool et al. (1987, 1989); Wall et
al. (1997) OMAFRA 23-005; Williams (1975) MUSLE.

Run: python3 -m unittest tools.tests.test_erosion -v
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
EROSION = REPO / "addons" / "hydrology" / "functions" / "erosion"
DRIVER = REPO / "addons" / "hydrology" / "functions" / "fnc_calculateErosion.sqf"
PREP = REPO / "addons" / "hydrology" / "XEH_PREP.hpp"
CORE = REPO / "addons" / "core" / "functions" / "fnc_updateEnvironment.sqf"


def kernel(name, *args):
    return run_sqf(EROSION / f"fnc_{name}.sqf", list(args))


class TestKineticEnergy(unittest.TestCase):
    def test_brown_foster_at_25(self):
        """Brown and Foster (1987), AH-703: e(25) = 0.2302 MJ/ha/mm.

        The issue text states 0.226; that value is not reproducible from the
        published form. The kernel returns the published value.
        """
        self.assertAlmostEqual(kernel("calculateKineticEnergy", 25), 0.23018, places=4)

    def test_wischmeier_form_at_25(self):
        """AH-537 logarithmic form: 0.119 + 0.0873 log10(25) = 0.2410."""
        self.assertAlmostEqual(
            kernel("calculateKineticEnergy", 25, "wischmeier"), 0.24104, places=4
        )

    def test_wischmeier_caps_at_76(self):
        """Above 76 mm/h the AH-537 form is the constant 0.283."""
        self.assertAlmostEqual(
            kernel("calculateKineticEnergy", 100, "wischmeier"), 0.283, places=4
        )

    def test_zero_intensity_is_zero_energy(self):
        self.assertEqual(kernel("calculateKineticEnergy", 0), 0)

    def test_energy_rises_with_intensity(self):
        self.assertLess(
            kernel("calculateKineticEnergy", 5), kernel("calculateKineticEnergy", 50)
        )


class TestErosivityIndex(unittest.TestCase):
    def test_issue_vector(self):
        """#21: EI30 = 500 for E=1000 MJ/ha, I30=50 mm/h."""
        self.assertAlmostEqual(
            kernel("calculateErosivityIndex", 1000, 50), 500.0, places=4
        )

    def test_a_storm_with_no_rain_is_zero(self):
        self.assertEqual(kernel("calculateErosivityIndex", 0, 0), 0)


class TestSoilErodibility(unittest.TestCase):
    def test_omafra_texture_values(self):
        """Wall et al. (1997) OMAFRA 23-005 Table 2, average organic matter."""
        expected = {
            "clay": 0.22,
            "clay loam": 0.30,
            "loam": 0.30,
            "silt loam": 0.38,
            "silty clay": 0.26,
            "silty clay loam": 0.32,
            "sandy loam": 0.13,
            "loamy sand": 0.04,
            "sand": 0.02,
            "fine sandy loam": 0.18,
            "very fine sand": 0.43,
            "heavy clay": 0.17,
        }
        for texture, k in expected.items():
            with self.subTest(texture=texture):
                self.assertAlmostEqual(
                    kernel("calculateSoilErodibility", texture), k, places=4
                )

    def test_case_insensitive(self):
        self.assertEqual(
            kernel("calculateSoilErodibility", "SILT LOAM"),
            kernel("calculateSoilErodibility", "silt loam"),
        )

    def test_unknown_texture_defaults_to_loam(self):
        self.assertEqual(kernel("calculateSoilErodibility", "unobtainium"), 0.30)


class TestSlopeLengthGradient(unittest.TestCase):
    def test_issue_vector(self):
        """#21: 10 percent slope, 50 m -> LS = 1.79."""
        self.assertAlmostEqual(
            kernel("calculateSlopeLengthGradient", 0.10, 50), 1.7871, places=3
        )

    def test_unit_plot_is_unity(self):
        """The unit plot (22.13 m, 9 percent) has LS = 1 by definition."""
        self.assertAlmostEqual(
            kernel("calculateSlopeLengthGradient", 0.09, 22.13), 1.0, delta=0.01
        )

    def test_flat_ground_has_no_slope_effect(self):
        """A flat cell keeps only the residual S = 0.03 at zero slope."""
        self.assertAlmostEqual(
            kernel("calculateSlopeLengthGradient", 0.0, 50), 0.03, places=4
        )

    def test_steeper_loses_more(self):
        self.assertLess(
            kernel("calculateSlopeLengthGradient", 0.10, 50),
            kernel("calculateSlopeLengthGradient", 0.30, 50),
        )


class TestCoverFactor(unittest.TestCase):
    def test_representative_values(self):
        expected = {
            "bare": 1.0,
            "crop": 0.36,
            "notill": 0.10,
            "pasture": 0.003,
            "forest": 0.001,
            "forestopen": 0.006,
        }
        for cls, c in expected.items():
            with self.subTest(cls=cls):
                self.assertAlmostEqual(kernel("calculateCoverFactor", cls), c, places=5)

    def test_forest_sheds_less_than_bare(self):
        self.assertLess(
            kernel("calculateCoverFactor", "forest"),
            kernel("calculateCoverFactor", "bare"),
        )


class TestSoilLoss(unittest.TestCase):
    def test_issue_vector(self):
        """#21: unit plot R=180, K=0.32 -> A = 57.6 t/ha/yr."""
        self.assertAlmostEqual(
            kernel("calculateSoilLoss", 180, 0.32, 1, 1, 1), 57.6, places=3
        )

    def test_product_of_factors(self):
        self.assertAlmostEqual(
            kernel("calculateSoilLoss", 500, 0.38, 1.79, 0.36, 1),
            500 * 0.38 * 1.79 * 0.36,
            places=3,
        )


class TestSedimentYield(unittest.TestCase):
    def test_musle_form(self):
        """Williams (1975): Sed = 11.8 (Q qp)^0.56 K LS C P."""
        q, qp, k, ls, c, p = 1000, 2, 0.30, 1.79, 0.36, 1
        expected = 11.8 * (q * qp) ** 0.56 * k * ls * c * p
        self.assertAlmostEqual(
            kernel("calculateSedimentYield", q, qp, k, ls, c, p), expected, places=4
        )

    def test_no_runoff_no_sediment(self):
        self.assertEqual(kernel("calculateSedimentYield", 0, 0, 0.3, 1.8, 0.4, 1), 0)


class TestSedimentDeposition(unittest.TestCase):
    def test_break_retains_the_stated_fraction(self):
        """A downslope gradient under half the upslope is a break."""
        self.assertEqual(kernel("calculateSedimentDeposition", 0.10, 0.02), 0.5)

    def test_continuous_slope_transports(self):
        self.assertEqual(kernel("calculateSedimentDeposition", 0.10, 0.08), 0)

    def test_gentle_ground_is_a_break(self):
        """A downslope gradient under 2 percent deposits."""
        self.assertEqual(kernel("calculateSedimentDeposition", 0.01, 0.015), 0.5)


class TestErosionDepth(unittest.TestCase):
    def test_issue_vector(self):
        """#21: 10 t/ha/yr at BD 1.3 g/cm3 -> 0.77 mm/yr."""
        self.assertAlmostEqual(
            kernel("calculateErosionDepth", 10, 1.3), 0.7692, places=3
        )

    def test_unit_plot_lowering(self):
        """#21: the unit-plot loss 57.6 t/ha/yr -> 4.4 mm/yr."""
        self.assertAlmostEqual(
            kernel("calculateErosionDepth", 57.6, 1.3), 4.43, places=2
        )


class TestDriverWiring(unittest.TestCase):
    """Source contract: the driver reuses the existing chain and publishes."""

    def setUp(self):
        self.src = DRIVER.read_text(encoding="utf-8")

    def test_driver_calls_every_kernel(self):
        for fn in (
            "calculateSoilErodibility",
            "calculateSlopeLengthGradient",
            "calculateCoverFactor",
            "calculateKineticEnergy",
            "calculateErosivityIndex",
            "calculateSoilLoss",
            "calculateSedimentYield",
            "calculateSedimentDeposition",
            "calculateErosionDepth",
        ):
            with self.subTest(kernel=fn):
                self.assertIn(f"FUNC({fn})", self.src)

    def test_driver_reuses_the_existing_d8_and_runoff_chain(self):
        self.assertIn("FUNC(routeRunoffD8)", self.src)
        self.assertIn("QGVAR(stormDepth_mm)", self.src)
        self.assertIn("QGVAR(runoffCumulative_mm)", self.src)
        self.assertIn("EFUNC(material,classifyBySurfaceType)", self.src)

    def test_driver_publishes_the_state(self):
        for var in (
            "erosionRate_thaYr",
            "erosionDepth_mmYr",
            "erosivityR",
            "sedimentYield_t",
            "erosionRisk",
            "erosionDepositedFraction",
        ):
            with self.subTest(var=var):
                self.assertIn(f"QGVAR({var})", self.src)

    def test_driver_records_the_terrain_ceiling(self):
        """The engine cannot lower terrain at the model's rates."""
        self.assertIn("CEILING", self.src)
        self.assertIn("setTerrainHeight", self.src)

    def test_prep_registers_the_driver_and_kernels(self):
        prep = PREP.read_text(encoding="utf-8")
        self.assertIn("PREP(calculateErosion);", prep)
        for fn in (
            "calculateKineticEnergy",
            "calculateErosivityIndex",
            "calculateSoilErodibility",
            "calculateSlopeLengthGradient",
            "calculateCoverFactor",
            "calculateSoilLoss",
            "calculateSedimentYield",
            "calculateSedimentDeposition",
            "calculateErosionDepth",
        ):
            with self.subTest(kernel=fn):
                self.assertIn(f"PREPS(erosion,{fn});", prep)

    def test_core_runs_erosion_after_the_river_chain(self):
        core = CORE.read_text(encoding="utf-8")
        river = core.index("EFUNC(hydrology,calculateRiverWaterLevel)")
        erosion = core.index("EFUNC(hydrology,calculateErosion)")
        self.assertLess(river, erosion, "erosion must run after the river chain")


if __name__ == "__main__":
    unittest.main()
