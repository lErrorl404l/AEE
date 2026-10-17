#!/usr/bin/env python3
"""Physics colour temperature and atmospheric grade (issue #100).

The pure kernels run here from their real SQF through tools/tests/sqf_lite.py.
The engine-touching driver and the wiring are source-contracted.

Every constant is traced to a published source or marked UNSOURCED beside the
value in the SQF header:

  fnc_perceptionColorTemperature    Bird & Riordan 1986 SPCTRAL2 spectra x
                                    CIE 1931 CMFs (tools/gen_daylight.py),
                                    Kasten & Czeplak 1980 cloud mixing.
  fnc_perceptionIlluminantFromCct   CIE 15:2004 daylight locus and the Kim
                                    et al. 2002 Planckian cubic
                                    (J. Korean Phys. Soc. 41(6):865-871),
                                    then the IEC 61966-2-1 Rec.709 matrix.

The issue cites the Tanner Helland 2012 approximation; this kernel uses the
CIE loci instead, because the loci are the standard the approximation fits and
are citable by identity.  The unit test therefore checks the CIE locus output,
not the Helland table.

Run: python3 -m unittest tools.tests.test_color_temperature -v
"""

from __future__ import annotations

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import gen_daylight  # noqa: E402
VISION = ROOT / "addons" / "vision"
PERCEPTION = VISION / "functions" / "perception"
GRADE = VISION / "functions" / "grade"

CT_KERNEL = PERCEPTION / "fnc_perceptionColorTemperature.sqf"
CCT_KERNEL = PERCEPTION / "fnc_perceptionIlluminantFromCct.sqf"
COMPOSE_KERNEL = PERCEPTION / "fnc_perceptionParams.sqf"
DRIVER = GRADE / "fnc_applyBaseGrade.sqf"
PREP = VISION / "XEH_PREP.hpp"

TABLE = PERCEPTION / "fnc_daylightTable.sqf"
_TABLE = run_sqf(TABLE, [])
DAYLIGHT_GLOBALS = {"__FUNC__daylightTable": lambda: _TABLE}

# Rec.709 luma weights (ITU-R BT.709-6), the desaturation target.
REC709_WEIGHTS = [0.2126, 0.7152, 0.0722, 0]


def cct(sun_elevation: float, overcast: float, haze: float = 0.08, pressure: float = 1013.25):
    return run_sqf(CT_KERNEL, [sun_elevation, overcast, haze, pressure], DAYLIGHT_GLOBALS)


def white_point(kelvin: float) -> list[float]:
    return run_sqf(CCT_KERNEL, [kelvin])


def compose(args: list) -> tuple:
    """Run fnc_perceptionParams with its sub-kernels bound (the same registry
    the composition kernel calls through FUNC)."""
    globals_ = {
        "__FUNC__perceptionToneResponse": lambda *a: run_sqf(
            PERCEPTION / "fnc_perceptionToneResponse.sqf", list(a)
        ),
        "__FUNC__perceptionIlluminant": lambda *a: run_sqf(
            PERCEPTION / "fnc_perceptionIlluminant.sqf", list(a)
        ),
        "__FUNC__perceptionChromaticAdaptation": lambda *a: run_sqf(
            PERCEPTION / "fnc_perceptionChromaticAdaptation.sqf", list(a)
        ),
        "__FUNC__perceptionMesopicColor": lambda *a: run_sqf(
            PERCEPTION / "fnc_perceptionMesopicColor.sqf", list(a)
        ),
        "__FUNC__perceptionBaseGrade": lambda *a: run_sqf(
            PERCEPTION / "fnc_perceptionBaseGrade.sqf", list(a)
        ),
    }
    return tuple(run_sqf(COMPOSE_KERNEL, args, globals_))


def live_source(path: Path) -> str:
    """Source with // and /* */ comments stripped, so a commented-out line is
    invisible to the contract assertions and the purity scan."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return "\n".join(line.split("//")[0] for line in text.splitlines())


class TestColorTemperature(unittest.TestCase):
    """fnc_perceptionColorTemperature: SPCTRAL2 daylight mixed with cloud."""

    @classmethod
    def setUpClass(cls):
        cls.c, cls.cmf = gen_daylight.load()

    def exact(self, elev, aod500, p=1013.25):
        """Clear-sky global chromaticity and CCT straight from the model."""
        dni, dhi = gen_daylight.spectrl2(self.c, elev, aod500, p)
        cz = math.sin(math.radians(elev))
        b = gen_daylight.tristimulus(self.c, self.cmf, [v * cz for v in dni])
        s = gen_daylight.tristimulus(self.c, self.cmf, dhi)
        g = [b[i] + s[i] for i in range(3)]
        x, y = g[0] / sum(g), g[1] / sum(g)
        return x, y, gen_daylight.cct(self.cmf, x, y)

    @staticmethod
    def haze_for(aod500):
        return aod500 / ((500 / 550) ** -1.14) / 1.2 + 0.0116

    def test_table_is_fresh(self):
        self.assertEqual(gen_daylight.main(["--check"]), 0)

    def test_clear_sky_on_the_grid_matches_the_spectral_model(self):
        # On-grid and off-grid points (interpolated between bands).
        for elev in (5, 11, 21.5, 50, 77):
            for aod in (0.05, 0.13, 0.2, 0.5):
                with self.subTest(elev=elev, aod=aod):
                    x, y, k, _sp = cct(elev, 0, self.haze_for(aod))
                    ex, ey, ek = self.exact(elev, aod)
                    self.assertAlmostEqual(x, ex, delta=5e-4)
                    self.assertAlmostEqual(y, ey, delta=5e-4)
                    self.assertAlmostEqual(k, ek, delta=0.01 * ek)

    def test_midday_clear_daylight_is_5500_to_6000_k(self):
        # Measured clear-sky global daylight at high sun: ~5500-6000 K
        # (Hernandez-Andres et al. 2001, JOSA A 18:1325).
        self.assertTrue(5500 < cct(50, 0, 0.08)[2] < 6000)

    def test_low_sun_turns_the_light_blue_as_the_sky_dominates(self):
        self.assertGreater(cct(3, 0, 0.08)[2], cct(20, 0, 0.08)[2])

    def test_overcast_light_is_the_neutral_global_light(self):
        # N = 1: no beam; cloud-diffuse light has the clear global colour.
        x, y, k, _sp = cct(40, 1, 0.08)
        aod = (0.08 - 0.0116) * 1.2 * (500 / 550) ** -1.14
        ex, ey, ek = self.exact(40, aod)
        self.assertAlmostEqual(x, ex, delta=5e-4)
        self.assertAlmostEqual(y, ey, delta=5e-4)

    def test_beam_only_is_warm(self):
        # A 0.5 deg sun's beam is red; the mixture is bluer than the beam.
        _x, _y, k, _sp = cct(0.5, 0, 0.05)
        self.assertGreater(k, 3000)

    def test_cct_formulas_match_the_definition(self):
        for xy in ((0.31271, 0.32902), (0.44757, 0.40745), (0.29, 0.30), (0.40, 0.39)):
            exact = gen_daylight.cct(self.cmf, *xy)
            nm = (xy[0] - 0.3320) / (0.1858 - xy[1])
            k = 449 * nm ** 3 + 3525 * nm ** 2 + 6823.3 * nm + 5520.33
            if k >= 3000:
                nh = (xy[0] - 0.3366) / (xy[1] - 0.1735)
                k = -949.86315 + 6253.80338 * math.exp(-nh / 0.92159) \
                    + 28.70599 * math.exp(-nh / 0.20039) + 0.00004 * math.exp(-nh / 0.07125)
            self.assertAlmostEqual(k, exact, delta=0.01 * exact, msg=xy)

    def test_daylight_sp_ratio(self):
        # Clear daylight S/P ~2.3-2.5 (CIE D65 is 2.47); the scotopic
        # integral is the CIE 1951 V'(lambda).
        for elev in (10, 30, 60):
            self.assertTrue(2.2 < cct(elev, 0, 0.08)[3] < 2.6)

    def test_pressure_reduces_rayleigh(self):
        # Thinner air: less blue sky, so a warmer total at low sun.
        self.assertLess(cct(5, 0, 0.08, 700)[2], cct(5, 0, 0.08, 1013.25)[2])


class TestIlluminantFromCct(unittest.TestCase):
    """fnc_perceptionIlluminantFromCct returns the linear Rec.709 white point."""

    def test_d65_is_the_unit_neutral(self):
        # The CIE daylight locus at 6504 K is D65, whose Rec.709 white point is
        # [1, 1, 1].
        r, g, b = white_point(6504)
        for channel in (r, g, b):
            self.assertAlmostEqual(channel, 1.0, places=2)

    def test_warm_temperature_is_red_dominant(self):
        r, g, b = white_point(2000)
        self.assertGreater(r, g)
        self.assertGreater(g, b)

    def test_cool_temperature_is_blue_dominant(self):
        r, _g, b = white_point(10000)
        self.assertGreater(b, r)

    def test_every_channel_is_non_negative(self):
        for kelvin in (1667, 2000, 2700, 4000, 5500, 6504, 10000, 25000):
            for channel in white_point(kelvin):
                self.assertGreaterEqual(channel, 0)

    def test_determinism(self):
        self.assertEqual(white_point(4200), white_point(4200))

    def test_malformed_input_falls_back_to_d65(self):
        self.assertEqual(white_point("x"), white_point(6504))


class TestComposeWithPhysicsInputs(unittest.TestCase):
    """fnc_perceptionParams folds the atmospheric alpha and the grain scale."""

    # 12-arg default (the pre-#100 call) plus the two new trailing inputs.
    BASE = [1, 1, [1, 1, 1], True, False, 0.25, 1, 0.9, 0, 0, [1, 1, 0], 0]

    def test_default_call_is_unchanged(self):
        cc, grain = compose(self.BASE)
        self.assertEqual(cc[4], [1, 1, 1, 1], "the default colour stage desaturates")
        self.assertEqual(cc[5], [0, 0, 0, 0])
        self.assertAlmostEqual(grain[0], 0.006, places=9)

    def test_atmospheric_alpha_desaturates(self):
        cc, _ = compose(self.BASE + [0.3, 1])
        self.assertEqual(
            cc[4], [1, 1, 1, 0.7], "atmospheric desaturation did not apply"
        )
        self.assertEqual(cc[5], REC709_WEIGHTS)

    def test_grain_scale_multiplies_the_intensity(self):
        _cc, grain = compose(self.BASE + [0, 3])
        self.assertAlmostEqual(grain[0], 0.018, places=9)

    def test_grain_intensity_stays_in_the_engine_range(self):
        _cc, grain = compose(self.BASE + [0, 100])
        self.assertLessEqual(grain[0], 0.05)

    def test_determinism(self):
        args = self.BASE + [0.3, 2]
        self.assertEqual(compose(args), compose(args))


class TestKernelPurity(unittest.TestCase):
    def test_kernels_are_pure(self):
        for kernel in (CT_KERNEL, CCT_KERNEL):
            text = live_source(kernel)
            for token in (
                "missionNamespace",
                "GVAR(",
                "EGVAR(",
                "getVariable",
                "setVariable",
            ):
                with self.subTest(kernel=kernel.name, token=token):
                    self.assertNotIn(token, text)


class TestWiring(unittest.TestCase):
    def test_preps_registered(self):
        source = PREP.read_text(encoding="utf-8")
        for name in (
            "perceptionColorTemperature",
            "perceptionIlluminantFromCct",
            "daylightTable",
        ):
            with self.subTest(name=name):
                self.assertIn(f"PREPS(perception,{name})", source)

    def test_driver_calls_the_new_kernels(self):
        live = live_source(DRIVER)
        self.assertIn("FUNC(perceptionColorTemperature)", live)
        self.assertIn("FUNC(perceptionIlluminantFromCct)", live)
        self.assertNotIn("perceptionAtmosphericColor", live)
        # The CCT supersedes the engine ambient only when the setting is on.
        self.assertIn("QGVAR(colorTemperature)", live)

    def test_header_carries_the_sources(self):
        ct_text = CT_KERNEL.read_text(encoding="utf-8")
        self.assertIn("Bird & Riordan 1986", ct_text)
        self.assertIn("Kasten & Czeplak 1980", ct_text)
        cct_text = CCT_KERNEL.read_text(encoding="utf-8")
        self.assertIn("Kim et al. 2002", cct_text)
        self.assertIn("CIE 15:2004", cct_text)


if __name__ == "__main__":
    unittest.main()
