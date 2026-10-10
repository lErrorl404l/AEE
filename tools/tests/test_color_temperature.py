#!/usr/bin/env python3
"""Physics colour temperature and atmospheric grade (issue #100).

The pure kernels run here from their real SQF through tools/tests/sqf_lite.py.
The engine-touching driver and the wiring are source-contracted.

Every constant is traced to a published source or marked UNSOURCED beside the
value in the SQF header:

  fnc_perceptionColorTemperature    Kasten and Young 1989 air mass
                                    (Applied Optics 28(22):4735-4738) plus
                                    CIE 15:2004 daylight anchors.
  fnc_perceptionIlluminantFromCct   CIE 15:2004 daylight locus and the Kim
                                    et al. 2002 Planckian cubic
                                    (J. Korean Phys. Soc. 41(6):865-871),
                                    then the IEC 61966-2-1 Rec.709 matrix.
  fnc_perceptionAtmosphericColor    coverage-union desaturation (UNSOURCED
                                    form and cap).

The issue cites the Tanner Helland 2012 approximation; this kernel uses the
CIE loci instead, because the loci are the standard the approximation fits and
are citable by identity.  The unit test therefore checks the CIE locus output,
not the Helland table.

Run: python3 -m unittest tools.tests.test_color_temperature -v
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
VISION = ROOT / "addons" / "vision"
PERCEPTION = VISION / "functions" / "perception"
GRADE = VISION / "functions" / "grade"

CT_KERNEL = PERCEPTION / "fnc_perceptionColorTemperature.sqf"
CCT_KERNEL = PERCEPTION / "fnc_perceptionIlluminantFromCct.sqf"
ATMOS_KERNEL = PERCEPTION / "fnc_perceptionAtmosphericColor.sqf"
COMPOSE_KERNEL = PERCEPTION / "fnc_perceptionParams.sqf"
DRIVER = GRADE / "fnc_applyBaseGrade.sqf"
PREP = VISION / "XEH_PREP.hpp"

# Rec.709 luma weights (ITU-R BT.709-6), the desaturation target.
REC709_WEIGHTS = [0.2126, 0.7152, 0.0722, 0]


def cct(sun_elevation: float, overcast: float) -> float:
    return run_sqf(CT_KERNEL, [sun_elevation, overcast])


def white_point(kelvin: float) -> list[float]:
    return run_sqf(CCT_KERNEL, [kelvin])


def atmos(overcast: float, rain: float, haze: float, cap: float | None = None) -> float:
    args = [overcast, rain, haze]
    if cap is not None:
        args.append(cap)
    return run_sqf(ATMOS_KERNEL, args)


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
    """fnc_perceptionColorTemperature maps the atmospheric state to kelvin."""

    def test_clear_high_sun_is_near_d55(self):
        # Air mass near 1.4 at 45 degrees -> D55 (5503 K) pulled slightly warm.
        value = cct(45, 0)
        self.assertGreater(value, 5000)
        self.assertLess(value, 5800)

    def test_clear_low_sun_is_warm(self):
        # At the horizon the air mass is about 38 -> the blackbody anchor.
        value = cct(0, 0)
        self.assertGreaterEqual(value, 1900)
        self.assertLessEqual(value, 2800)

    def test_full_overcast_is_d65(self):
        # Overcast 1 makes the sky term take the whole weight: D65, 6504 K.
        self.assertAlmostEqual(cct(45, 1), 6504, places=1)

    def test_clear_sky_below_horizon_is_high_cct(self):
        # Civil twilight and below: the sky term takes the whole weight, so the
        # clear-sky anchor (10000 K) is returned.
        self.assertAlmostEqual(cct(-10, 0), 10000, places=1)

    def test_rising_sun_raises_the_cct_when_clear(self):
        rising = [cct(e, 0) for e in (0, 20, 45, 80)]
        self.assertEqual(rising, sorted(rising), "CCT did not rise with the sun")

    def test_output_stays_in_the_sourced_band(self):
        for elev in (-90, -6, 0, 45, 90):
            for ov in (0, 0.5, 1, 2):
                with self.subTest(elev=elev, overcast=ov):
                    value = cct(elev, ov)
                    self.assertGreaterEqual(value, 2000)
                    self.assertLessEqual(value, 25000)

    def test_malformed_inputs_fall_back(self):
        self.assertEqual(cct("x", "y"), cct(0, 0))


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


class TestAtmosphericColor(unittest.TestCase):
    """fnc_perceptionAtmosphericColor returns a bounded desaturation alpha."""

    def test_clear_is_the_identity(self):
        self.assertEqual(atmos(0, 0, 0), 0)

    def test_full_overcast_reaches_the_cap(self):
        self.assertAlmostEqual(atmos(1, 0, 0), 0.4, places=9)

    def test_rain_alone_scales_the_cap(self):
        self.assertAlmostEqual(atmos(0, 0.5, 0), 0.2, places=9)

    def test_rising_overcast_raises_the_alpha(self):
        rising = [atmos(o, 0, 0) for o in (0, 0.25, 0.5, 0.75, 1)]
        self.assertEqual(rising, sorted(rising))

    def test_cap_is_clamped_to_half(self):
        self.assertAlmostEqual(atmos(1, 1, 1, 0.9), 0.5, places=9)

    def test_negative_inputs_are_clamped(self):
        self.assertEqual(atmos(-1, -1, -1), 0)


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
        for kernel in (CT_KERNEL, CCT_KERNEL, ATMOS_KERNEL):
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
            "perceptionAtmosphericColor",
        ):
            with self.subTest(name=name):
                self.assertIn(f"PREPS(perception,{name})", source)

    def test_driver_calls_the_new_kernels(self):
        live = live_source(DRIVER)
        self.assertIn("FUNC(perceptionColorTemperature)", live)
        self.assertIn("FUNC(perceptionIlluminantFromCct)", live)
        self.assertIn("FUNC(perceptionAtmosphericColor)", live)
        # The CCT supersedes the engine ambient only when the setting is on.
        self.assertIn("QGVAR(colorTemperature)", live)

    def test_header_carries_the_sources(self):
        self.assertIn("Kasten and Young 1989", CT_KERNEL.read_text(encoding="utf-8"))
        cct_text = CCT_KERNEL.read_text(encoding="utf-8")
        self.assertIn("Kim et al. 2002", cct_text)
        self.assertIn("CIE 15:2004", cct_text)


if __name__ == "__main__":
    unittest.main()
