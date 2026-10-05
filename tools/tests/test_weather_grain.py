#!/usr/bin/env python3
"""Rain-scaled film grain kernel and wiring (aee-workshop-copy item 5).

The kernel is pure: no missionNamespace, no GVAR or EGVAR, no engine state.
These tests run the REAL SQF through the SQF lite interpreter and cross-check
it against a Python mirror of the same spec, so a constant change in the SQF
fails here until the mirror is re-synced.

The colour invariant is the regression this file guards.  The source wrote the
literal `true` as the sixth FilmGrain element; AEE writes 1, so the grain is
colour.  A 0 there is monochrome and drains the scene to grey, which is the
live defect fixed at c753730 for the acuity grain.  ``test_every_filmgrain_
array_is_colour`` fails if any branch (or a mutation) returns 0 or a
non-number.

MUTATION PROOF (executed by hand at commit time):
  - change the night-rain branch last element to 0 in
    fnc_weatherGrainParams.sqf ->
    ``test_every_filmgrain_array_is_colour`` fails; restore -> OK.

Run: python3 -m unittest tools.tests.test_weather_grain -v
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))

from sqf_lite import run_sqf  # noqa: E402

OPTICS = REPO / "addons" / "optics"
KERNEL = OPTICS / "functions" / "vision" / "fnc_weatherGrainParams.sqf"
APPLY = OPTICS / "functions" / "vision" / "fnc_applyWeatherGrain.sqf"
INIT = OPTICS / "functions" / "vision" / "fnc_initWeatherGrain.sqf"
PREP = OPTICS / "XEH_PREP.hpp"
POSTINIT = OPTICS / "XEH_postInit.sqf"


def mirror(rain: float, sun_or_moon: float) -> list[float]:
    if sun_or_moon < 0.5:
        if rain > 0.4:
            return [0.01, 0.7, 3.5, 1, 1, 1]
        return [0.01, 0.5, 0.5, 0.1, 0.1, 1]
    if rain > 0.2:
        t = (rain - 0.2) / (1 - 0.2)
        t = max(0.0, min(1.0, t))
        return [0.01, 0.7 + t * (0.2 - 0.7), 3, 1, 1, 1]
    return [0.1, 0.5, 0.5, 0.1, 0.1, 1]


def params(rain: float, sun_or_moon: float) -> list[float]:
    return run_sqf(KERNEL, [rain, sun_or_moon])


def live_source(path: Path) -> str:
    """Source with // and /* */ comments stripped, so a commented-out line
    is invisible to the contract assertions."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return "\n".join(line.split("//")[0] for line in text.splitlines())


class TestWeatherGrainBranches(unittest.TestCase):
    def test_night_rain_branch(self) -> None:
        self.assertEqual(params(0.6, 0.0), [0.01, 0.7, 3.5, 1, 1, 1])
        self.assertEqual(params(1.0, 0.0), [0.01, 0.7, 3.5, 1, 1, 1])
        # rain exactly 0.4 is NOT above the threshold: the night-dry branch.
        self.assertEqual(params(0.4, 0.0), [0.01, 0.5, 0.5, 0.1, 0.1, 1])

    def test_night_dry_branch(self) -> None:
        self.assertEqual(params(0.0, 0.0), [0.01, 0.5, 0.5, 0.1, 0.1, 1])
        self.assertEqual(params(0.39, 0.0), [0.01, 0.5, 0.5, 0.1, 0.1, 1])

    def test_day_rain_branch(self) -> None:
        # The sharpness is a linear map from rain in [0.2, 1] onto [0.7, 0.2],
        # clamped.  The array is compared to the mirror, not to a constant.
        for rain in (0.21, 0.5, 0.75, 1.0):
            with self.subTest(rain=rain):
                got = params(rain, 1.0)
                want = mirror(rain, 1.0)
                self.assertAlmostEqual(got[1], want[1], places=6)
                self.assertEqual(got[0], 0.01)
                self.assertEqual(got[2], 3)
                self.assertEqual(got[3:], [1, 1, 1])

    def test_day_dry_branch(self) -> None:
        self.assertEqual(params(0.0, 1.0), [0.1, 0.5, 0.5, 0.1, 0.1, 1])
        # rain exactly 0.2 is NOT above the threshold: the day-dry branch.
        self.assertEqual(params(0.2, 1.0), [0.1, 0.5, 0.5, 0.1, 0.1, 1])

    def test_mirror_matches_sqf_over_a_sweep(self) -> None:
        for sun in (0.0, 0.25, 0.49, 0.5, 0.75, 1.0):
            for rain in (0.0, 0.19, 0.2, 0.21, 0.39, 0.4, 0.41, 0.6, 0.8, 1.0):
                with self.subTest(sun=sun, rain=rain):
                    self.assertEqual(params(rain, sun), mirror(rain, sun))


class TestFilmGrainColourInvariant(unittest.TestCase):
    """The sixth element is always 1 (colour), never 0.  A 0 is monochrome
    and drains the scene to grey (the live defect fixed at c753730)."""

    def test_every_filmgrain_array_is_colour(self) -> None:
        for sun in (0.0, 0.49, 0.5, 1.0):
            for rain in (0.0, 0.2, 0.21, 0.4, 0.41, 0.6, 1.0):
                with self.subTest(sun=sun, rain=rain):
                    got = params(rain, sun)
                    self.assertEqual(len(got), 6)
                    self.assertEqual(got[5], 1, f"monochrome grain at {rain}/{sun}")
                    self.assertIsInstance(got[5], (int, float))
                    self.assertNotIsInstance(got[5], bool)

    def test_source_never_writes_true_or_a_zero_colour(self) -> None:
        live = live_source(KERNEL)
        # The source branch values carry the colour 1, never the literal true.
        self.assertNotIn("true", live.split("params")[-1])
        # Every array literal in a branch ends in a 1 colour element.
        for m in re.finditer(r"\[([^\]]+)\]", live):
            nums = [x.strip() for x in m.group(1).split(",")]
            if len(nums) == 6:
                with self.subTest(array=m.group(0)):
                    self.assertEqual(nums[5], "1")


class TestKernelPurity(unittest.TestCase):
    def test_kernel_is_pure(self) -> None:
        text = live_source(KERNEL)
        for token in (
            "missionNamespace",
            "GVAR(",
            "EGVAR(",
            "getVariable",
            "setVariable",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, text)

    def test_header_carries_the_source_marking(self) -> None:
        text = KERNEL.read_text(encoding="utf-8")
        self.assertIn("2809399991", text)
        self.assertIn("no licence", text)
        self.assertIn("not copied", text)
        # The true-to-1 correction is stated.
        self.assertIn("true", text)


class TestWeatherGrainWiring(unittest.TestCase):
    def test_prep_entries_exist(self) -> None:
        prep = PREP.read_text(encoding="utf-8")
        for entry in (
            "PREPS(vision,weatherGrainParams)",
            "PREPS(vision,applyWeatherGrain)",
            "PREPS(vision,initWeatherGrain)",
        ):
            with self.subTest(entry=entry):
                self.assertIn(entry, prep)

    def test_client_tick_starts_the_driver(self) -> None:
        live = live_source(POSTINIT)
        self.assertIn("FUNC(initWeatherGrain)", live)
        init = live_source(INIT)
        self.assertRegex(
            init, r"\[FUNC\(applyWeatherGrain\), 1\.0\] call CBA_fnc_addPerFrameHandler"
        )

    def test_registry_key_and_priority(self) -> None:
        live = live_source(APPLY)
        self.assertRegex(
            live,
            r'\["optics",\s*"WeatherGrain",\s*"FilmGrain",\s*1747,\s*""\]\s*call EFUNC\(core,createPPEffect\)',
        )
        # The matcher grain scale is element 2 of the published profile.
        self.assertIn("QEGVAR(environmental,worldLighting)", live)
        self.assertIn("select 2", live)
        self.assertIn("QGVAR(weatherGrainIntensity)", live)
        self.assertIn("QGVAR(weatherGrainRainThreshold)", live)
        # The colour invariant holds on the adjust call.
        self.assertRegex(
            live, r"ppEffectAdjust \[_intensity, _sharpness, _size, 1, 1, 1\]"
        )
        # Sensor stand-down.
        self.assertIn("currentVisionMode", live)

    def test_weather_grain_priority_is_free(self) -> None:
        """No other ppEffectCreate in the mod uses priority 1747.  The source
        used it; AEE may keep it only if no other effect holds it.  The core
        registry still bumps on any runtime handle collision."""
        direct = re.compile(r'ppEffectCreate\s*\[\s*"([A-Za-z]+)"\s*,\s*(\d+)\s*\]')
        registry = re.compile(
            r'\[\s*"[^"]+"\s*,\s*"[^"]+"\s*,\s*"([A-Za-z]+)"\s*,\s*(\d+)\s*,'
        )
        hits = []
        for sqf in sorted((REPO / "addons").rglob("*.sqf")):
            text = live_source(sqf)
            for m in list(direct.finditer(text)) + list(registry.finditer(text)):
                if int(m.group(2)) == 1747:
                    hits.append((m.group(1), str(sqf.relative_to(REPO))))
        expected = [
            ("FilmGrain", "addons/optics/functions/vision/fnc_applyWeatherGrain.sqf")
        ]
        self.assertEqual(sorted(hits), sorted(expected))


INIT_SETTINGS = OPTICS / "initSettings.inc.sqf"
STRINGTABLE = OPTICS / "stringtable.xml"
CONFIG_DOCS = REPO / "docs" / "wiki" / "chapters" / "configuration.qmd"


class TestWeatherGrainSettings(unittest.TestCase):
    def test_settings_register_in_the_optics_intensity_group(self) -> None:
        live = live_source(INIT_SETTINGS)
        self.assertRegex(
            live,
            r'AEE_SETTING_SLIDER\(weatherGrainIntensity,"AEE Optics","Intensity",0,1,0\.5,2\)',
        )
        self.assertRegex(
            live,
            r'AEE_SETTING_SLIDER\(weatherGrainRainThreshold,"AEE Optics","Intensity",0,1,0\.2,2\)',
        )

    def test_driver_reads_the_settings_not_constants(self) -> None:
        live = live_source(APPLY)
        self.assertIn("QGVAR(weatherGrainIntensity)", live)
        self.assertIn("QGVAR(weatherGrainRainThreshold)", live)
        self.assertNotIn("AEE_WEATHER_GRAIN_", live)
        # The off-threshold is half the on-threshold (the hysteresis pattern).
        self.assertIn("_rainThreshold * 0.5", live)

    def test_stringtable_carries_the_keys(self) -> None:
        text = STRINGTABLE.read_text(encoding="utf-8")
        for key in (
            "STR_AEE_Optics_weatherGrainIntensity_Name",
            "STR_AEE_Optics_weatherGrainIntensity_Description",
            "STR_AEE_Optics_weatherGrainRainThreshold_Name",
            "STR_AEE_Optics_weatherGrainRainThreshold_Description",
        ):
            with self.subTest(key=key):
                self.assertIn(key, text)

    def test_configuration_docs_are_regenerated(self) -> None:
        doc = CONFIG_DOCS.read_text(encoding="utf-8")
        for name in (
            "aee_optics_weatherGrainIntensity",
            "aee_optics_weatherGrainRainThreshold",
        ):
            with self.subTest(name=name):
                self.assertIn(name, doc)
