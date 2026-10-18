#!/usr/bin/env python3
"""Star brightness and light-pollution kernels (aee-workshop-copy item 3).

The three kernels are pure: no missionNamespace, no GVAR/EGVAR, no engine
command.  These tests run the REAL SQF through the SQF lite interpreter and
cross-check it against a Python mirror of the same spec, so a constant change
in the SQF fails here until the mirror is re-synced.

Run: python3 -m unittest tools.tests.test_star_brightness -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))

from sqf_lite import run_sqf  # noqa: E402

ASTRONOMY = REPO / "addons" / "lighting" / "functions" / "astronomy"
FADE = ASTRONOMY / "fnc_starWeatherFade.sqf"
PENALTY = ASTRONOMY / "fnc_lightPollutionPenalty.sqf"
LIMIT = ASTRONOMY / "fnc_calculateLimitingMagnitude.sqf"
CATALOG = ASTRONOMY / "fnc_getStarCatalog.sqf"
MAGNITUDE = ASTRONOMY / "fnc_starMagnitude.sqf"
ENV_UPDATE = REPO / "addons" / "core" / "functions" / "fnc_updateEnvironment.sqf"


# ─── Python mirrors of the same spec, for cross-checking the SQF ────────────
def mirror_fade(value: float, overcast: float, fog: float) -> float:
    return value * (1 - max(0.0, min(1.0, overcast)))


def mirror_penalty(houses: float) -> float:
    h = max(houses, 0)
    penalty = 2.0 * (math.log10(1 + h) / math.log10(1 + 1000))
    return max(0.0, min(2.0, penalty))


def fade(value: float, overcast: float, fog: float) -> float:
    return run_sqf(FADE, [value, overcast, fog])


def penalty(houses: float) -> float:
    return run_sqf(PENALTY, [houses])


def live_source(path: Path) -> str:
    """Source with // and /* */ comments stripped, so a commented-out line
    is invisible to the contract assertions (the mutation proof)."""
    text = path.read_text(encoding="utf-8")
    text = __import__("re").sub(r"/\*.*?\*/", "", text, flags=__import__("re").DOTALL)
    return "\n".join(line.split("//")[0] for line in text.splitlines())


class TestStarWeatherFade(unittest.TestCase):
    def test_weather_fade_is_bounded(self) -> None:
        for value in (0.0, 0.5, 1.0, 100.0):
            for overcast in (0.0, 0.45, 0.5, 0.8, 1.0):
                for fog in (0.0, 0.35, 0.4, 0.7, 1.0):
                    with self.subTest(value=value, overcast=overcast, fog=fog):
                        got = fade(value, overcast, fog)
                        self.assertGreaterEqual(got, 0.0)
                        self.assertLessEqual(got, value)
                        self.assertAlmostEqual(
                            got, mirror_fade(value, overcast, fog), places=6
                        )

    def test_clear_sky_keeps_the_value(self) -> None:
        self.assertAlmostEqual(fade(10.0, 0.0, 0.7), 10.0, places=6)

    def test_overcast_is_the_cloud_fraction(self) -> None:
        self.assertAlmostEqual(fade(10.0, 0.3, 0.0), 7.0, places=5)
        self.assertAlmostEqual(fade(10.0, 1.0, 0.0), 0.0, places=6)


class TestLightPollutionPenalty(unittest.TestCase):
    """Albers & Duriscoe 2001: I = 11.3e6 p r^-2.5 nL, x2.5 at the centre."""

    def test_albers_duriscoe(self) -> None:
        for houses, hh in ((10, 2.4), (200, 4.8)):
            ref = 11300000 * houses * hh * 2500 ** -2.5 * 2.5 * 3.183e-6
            self.assertAlmostEqual(run_sqf(PENALTY, [houses, hh]), ref, places=12)

    def test_zero_and_negative_houses_add_nothing(self) -> None:
        self.assertEqual(run_sqf(PENALTY, [0, 2.4]), 0)
        self.assertEqual(run_sqf(PENALTY, [-5, 2.4]), 0)


class TestKernelPurity(unittest.TestCase):
    """The three kernels must not touch missionNamespace, GVAR or an engine
    command: they are pure functions of their arguments."""

    def test_kernels_are_pure(self) -> None:
        for kernel in (FADE, PENALTY):
            text = live_source(kernel)
            for token in (
                "missionNamespace",
                "GVAR(",
                "EGVAR(",
                "call FUNC",
                "getVariable",
            ):
                with self.subTest(kernel=kernel.name, token=token):
                    self.assertNotIn(token, text)

    def test_prep_entries_exist(self) -> None:
        prep = (REPO / "addons" / "lighting" / "XEH_PREP.hpp").read_text(
            encoding="utf-8"
        )
        for entry in (
            "PREPS(astronomy,starWeatherFade)",
            "PREPS(astronomy,lightPollutionPenalty)",
        ):
            with self.subTest(entry=entry):
                self.assertIn(entry, prep)



class TestNelmLinksToLightPollution(unittest.TestCase):
    """fnc_calculateLimitingMagnitude subtracts the light-pollution penalty."""

    @staticmethod
    def nelm(houses):
        g = {"__FUNC__lightPollutionPenalty": lambda *a: run_sqf(PENALTY, list(a))}
        return run_sqf(LIMIT, [-90, 0, 0, 0.08, houses, 2.4], g)[0]

    def test_nelm_falls_with_more_houses(self) -> None:
        self.assertIn("call FUNC(lightPollutionPenalty)", live_source(LIMIT))
        self.assertLess(self.nelm(100), self.nelm(0))

    def test_nelm_unchanged_at_zero_houses(self) -> None:
        self.assertAlmostEqual(penalty(0), 0.0, places=6)
        self.assertAlmostEqual(self.nelm(0) - self.nelm(0), 0.0, places=9)


class TestStarCatalogueWiring(unittest.TestCase):
    def test_star_catalogue_applies_the_brightness_coefficient(self) -> None:
        live = live_source(CATALOG)
        self.assertIn("call FUNC(starWeatherFade)", live)
        self.assertIn("GVAR(starBrightnessScale)", live)
        self.assertIn("GVAR(worldLighting)", live)
        self.assertIn("setVariable [QGVAR(starBrightnessCoefficient)", live)

    def test_renderers_pass_the_published_scale(self) -> None:
        for renderer in (
            ASTRONOMY / "fnc_drawFaintStars.sqf",
            ASTRONOMY / "fnc_starLightsSync.sqf",
        ):
            live = live_source(renderer)
            with self.subTest(renderer=renderer.name):
                self.assertIn("starBrightnessCoefficient", live)
                self.assertRegex(live, r"call FUNC\(starMagnitude\)")


class TestStarMagnitudeScale(unittest.TestCase):
    def test_scale_multiplies_alpha_and_clamps(self) -> None:
        base = run_sqf(MAGNITUDE, [2])[1]
        scaled = run_sqf(MAGNITUDE, [2, 0.5])[1]
        self.assertAlmostEqual(scaled, base * 0.5, places=6)
        self.assertAlmostEqual(run_sqf(MAGNITUDE, [-1.46, 100])[1], 1.0, places=6)
        self.assertAlmostEqual(run_sqf(MAGNITUDE, [0, 0])[1], 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
