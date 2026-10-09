#!/usr/bin/env python3
"""Weather particle alpha and heat haze kernels (aee-workshop-copy item 7).

The kernels are pure: no missionNamespace, no GVAR or EGVAR, no engine
command.  These tests run the REAL SQF through the SQF lite interpreter and
cross-check it against a Python mirror of the same spec, so a constant change
in the SQF fails here until the mirror is re-synced.

The values are re-derived from Better Visuals (Workshop 3351805137)
fn_blastWaveEffectMedium.sqf and fn_heatHaze.sqf.  The mod publishes no
licence, so this is a re-implementation, not copied code.  No mod content is
copied.

MUTATION PROOF (executed by hand at commit time):
  - remove the upper clamp in fnc_heatHazeAlpha.sqf and pass temperature 100
    -> ``test_heat_haze_is_clamped_0_15_to_0_45`` fails; restore -> OK.

Run: python3 -m unittest tools.tests.test_weather_particles -v
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))

from sqf_lite import run_sqf  # noqa: E402

FX = REPO / "addons" / "fx"
PARTICLE = REPO / "addons" / "particles" / "functions" / "particle"
WEATHER = REPO / "addons" / "weatherfx" / "functions" / "weather"
ALPHA = PARTICLE / "fnc_weatherParticleAlpha.sqf"
HAZE_ALPHA = PARTICLE / "fnc_heatHazeAlpha.sqf"
HAZE_SIZE = PARTICLE / "fnc_heatHazeSize.sqf"
PREP = REPO / "addons" / "particles" / "XEH_PREP.hpp"
TRACE = PARTICLE / "fnc_renderSupersonicTrace.sqf"
EMIT = PARTICLE / "fnc_particlePipelineEmit.sqf"
SHIMMER = WEATHER / "fnc_applyExhaustShimmer.sqf"
INIT_SETTINGS = REPO / "addons" / "particles" / "initSettings.inc.sqf"
WEATHERFX_SETTINGS = REPO / "addons" / "weatherfx" / "initSettings.inc.sqf"
PARTICLES_STRINGTABLE = REPO / "addons" / "particles" / "stringtable.xml"
WEATHERFX_STRINGTABLE = REPO / "addons" / "weatherfx" / "stringtable.xml"
CONFIG_DOCS = REPO / "docs" / "wiki" / "chapters" / "configuration.qmd"
CHANGED_FX = (TRACE, EMIT, SHIMMER)


# ─── Python mirror of the kernel spec ───────────────────────────────────────


def mirror_alpha(
    alpha: float, overcast: float, humidity_percent: float, scale: float
) -> float:
    return max(0.0, min(alpha * (overcast + humidity_percent / 100) * scale, 2.0))


def mirror_haze_alpha(temp: float, lo: float = 0.15, hi: float = 0.45) -> float:
    return max(lo, min(temp / 100, hi))


def mirror_haze_size(rng: float) -> float:
    return max(0.5, min(0.5 + rng, 1.5))


# ─── Harness wrappers ───────────────────────────────────────────────────────


def alpha(
    value: float = 1,
    overcast: float = 0,
    humidity_percent: float = 50,
    scale: float = 1,
):
    return run_sqf(ALPHA, [value, overcast, humidity_percent, scale])


def haze_alpha(temp: float = 20, lo: float = 0.15, hi: float = 0.45):
    return run_sqf(HAZE_ALPHA, [temp, lo, hi])


def haze_size(rng: float = 1):
    return run_sqf(HAZE_SIZE, [rng])


def live_source(path: Path) -> str:
    """Source with // and /* */ comments stripped, so a commented-out line
    or a header mention is invisible to a contract assertion."""
    text = path.read_text(encoding="utf-8")
    import re

    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return "\n".join(line.split("//")[0] for line in text.splitlines())


class TestWeatherParticleAlpha(unittest.TestCase):
    def test_alpha_scales_with_overcast_and_humidity(self) -> None:
        # overcast 0.5 + humidity 50/100 = 1.0, so the base alpha passes through.
        self.assertAlmostEqual(alpha(1, 0.5, 50, 1), 1.0, places=9)
        self.assertAlmostEqual(alpha(0.5, 0.2, 80, 1), 0.5, places=9)
        self.assertAlmostEqual(alpha(1, 0, 0, 1), 0.0, places=9)
        # More humidity and more overcast each raise the alpha.
        self.assertGreater(alpha(1, 0.5, 90, 1), alpha(1, 0.5, 10, 1))
        self.assertGreater(alpha(1, 0.8, 50, 1), alpha(1, 0.2, 50, 1))

    def test_alpha_is_clamped(self) -> None:
        # 1 * (1 + 100/100) * 8 is far above the 2 ceiling.
        self.assertEqual(alpha(1, 1, 100, 8), 2.0)
        # A negative product floors at 0.
        self.assertEqual(alpha(1, 0, 50, -1), 0.0)

    def test_scale_and_defaults(self) -> None:
        self.assertAlmostEqual(alpha(2, 0.5, 50, 0.5), 1.0, places=9)
        # Defaults: alpha 1, overcast 0, humidity 50, scale 1 -> 0.5
        self.assertAlmostEqual(run_sqf(ALPHA, []), 0.5, places=9)

    def test_mirror_matches_sqf_over_a_sweep(self) -> None:
        for overcast in (0.0, 0.25, 0.5, 0.75, 1.0):
            for humidity in (0, 25, 50, 75, 100, 120):
                with self.subTest(overcast=overcast, humidity=humidity):
                    got = alpha(1, overcast, humidity, 1)
                    want = mirror_alpha(1.0, overcast, humidity, 1.0)
                    self.assertAlmostEqual(got, want, places=9)


class TestHeatHazeAlpha(unittest.TestCase):
    def test_heat_haze_is_clamped_0_15_to_0_45(self) -> None:
        self.assertAlmostEqual(haze_alpha(20), 0.20, places=9)
        self.assertAlmostEqual(haze_alpha(45), 0.45, places=9)
        self.assertEqual(haze_alpha(100), 0.45)
        self.assertEqual(haze_alpha(0), 0.15)

    def test_cold_ambient_uses_the_floor(self) -> None:
        self.assertEqual(haze_alpha(-40), 0.15)
        self.assertEqual(haze_alpha(10), 0.15)

    def test_bounds_are_parameters(self) -> None:
        self.assertEqual(haze_alpha(100, 0.0, 0.8), 0.8)
        self.assertEqual(haze_alpha(5, 0.1, 0.45), 0.1)

    def test_mirror_matches_sqf_over_a_sweep(self) -> None:
        for temp in (-40, 0, 10, 15, 20, 30, 44, 45, 60, 100):
            with self.subTest(temp=temp):
                self.assertAlmostEqual(
                    haze_alpha(temp), mirror_haze_alpha(temp), places=9
                )


class TestHeatHazeSize(unittest.TestCase):
    def test_size_is_0_5_plus_the_draw(self) -> None:
        self.assertAlmostEqual(haze_size(0), 0.5, places=9)
        self.assertAlmostEqual(haze_size(0.5), 1.0, places=9)
        self.assertAlmostEqual(haze_size(1), 1.5, places=9)

    def test_size_is_clamped(self) -> None:
        self.assertEqual(haze_size(-5), 0.5)
        self.assertEqual(haze_size(5), 1.5)

    def test_mirror_matches_sqf(self) -> None:
        for rng in (-1, 0, 0.25, 0.5, 0.9, 1, 2):
            with self.subTest(rng=rng):
                self.assertAlmostEqual(haze_size(rng), mirror_haze_size(rng), places=9)


class TestKernelPurity(unittest.TestCase):
    def test_kernels_are_pure(self) -> None:
        for path in (ALPHA, HAZE_ALPHA, HAZE_SIZE):
            text = live_source(path)
            for token in (
                "missionNamespace",
                "GVAR(",
                "EGVAR(",
                "getVariable",
                "setVariable",
            ):
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token, text)

    def test_headers_carry_the_source_marking(self) -> None:
        for path in (ALPHA, HAZE_ALPHA, HAZE_SIZE):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("3351805137", text)
                self.assertIn("no licence", text)
                self.assertIn("No mod content is copied", text)


class TestPrepEntries(unittest.TestCase):
    def test_prep_entries_exist(self) -> None:
        prep = PREP.read_text(encoding="utf-8")
        for entry in (
            "PREPS(particle,weatherParticleAlpha)",
            "PREPS(particle,heatHazeAlpha)",
            "PREPS(particle,heatHazeSize)",
        ):
            with self.subTest(entry=entry):
                self.assertIn(entry, prep)


class TestWeatherWiring(unittest.TestCase):
    def test_blast_alpha_uses_overcast_and_humidity(self) -> None:
        # The shared particle-colour path (the blast, fire and weather family)
        # and the refract shock trace both call the kernel with the engine
        # overcast and the published humidity.
        for path in (TRACE, EMIT):
            live = live_source(path)
            with self.subTest(path=path.name):
                self.assertIn("FUNC(weatherParticleAlpha)", live)
                self.assertIn("overcast", live)
                self.assertIn("QEGVAR(core,currentHumidity)", live)

    def test_heat_haze_is_wired_to_the_exhaust_shimmer(self) -> None:
        live = live_source(SHIMMER)
        self.assertIn("EFUNC(particles,heatHazeAlpha)", live)
        self.assertIn("EFUNC(particles,heatHazeSize)", live)
        self.assertIn("ambientTemperature", live)

    def test_haze_scale_guards_a_zero_reference(self) -> None:
        """H1: heatHazeMaxAlpha 0 makes the 20 C reference 0, so the raw
        ratio divides by zero.  The guard returns the neutral scale 1."""
        live = live_source(SHIMMER)
        self.assertIn("_hazeRef > 0", live)
        self.assertRegex(
            live,
            re.compile(
                r"if \(_hazeRef > 0\) then \{.*?\} else \{\s*1\s*\};",
                re.DOTALL,
            ),
        )

    def test_shimmer_consumes_the_matcher_haze_scale(self) -> None:
        """GAP-2: fnc_worldLightingProfile returns element 3 (the haze
        scale) and it must have a consumer.  The shimmer reads it the way the
        grain path reads element 2."""
        live = live_source(SHIMMER)
        self.assertRegex(
            live,
            r"_worldProfile\s*=\s*missionNamespace getVariable "
            r"\[QEGVAR\(lighting,worldLighting\)",
        )
        self.assertIn("_worldProfile select 3", live)
        self.assertIn("_hazeWorldScale", live)

    def test_no_engine_weather_write(self) -> None:
        # The change reads engine weather and never writes it.
        banned = ("setOvercast", "setRain", "setFog", "setHumidity", "setWind")
        for path in CHANGED_FX:
            live = live_source(path)
            for token in banned:
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token, live)


class TestWeatherSettings(unittest.TestCase):
    def test_settings_register_in_the_particles_and_weatherfx_groups(self) -> None:
        particles = live_source(INIT_SETTINGS)
        weatherfx = live_source(WEATHERFX_SETTINGS)
        self.assertRegex(
            particles,
            r'AEE_SETTING_CHECKBOX\(weatherAlphaEnabled,"AEE Particles","Particles",true\)',
        )
        self.assertRegex(
            weatherfx,
            r'AEE_SETTING_CHECKBOX\(heatHazeEnabled,"AEE Weather FX","Particles",true\)',
        )
        self.assertRegex(
            weatherfx,
            r'AEE_SETTING_SLIDER\(heatHazeMaxAlpha,"AEE Weather FX","Particles",0,0\.45,0\.45,2\)',
        )

    def test_stringtable_carries_the_keys(self) -> None:
        particles = PARTICLES_STRINGTABLE.read_text(encoding="utf-8")
        weatherfx = WEATHERFX_STRINGTABLE.read_text(encoding="utf-8")
        for key in (
            "STR_AEE_Particles_weatherAlphaEnabled_Name",
            "STR_AEE_Particles_weatherAlphaEnabled_Description",
        ):
            with self.subTest(key=key):
                self.assertIn(key, particles)
        for key in (
            "STR_AEE_WeatherFX_heatHazeEnabled_Name",
            "STR_AEE_WeatherFX_heatHazeEnabled_Description",
            "STR_AEE_WeatherFX_heatHazeMaxAlpha_Name",
            "STR_AEE_WeatherFX_heatHazeMaxAlpha_Description",
        ):
            with self.subTest(key=key):
                self.assertIn(key, weatherfx)

    def test_configuration_docs_are_regenerated(self) -> None:
        doc = CONFIG_DOCS.read_text(encoding="utf-8")
        for name in (
            "aee_particles_weatherAlphaEnabled",
            "aee_weatherfx_heatHazeEnabled",
            "aee_weatherfx_heatHazeMaxAlpha",
        ):
            with self.subTest(name=name):
                self.assertIn(name, doc)


if __name__ == "__main__":
    unittest.main()
