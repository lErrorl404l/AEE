#!/usr/bin/env python3
"""Round-2 engine-unit and environment defect locks.

One test per defect found in `.omo/qa/round2/engine-unit-audit.md` and
`.omo/qa/round2/environment-audit.md`.  Each test pins the engine contract or
the corrected scale, so the defect cannot return silently.  The value tests
are Python mirrors of the SQF arithmetic, because the SQF reads engine state a
headless run does not provide; the source-lock assertions fail first if the
SQF stops matching the contract.

Engine contract sources (local, portable names only):
  * acemod/arma3-wiki command DB, command pages `commands/<name>.yml`.
  * BIKI pages, quoted in the SQF comments.
  * Vanilla world config `CfgWorlds >> <world> >> Sea >> MaxWave`
    (map_altis config.cpp:486, MaxWave = 0.25).

Run: python3 -m unittest tools.tests.test_engine_units_round2
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ATMOS_STATE = REPO / "addons" / "atmos" / "functions" / "state"
WEATHER = REPO / "addons" / "weather" / "functions"
CLIMATOLOGY = WEATHER / "climatology"
TERRAIN = WEATHER / "terrain"
WARNINGS = WEATHER / "warnings"

BIOLOGICAL_AMBIENT = WARNINGS / "fnc_calculateBiologicalAmbient.sqf"
UPDATE_WIND = ATMOS_STATE / "fnc_updateWind.sqf"
UPDATE_FOG = ATMOS_STATE / "fnc_updateFog.sqf"
ENGINE_WAVES = REPO / "addons" / "maritime" / "functions" / "fnc_updateEngineWaves.sqf"
SNOW = TERRAIN / "fnc_calculateSnowAccumulation.sqf"
SPACE_WEATHER = CLIMATOLOGY / "fnc_calculateSpaceWeather.sqf"
FOG_BASE = CLIMATOLOGY / "fnc_calculateFogBaseAltitude.sqf"
LATITUDE_CLIMATE = CLIMATOLOGY / "fnc_getLatitudeClimate.sqf"
LUNAR = CLIMATOLOGY / "fnc_calculateLunarIllumination.sqf"
STATIONS = REPO / "addons" / "weather" / "CfgClimateStations.hpp"
ATMOS_DUMP = REPO / "addons" / "atmos" / "functions" / "fnc_dumpState.sqf"


def _read(path):
    return path.read_text(encoding="utf-8")


def _station_ids(text):
    return re.findall(r'\bid = "([^"]*)"', text)


# ─── M4: sunOrMoon is 0..1, never negative ───────────────────────────────


def night_factor(sun_or_moon):
    """Mirror of the night factor in fnc_calculateBiologicalAmbient."""
    return 0.6 if sun_or_moon < 0.5 else 1.0


class TestSunOrMoonNightTest(unittest.TestCase):
    """BIKI `sunOrMoon`: 0 for night (moon), 1 for day (sun), range 0..1."""

    def setUp(self):
        self.src = _read(BIOLOGICAL_AMBIENT)

    def test_the_negative_night_test_is_gone(self):
        # The engine never returns -1, so this test was always false.
        self.assertNotIn("sunOrMoon == -1", self.src)

    def test_the_night_half_of_the_transition_is_night(self):
        self.assertIn("sunOrMoon < 0.5", self.src)

    def test_night_factor_is_reduced_at_night(self):
        self.assertAlmostEqual(night_factor(0), 0.6)
        self.assertAlmostEqual(night_factor(0.2), 0.6)
        self.assertAlmostEqual(night_factor(1), 1.0)

    def test_the_mid_transition_switches_at_half(self):
        self.assertAlmostEqual(night_factor(0.49), 0.6)
        self.assertAlmostEqual(night_factor(0.5), 1.0)


# ─── M2: the engine nular is `gusts` ─────────────────────────────────────


class TestGustsCommand(unittest.TestCase):
    """BIKI `gusts`: "Return the current gusts value. Scale is 0 to 1."."""

    def setUp(self):
        self.src = _read(UPDATE_WIND)

    def test_the_engine_command_is_gusts(self):
        self.assertIn("isNil {gusts}", self.src)
        self.assertIn("_gusts = gusts;", self.src)

    def test_the_undefined_gust_name_is_gone(self):
        # `gust` is not a command in the command DB, so the guard was always
        # true and the engine gust signal never reached AEE.
        self.assertNotIn("isNil {gust}", self.src)
        self.assertNotIn("_gusts = gust;", self.src)

    def test_the_unit_is_recorded_as_the_engine_fraction(self):
        # The published value is the engine 0..1 fraction times the gust
        # frequency (0..2).  The consumer that reads it as m/s is named.
        self.assertIn("Scale is 0 to 1", self.src)
        self.assertIn("fnc_applyFlightTurbulence", self.src)


# ─── M3: the engine wave scale is the world's MaxWave ────────────────────


def engine_waves(wave_h_m, world_max_wave=0.25):
    """Mirror of fnc_updateEngineWaves with the world wave scale."""
    return min(max(0.0, wave_h_m), world_max_wave) / world_max_wave


class TestEngineWaveScale(unittest.TestCase):
    """CfgWorlds >> Sea >> MaxWave declares the metre scale of `waves`."""

    def setUp(self):
        self.src = _read(ENGINE_WAVES)

    def test_the_world_field_is_read(self):
        self.assertIn(
            'getNumber (configFile >> "CfgWorlds" >> worldName >> "Sea" >> "MaxWave")',
            self.src,
        )

    def test_the_hard_coded_15_metres_is_gone(self):
        self.assertNotIn("_fullScaleMetres = 15", self.src)

    def test_the_world_fallback_is_the_altis_value(self):
        self.assertIn("_worldMaxWave = 0.25;", self.src)

    def test_a_flat_sea_maps_to_zero(self):
        self.assertAlmostEqual(engine_waves(0.0), 0.0)

    def test_the_world_scale_maps_to_one(self):
        # Altis MaxWave is 0.25 m: the engine's own full scale for the world.
        self.assertAlmostEqual(engine_waves(0.25), 1.0)

    def test_the_engine_value_saturates_above_the_world_scale(self):
        self.assertAlmostEqual(engine_waves(15.0), 1.0)

    def test_the_old_scale_overstated_the_sea(self):
        # Against Altis, the old 15 m full scale gave 0.0167 where the world
        # scale gives 1.0 for the same height: about 60x.
        self.assertGreater(engine_waves(0.25) / (0.25 / 15), 59)


# ─── M1: fogForecast is a Number, not an array ───────────────────────────


class TestFogForecastRead(unittest.TestCase):
    """BIKI `fogForecast`: a Number, "0 means no fog, 1 means maximum fog"."""

    def setUp(self):
        self.src = _read(UPDATE_FOG)

    def test_the_array_guard_on_fogForecast_is_gone(self):
        self.assertNotIn("_forecast isEqualType []", self.src)

    def test_the_number_is_read_and_the_published_shape_is_kept(self):
        self.assertIn("private _forecastFog = fogForecast;", self.src)
        self.assertIn(
            "setVariable [QEGVAR(core,fogForecast), [_forecastFog, 0.5, 0]]",
            self.src,
        )

    def test_a_missing_forecast_falls_back_to_the_model_density(self):
        self.assertIn(
            "if !(_forecastFog isEqualType 0) then { _forecastFog = _fogDensity; };",
            self.src,
        )


# ─── Environment: the snow drift ramp reaches the declared 0..1 ──────────


def drift_intensity(wind_spd):
    """Mirror of the drift ramp in fnc_calculateSnowAccumulation."""
    if wind_spd <= 8:
        return 0.0
    return max(0.0, min((wind_spd - 8) / 8, 1.0))


class TestSnowDriftRamp(unittest.TestCase):
    """The header declares 0..1; the old `* 0.001` reached at most 0.03."""

    def setUp(self):
        self.src = _read(SNOW)

    def test_the_old_scale_is_gone(self):
        self.assertNotIn("(_windSpd * 0.001)", self.src)

    def test_the_ramp_is_the_excess_over_the_threshold(self):
        self.assertIn("((_windSpd - 8) / 8) min 1.0", self.src)

    def test_calm_wind_carries_no_drift(self):
        self.assertAlmostEqual(drift_intensity(8), 0.0)

    def test_half_the_declared_range_at_12_metres_per_second(self):
        self.assertAlmostEqual(drift_intensity(12), 0.5)

    def test_the_range_saturates_at_twice_the_threshold(self):
        self.assertAlmostEqual(drift_intensity(16), 1.0)
        self.assertAlmostEqual(drift_intensity(30), 1.0)

    def test_the_declared_range_is_reached(self):
        self.assertGreater(drift_intensity(16), 0.99)


# ─── Environment: the orphan space-weather writes have a consumer ────────


class TestSpaceWeatherConsumer(unittest.TestCase):
    """The five published values were written and never read."""

    ORPHANS = (
        "solarActivity",
        "geomagneticDescription",
        "xrayFlux",
        "flareClass",
        "auroraElevationDeg",
    )

    def setUp(self):
        self.dump = _read(ATMOS_DUMP)
        self.producer = _read(SPACE_WEATHER)

    def test_the_producer_still_publishes_them(self):
        for name in self.ORPHANS:
            with self.subTest(value=name):
                self.assertIn(f"setVariable [QGVAR({name})", self.producer)

    def test_the_state_line_reads_every_one(self):
        for name in self.ORPHANS:
            with self.subTest(value=name):
                self.assertIn(f"QEGVAR(weather,{name})", self.dump)

    def test_the_state_line_carries_the_values(self):
        for token in (
            "_geomagnetic",
            "_solarActivity",
            "_xrayFlux",
            "_flareClass",
            "_auroraEdge",
        ):
            with self.subTest(value=token):
                self.assertIn(token, self.dump.split('"atmos state', 1)[1])
        self.assertIn("%25", self.dump)


# ─── Environment: station identifiers ───────────────────────────────────


class TestClimateStationIds(unittest.TestCase):
    """A WIGOS station identifier is `0-20000-0-XXXXX`."""

    def setUp(self):
        self.ids = _station_ids(_read(STATIONS))

    def test_no_empty_wigos_prefix(self):
        self.assertNotIn("WIGOS ", self.ids)

    def test_no_dash_placeholder_wigos(self):
        self.assertNotIn("WIGOS -", self.ids)

    def test_no_identifier_is_an_empty_or_dash_tail(self):
        # The NOAA composite carries no identifier for a few stations, so the
        # defect is the emitter printing a bare "WIGOS " prefix.  The other
        # identifiers are quoted verbatim from the composite and are not this
        # mod's to rewrite.
        for sid in self.ids:
            with self.subTest(value=sid):
                if sid:
                    tail = sid.removeprefix("WIGOS ").strip()
                    self.assertTrue(tail, f"empty WIGOS tail: {sid!r}")
                    self.assertNotEqual(tail, "-")


# ─── Environment: citations and labels ──────────────────────────────────


class TestFogBaseAttribution(unittest.TestCase):
    """17.62/243.12 is the WMO-No. 8 Annex 4.B Magnus pair, not Sonntag."""

    def setUp(self):
        self.src = _read(FOG_BASE)

    def test_the_wrong_attribution_is_gone(self):
        self.assertNotIn("Magnus dew point (Sonntag 1990", self.src)

    def test_the_correct_source_is_cited(self):
        self.assertIn("WMO-No. 8 Annex 4.B", self.src)


class TestTwilightLabel(unittest.TestCase):
    """-12 deg is the end of nautical twilight, not nautical twilight itself."""

    def setUp(self):
        self.src = _read(SPACE_WEATHER)

    def test_the_wrong_label_is_gone(self):
        self.assertNotIn("sun below -12 deg (nautical twilight)", self.src)

    def test_the_boundary_is_named(self):
        self.assertIn("end of\nnautical twilight", self.src)
        self.assertIn("astronomical", self.src)


class TestLatitudeClimateComments(unittest.TestCase):
    """The header must state the values the code actually produces."""

    def setUp(self):
        self.src = _read(LATITUDE_CLIMATE)

    def test_the_diurnal_range_matches_the_code(self):
        # _diurnal = 8 + 5*exp(-((lat-30)^2)/250)*(1 - lat/90), forced to 8
        # below 10 deg: 11.33 C at 30 deg, 8.05 C at 60 deg.
        self.assertNotIn("13 C at 30 deg", self.src)
        self.assertIn("11.3 C at 30 deg", self.src)
        self.assertIn("8.0 C at 60+ deg", self.src)

    def test_the_base_latitude_matches_the_code(self):
        self.assertNotIn("27 - 0.42*lat", self.src)
        self.assertIn("26 - 0.40*lat", self.src)

    def test_the_diurnal_formula_is_unchanged(self):
        self.assertIn(
            "8 + 5 * exp (-((_lat - 30) ^ 2) / 250) * (1 - _lat / 90)", self.src
        )


class TestLunarHeader(unittest.TestCase):
    """The header must describe the body: it returns the phase, and writes
    only lunarPhase."""

    def setUp(self):
        self.src = _read(LUNAR)

    def test_the_header_does_not_claim_ambient_lux(self):
        self.assertNotIn("QGVAR(ambientLux)", self.src)

    def test_the_header_names_the_real_outputs(self):
        self.assertIn("Sets  QGVAR(lunarPhase).", self.src)


if __name__ == "__main__":
    unittest.main()
