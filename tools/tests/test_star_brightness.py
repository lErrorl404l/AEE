#!/usr/bin/env python3
"""Star brightness and light-pollution kernels (aee-workshop-copy item 3).

The three kernels are pure: no missionNamespace, no GVAR/EGVAR, no engine
command.  These tests run the REAL SQF through the SQF lite interpreter and
cross-check it against a Python mirror of the same spec, so a constant change
in the SQF fails here until the mirror is re-synced.

MUTATION PROOF (executed by hand at commit time):
  - change the house divisor ``max 1`` to ``+ 1`` in
    fnc_starBrightnessCoefficient.sqf ->
    ``test_more_houses_lower_the_coefficient`` fails; restore -> OK.

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
BRIGHTNESS = ASTRONOMY / "fnc_starBrightnessCoefficient.sqf"
FADE = ASTRONOMY / "fnc_starWeatherFade.sqf"
PENALTY = ASTRONOMY / "fnc_lightPollutionPenalty.sqf"
LIMIT = ASTRONOMY / "fnc_calculateLimitingMagnitude.sqf"
CATALOG = ASTRONOMY / "fnc_getStarCatalog.sqf"
MAGNITUDE = ASTRONOMY / "fnc_starMagnitude.sqf"
ENV_UPDATE = REPO / "addons" / "core" / "functions" / "fnc_updateEnvironment.sqf"


# ─── Python mirrors of the same spec, for cross-checking the SQF ────────────
def mirror_brightness(moon_phase: float, ambient: float, houses: float) -> float:
    coef2 = ((1.5 - moon_phase) ** 2) * (min(ambient, 1000) ** 4)
    if coef2 <= 0:
        return 100.0
    inner = max((10 / coef2) / max(houses, 1), 0.1)
    return min((inner**0.8) / 2, 100.0)


def mirror_fade(value: float, overcast: float, fog: float) -> float:
    overcast_fade = value * ((0.5 - overcast) / 0.05) if overcast < 0.5 else 0.0
    fog_fade = value * ((0.4 - fog) / 0.05) if fog < 0.4 else 0.0
    overcast_fade = max(0.0, min(value, overcast_fade))
    fog_fade = max(0.0, min(value, fog_fade))
    return min(overcast_fade, fog_fade, value)


def mirror_penalty(houses: float) -> float:
    h = max(houses, 0)
    penalty = 2.0 * (math.log10(1 + h) / math.log10(1 + 1000))
    return max(0.0, min(2.0, penalty))


def brightness(moon_phase: float, ambient: float, houses: float) -> float:
    return run_sqf(BRIGHTNESS, [moon_phase, ambient, houses])


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


class TestStarBrightnessCoefficient(unittest.TestCase):
    def test_brightness_rises_with_moon_phase(self) -> None:
        dim = brightness(0.0, 0.5, 0)
        bright = brightness(0.5, 0.5, 0)
        self.assertGreater(bright, dim)
        self.assertLess(mirror_brightness(0.5, 0.5, 0), 100.0)
        self.assertAlmostEqual(bright, mirror_brightness(0.5, 0.5, 0), places=6)

    def test_more_houses_lower_the_coefficient(self) -> None:
        rural = brightness(0.5, 0.5, 0)
        town = brightness(0.5, 0.5, 100)
        self.assertGreater(rural, town)
        self.assertAlmostEqual(town, mirror_brightness(0.5, 0.5, 100), places=6)

    def test_more_ambient_lowers_the_coefficient(self) -> None:
        dark = brightness(0.5, 0.1, 0)
        lit = brightness(0.5, 5.0, 0)
        self.assertGreater(dark, lit)

    def test_zero_ambient_returns_the_cap(self) -> None:
        self.assertAlmostEqual(brightness(0.5, 0.0, 0), 100.0, places=6)
        self.assertAlmostEqual(mirror_brightness(0.5, 0.0, 0), 100.0, places=6)

    def test_mirror_matches_sqf_over_a_sweep(self) -> None:
        for moon in (0.0, 0.25, 0.5, 0.75, 1.0):
            for ambient in (0.0, 0.01, 0.1, 1.0, 1000.0):
                for houses in (0, 1, 10, 100):
                    with self.subTest(moon=moon, ambient=ambient, houses=houses):
                        got = brightness(moon, ambient, houses)
                        want = mirror_brightness(moon, ambient, houses)
                        self.assertAlmostEqual(got, want, places=4)


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

    def test_overcast_fades_the_value(self) -> None:
        clear = fade(10.0, 0.0, 0.0)
        cloudy = fade(10.0, 0.49, 0.0)
        self.assertGreater(clear, cloudy)

    def test_fog_fades_the_value(self) -> None:
        clear = fade(10.0, 0.0, 0.0)
        hazy = fade(10.0, 0.0, 0.39)
        self.assertGreater(clear, hazy)

    def test_high_overcast_zeroes_the_value(self) -> None:
        self.assertAlmostEqual(fade(10.0, 0.5, 0.0), 0.0, places=6)
        self.assertAlmostEqual(fade(10.0, 1.0, 0.0), 0.0, places=6)


class TestLightPollutionPenalty(unittest.TestCase):
    def test_light_pollution_penalty_is_bounded_0_to_2(self) -> None:
        for houses in (0, 1, 10, 100, 1000, 10000, 100000):
            with self.subTest(houses=houses):
                got = penalty(houses)
                self.assertGreaterEqual(got, 0.0)
                self.assertLessEqual(got, 2.0)
                self.assertAlmostEqual(got, mirror_penalty(houses), places=6)

    def test_penalty_is_zero_at_zero_houses(self) -> None:
        self.assertAlmostEqual(penalty(0), 0.0, places=6)

    def test_penalty_rises_with_houses(self) -> None:
        self.assertGreater(penalty(100), penalty(10))
        self.assertGreater(penalty(10), penalty(0))

    def test_negative_house_count_clamps_to_zero(self) -> None:
        self.assertAlmostEqual(penalty(-5), 0.0, places=6)


class TestKernelPurity(unittest.TestCase):
    """The three kernels must not touch missionNamespace, GVAR or an engine
    command: they are pure functions of their arguments."""

    def test_kernels_are_pure(self) -> None:
        for kernel in (BRIGHTNESS, FADE, PENALTY):
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
            "PREPS(astronomy,starBrightnessCoefficient)",
            "PREPS(astronomy,starWeatherFade)",
            "PREPS(astronomy,lightPollutionPenalty)",
        ):
            with self.subTest(entry=entry):
                self.assertIn(entry, prep)

    def test_headers_carry_the_source_marking(self) -> None:
        for kernel in (BRIGHTNESS, FADE, PENALTY):
            text = kernel.read_text(encoding="utf-8")
            with self.subTest(kernel=kernel.name):
                self.assertIn("3749362906", text)
                self.assertIn("no licence", text)
                self.assertIn("UNSOURCED", text)


def mirror_nelm(
    ambient_lux: float, seeing: float, houses: float, subtract_pollution: bool = True
) -> float:
    m_base = 6.5 - math.log10(max(ambient_lux / 0.001, 1e-6))
    clamped_seeing = max(0.1, min(1.0, seeing))
    seeing_penalty = 0.2 + 1.3 * ((clamped_seeing - 0.1) / 0.9)
    pollution = penalty(houses) if subtract_pollution else 0.0
    return max(2.0, min(7.0, m_base - pollution - seeing_penalty))


class TestNelmLinksToLightPollution(unittest.TestCase):
    """fnc_calculateLimitingMagnitude subtracts the light-pollution penalty."""

    def test_nelm_falls_with_more_houses(self) -> None:
        live = live_source(LIMIT)
        self.assertIn("call FUNC(lightPollutionPenalty)", live)
        self.assertTrue(
            __import__("re").search(r"_mBase\s*-\s*_pollution", live),
            "the penalty is not subtracted from _mBase",
        )
        # Tie the numeric result to the source: if the subtraction line is
        # commented out the live source loses both tokens and the NELM no
        # longer falls with houses.
        wired = "call FUNC(lightPollutionPenalty)" in live
        n0 = mirror_nelm(0.001, 0.1, 0, wired)
        n100 = mirror_nelm(0.001, 0.1, 100, wired)
        self.assertLess(n100, n0)

    def test_nelm_unchanged_at_zero_houses(self) -> None:
        self.assertAlmostEqual(penalty(0), 0.0, places=6)
        self.assertAlmostEqual(
            mirror_nelm(0.001, 0.1, 0), mirror_nelm(0.001, 0.1, 0, False), places=6
        )
        self.assertAlmostEqual(
            mirror_nelm(0.3, 0.5, 0), mirror_nelm(0.3, 0.5, 0, False), places=6
        )


class TestStarCatalogueWiring(unittest.TestCase):
    def test_star_catalogue_applies_the_brightness_coefficient(self) -> None:
        live = live_source(CATALOG)
        self.assertIn("call FUNC(starBrightnessCoefficient)", live)
        self.assertIn("call FUNC(starWeatherFade)", live)
        self.assertIn("GVAR(starBrightnessScale)", live)
        self.assertIn("GVAR(worldLighting)", live)
        self.assertIn("setVariable [QGVAR(starBrightnessCoefficient)", live)

    def test_source_contract_reads_getlighting_element_1(self) -> None:
        # The tick caller caches the engine ambient brightness (getLighting
        # element 1); the catalogue reads the cache.  The kernel stays pure.
        live_tick = live_source(ENV_UPDATE)
        self.assertIn("getLighting select 1", live_tick)
        live_cat = live_source(CATALOG)
        self.assertIn("ambientBrightness", live_cat)

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
