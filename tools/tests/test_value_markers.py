#!/usr/bin/env python3
"""Value-marker locks: a labelled constant keeps its label and its order.

The project rule is that every constant traces to a published source.  Where a
constant has no reachable source, it carries a marker in the source
(`MODELLING CHOICE`, `DECLARED DEFAULT`, `proxy`, `tuning`, or `no published`).
A marker is only worth the paper it is written on if the value cannot drift
away from it, so this suite locks the label beside the value for the markers
the triage in docs/wiki/research/value-marker-triage.md resolved.

Three kinds of lock:

  * LABEL BESIDE VALUE.  The value and its marker are read out of the real
    source, and a value that loses its marker fails.
  * ARITHMETIC.  Where a declared default states an anchor ("0.164 degC per
    shot"), the stated figure is recomputed from the value, so a change to one
    without the other fails.
  * CORPUS BEFORE FALLBACK.  A declaration that a corpus row wins over a
    fallback is proved by the order of the reads in the source, not asserted
    in prose.

Every SQF read strips comments first, unless the test is about the comment.

Run: python3 -m unittest tools.tests.test_value_markers -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

AMMO_HPP = REPO / "addons/ballistics/script_component.hpp"
AMMO_FN = REPO / "addons/ballistics/functions/fnc_calculateAmmoTemperature.sqf"
AMMO_SETTINGS = REPO / "addons/ballistics/initSettings.inc.sqf"
ICING = REPO / "addons/atmos/functions/physics/fnc_calculateAirframeIcing.sqf"
ENGINE_LOAD = REPO / "addons/vehicles/functions/fnc_calculateEngineLoad.sqf"
AIR_LOAD = REPO / "addons/flight/functions/fnc_calculateAirEngineLoad.sqf"
ENGINE_NG = REPO / "addons/flight/functions/fnc_calculateEngineNg.sqf"
SHIMMER = REPO / "addons/weatherfx/functions/weather/fnc_applyExhaustShimmer.sqf"
AIRCRAFT_DATA = REPO / "addons/flight/functions/fnc_getAircraftData.sqf"
POOL_EVAP = (
    REPO / "addons/weather/functions/dispersion/fnc_calculatePoolEvaporation.sqf"
)
FRONT = REPO / "addons/atmos/functions/physics/fnc_calculateWeatherFront.sqf"
SECOND_SUN = REPO / "addons/thermal/functions/display/fnc_applySecondSun.sqf"
TRANSMISSION = (
    REPO / "addons/thermal/functions/solver/fnc_calculateAtmosphericTransmission.sqf"
)
BALLISTICS_POST_INIT = REPO / "addons/ballistics/XEH_postInit.sqf"
NVG_TUBE = REPO / "addons/nightvision/functions/fnc_applyNVGTubeModel.sqf"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_comments(source: str) -> str:
    """Remove // and /* */ comments, keeping string literals intact."""
    out: list[str] = []
    i = 0
    n = len(source)
    in_string = False
    while i < n:
        ch = source[i]
        if in_string:
            out.append(ch)
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if source.startswith("//", i):
            while i < n and source[i] != "\n":
                i += 1
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def squash(text: str) -> str:
    """Collapse every whitespace run to one space, so a wrapped line still matches."""
    return re.sub(r"\s+", " ", text)


def default_of(source: str, name: str) -> float:
    """The declared default of a params entry: ["_name", VALUE, [0]]."""
    match = re.search(
        r'\["' + re.escape(name) + r'"\s*,\s*(-?[0-9.]+)\s*,\s*\[0\]\]', source
    )
    if match is None:
        raise AssertionError(f"{name} has no numeric declared default")
    return float(match.group(1))


class AmmoShotHeatTest(unittest.TestCase):
    """The shot-heat default: one definition, and a label that adds up."""

    def setUp(self) -> None:
        self.hpp = read(AMMO_HPP)
        self.fn = read(AMMO_FN)
        self.settings = read(AMMO_SETTINGS)

    def test_one_definition(self) -> None:
        match = re.search(
            r"#define\s+AEE_AMMO_HEAT_PER_SHOT_DEFAULT\s+([0-9.eE+-]+)", self.hpp
        )
        self.assertIsNotNone(match, "the shot-heat default lost its single definition")
        self.assertAlmostEqual(float(match.group(1)), 0.0001, places=9)

    def test_setting_literal_equals_the_definition(self) -> None:
        # The settings taxonomy and the documentation generators parse the
        # settings file as text and cannot resolve a macro, so the default is
        # written out there.  This lock is what keeps the copy honest.
        match = re.search(
            r'AEE_SETTING_SLIDER\(ammoHeatPerShotJ,[^)]*?,([0-9.eE+-]+),\d+\);',
            self.settings,
        )
        self.assertIsNotNone(match, "the ammo shot-heat setting is missing")
        self.assertAlmostEqual(float(match.group(1)), 0.0001, places=9)

    def test_the_read_uses_the_definition(self) -> None:
        self.assertIn("AEE_AMMO_HEAT_PER_SHOT_DEFAULT", self.fn)
        # A bare copy of the number is the drift this lock exists to stop.
        self.assertNotRegex(
            strip_comments(self.fn),
            r"ammoHeatPerShotJ\)\s*,\s*0\.0001",
            "the read fallback carries a bare copy of the default",
        )

    def test_label_states_it_is_a_declared_default(self) -> None:
        self.assertIn("DECLARED DEFAULT, not a measurement", self.fn)

    def test_the_stated_anchors_are_the_arithmetic_of_the_default(self) -> None:
        # The header states two anchored figures.  Recompute both from the
        # default, so a change to one without the other fails.
        heat = 0.0001
        five_five_six = 0.5 * 0.004 * 905**2
        nine_mm = 0.5 * 0.008 * 400**2
        for stated, energy in ((0.164, five_five_six), (0.064, nine_mm)):
            self.assertAlmostEqual(
                round(heat * energy, 3),
                stated,
                places=3,
                msg=f"the label states {stated} degC but the default yields {heat * energy:.4f}",
            )
            self.assertIn(f"{stated} degC per shot", self.fn)


class IcingLiquidWaterTest(unittest.TestCase):
    """The liquid-water coefficients carry the citation that bounds them."""

    def setUp(self) -> None:
        self.source = read(ICING)
        self.code = strip_comments(self.source)

    def test_coefficients_are_named_beside_the_label(self) -> None:
        self.assertRegex(self.code, r"private _cloudLwcGm3\s*=\s*0\.5;")
        self.assertRegex(self.code, r"private _rainLwcGm3\s*=\s*2;")
        self.assertIn("_overcast * _cloudLwcGm3", self.code)
        self.assertIn("_rain * _rainLwcGm3", self.code)

    def test_no_bare_copy_survives_in_the_lwc_sum(self) -> None:
        self.assertNotRegex(self.code, r"_overcast \* 0\.5")
        self.assertNotRegex(self.code, r"_rain \* 2\b")

    def test_label_cites_the_appendix_paragraph(self) -> None:
        self.assertIn("25 App C Part I(c)", self.source)
        self.assertIn("0.35 g/m3", self.source)

    def test_label_says_the_appendix_holds_no_rain_figure(self) -> None:
        # The appendix states one cloud LWC and no rain LWC.  A label that
        # claims the envelope covers rain is the drift this locks out.
        self.assertIn("no rain figure", self.source)
        self.assertIn("STATED PROXIES", self.source)

    def test_accretion_scale_is_labelled(self) -> None:
        self.assertIn("0.05 is a stated scale, not a measurement", self.source)

    def test_cloud_probe_stays_the_preferred_path(self) -> None:
        probe = self.code.find("simulCloudDensity")
        self.assertGreater(probe, 0, "the in-cloud probe path is gone")
        self.assertLess(
            self.code.find("_overcast * _cloudLwcGm3"),
            probe,
            "the overcast proxy must be the value the probe replaces",
        )


class DeclaredDefaultLabelTest(unittest.TestCase):
    """Each kept declared default still carries the prose that qualifies it."""

    def test_ground_engine_load_rated_power(self) -> None:
        code = strip_comments(read(ENGINE_LOAD))
        self.assertEqual(default_of(code, "_ratedPowerW"), 150000)
        self.assertEqual(default_of(code, "_dragAreaM2"), 0.7)
        self.assertIn("DECLARED DEFAULT", read(ENGINE_LOAD))

    def test_air_engine_load_rated_power(self) -> None:
        source = read(AIR_LOAD)
        code = strip_comments(source)
        self.assertEqual(default_of(code, "_ratedPowerW"), 150000)
        self.assertEqual(default_of(code, "_dragAreaM2"), 0.7)
        self.assertEqual(default_of(code, "_rotorDiscAreaM2"), 50)
        self.assertIn(
            "THE DRAG AREA AND THE ROTOR DISC AREA ARE DECLARED DEFAULTS", source
        )
        self.assertIn("RATED POWER IS A DECLARED DEFAULT", source)
        # The header records the coincidence so nobody reads it as evidence.
        self.assertIn("COINCIDENCE OF ORDER OF MAGNITUDE", squash(source))

    def test_engine_spool_time_constant(self) -> None:
        source = read(ENGINE_NG)
        self.assertEqual(default_of(strip_comments(source), "_spoolTauS"), 4)
        self.assertIn(
            "THE TIME CONSTANT IS A DECLARED DEFAULT, NOT A MEASUREMENT", source
        )

    def test_pool_evaporation_schmidt_number(self) -> None:
        source = read(POOL_EVAP)
        self.assertEqual(default_of(strip_comments(source), "_schmidt"), 0.7)
        self.assertIn("MODELLING CHOICE", source)
        # The band is a stated placeholder, not a cited table.  The label has
        # to say so, or the range reads as sourced.
        self.assertIn(
            "no published table of molecular Schmidt numbers for vapours in air",
            squash(source),
        )

    def test_weather_front_cycle_length_is_cited(self) -> None:
        source = read(FRONT)
        self.assertIn("345600", strip_comments(source))
        self.assertIn("Stull", source)
        self.assertIn("modelling choice", source.lower())

    def test_second_sun_brightness_is_display_tuning(self) -> None:
        source = read(SECOND_SUN)
        self.assertIn("_lightBrightness = 13 * _radiation", strip_comments(source))
        self.assertIn("display-tuning value with no published", source)

    def test_atmospheric_transmission_alpha_is_cited(self) -> None:
        source = read(TRANSMISSION)
        self.assertEqual(
            re.search(r"private _alphaRef = ([0-9.]+);", strip_comments(source)).group(
                1
            ),
            "0.008",
        )
        self.assertIn("Minkina and Klecha 2016", source)


class BulletMassFallbackTest(unittest.TestCase):
    """The held bullet wins; the CfgAmmo damage figure is only the fallback."""

    def setUp(self) -> None:
        self.code = strip_comments(read(BALLISTICS_POST_INIT))

    def test_corpus_precedes_the_damage_number(self) -> None:
        corpus = self.code.find("FUNC(getProjectileData)")
        proxy = self.code.find('"hit") * 0.5')
        baseline = self.code.find("4.0 / 1000")
        self.assertTrue(-1 < corpus < proxy, "the corpus is not read before the proxy")
        self.assertTrue(-1 < proxy < baseline, "the baseline does not sit last")

    def test_the_proxy_is_labelled_as_a_fallback(self) -> None:
        source = read(BALLISTICS_POST_INIT)
        self.assertIn("only the fallback when the corpus", squash(source))


class DeviceRowPrecedenceTest(unittest.TestCase):
    """A published tube row wins over the tuned generation defaults."""

    def setUp(self) -> None:
        self.code = strip_comments(read(NVG_TUBE))

    def test_snr_row_wins_over_the_generation_floor(self) -> None:
        tuned = self.code.find("private _noiseFloor = 0.15;")
        row = self.code.find("if (_devSnr > 0) then { _noiseFloor = 1 / _devSnr; }")
        self.assertTrue(
            -1 < tuned < row, "the device SNR must be applied after the tier default"
        )

    def test_resolution_row_wins_over_the_tier_mtf_input(self) -> None:
        tuned = self.code.find("private _mtf15 = 0.45;")
        row = self.code.find("if (_devRes > 0) then { _resLpmm = _devRes; }")
        self.assertTrue(
            -1 < tuned < row, "the device resolution must be applied after the default"
        )

    def test_photon_scale_is_labelled_as_one_calibration_constant(self) -> None:
        source = read(NVG_TUBE)
        self.assertIn("#define AEE_PHOTON_SCALE 500", strip_comments(source))
        self.assertIn("NOT per-tier magic", squash(source))


class CorpusBeforeFallbackTest(unittest.TestCase):
    """The aircraft corpus row wins over the declared default, in the source."""

    def setUp(self) -> None:
        self.code = strip_comments(read(SHIMMER))
        block = re.search(r"private _deriveAirPower = \{(.*?)\n\};", self.code, re.S)
        self.assertIsNotNone(block, "the air power resolver is missing")
        self.body = block.group(1)

    def _order(self, *tokens: str) -> list[int]:
        found = []
        for token in tokens:
            index = self.body.find(token)
            self.assertGreater(index, -1, f"{token} is missing from the air resolver")
            found.append(index)
        return found

    def test_the_row_is_read_before_any_default(self) -> None:
        order = self._order("getAircraftData", "_corpusRated", "_rated = 150000")
        self.assertEqual(order, sorted(order), "the corpus is read after the default")

    def test_rated_power_is_override_then_corpus_then_default(self) -> None:
        order = self._order(
            'getVariable ["aee_engineRatedPowerW", 0]',
            "_rated = _corpusRated",
            "_rated = 150000",
        )
        self.assertEqual(
            order, sorted(order), "rated power order is override, corpus, default"
        )

    def test_drag_area_is_override_then_corpus_then_default(self) -> None:
        order = self._order(
            'getVariable ["aee_engineDragAreaM2", 0]',
            "_dragArea = _corpusDrag",
            "_dragArea = 0.7",
        )
        self.assertEqual(
            order, sorted(order), "drag area order is override, corpus, default"
        )

    def test_disc_area_is_override_then_corpus_then_default(self) -> None:
        order = self._order(
            'getVariable ["aee_engineRotorDiscAreaM2", 0]',
            "_discArea = _corpusDisc",
            "_discArea = 50",
        )
        self.assertEqual(
            order, sorted(order), "disc area order is override, corpus, default"
        )

    def test_a_corpus_row_is_required_before_the_default_can_apply(self) -> None:
        # Each default line must be guarded by a > 0 test on the corpus value,
        # so an empty row falls through and a present row stops the fall.
        for name in ("_rated", "_dragArea", "_discArea"):
            self.assertIn(f"if ({name} <= 0) then {{ {name} = _corpus", self.body)

    def test_row_indices_match_the_documented_order(self) -> None:
        # The row is [mass kg, rated power W, drag area m2, rotor disc area m2].
        documented = read(AIRCRAFT_DATA)
        self.assertIn(
            "operating weight kg, rated power W, drag area m^2 and rotor disc area m^2",
            squash(documented),
        )
        self.assertIn("_row select 0", self.body)  # mass
        self.assertIn("_row select 1", self.body)  # rated power
        self.assertIn("_row select 2", self.body)  # drag area
        self.assertIn("_row select 3", self.body)  # rotor disc area
        self.assertLess(
            self.body.find("_row select 1"),
            self.body.find("_rated = _corpusRated"),
            "the rated power is not taken from index 1",
        )


if __name__ == "__main__":
    unittest.main()
