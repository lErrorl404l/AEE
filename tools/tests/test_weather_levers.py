#!/usr/bin/env python3
"""Unused engine weather levers: phase, cloud structure, wind aloft, temperature.

Four levers the engine exposes were unused. This suite pins each bridge and
the command facts it relies on, and it cross-checks those facts against the
local acemod/arma3-wiki command DB when the DB is present (the check skips
when it is absent, as the other engine suites do).

Levers:
  * ``setRain [rainParams]`` snow form (syntax 2, Arma 3 2.08): the only
    precipitation-phase render path. Element 15 is the ``snow`` flag.
  * ``simulSetHumidity`` (working 2.18) plus the read-only probe
    ``simulInClouds`` / ``simulCloudDensity``.
  * ``enableEnvironment [.., .., windyCoef]`` (``windyCoef`` 2.12): wind aloft.
  * ``ambientTemperature`` (2.06): the engine black/white surface pair, read.

Deliberately NOT written: ``setGusts`` (ADR-041) and any air-temperature
setter (none exists).

Run: python3 -m unittest tools.tests.test_weather_levers
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ATMOS = REPO / "addons" / "atmos" / "functions"
THERMAL = REPO / "addons" / "thermal" / "functions" / "environment"
CORE = REPO / "addons" / "core" / "functions"

SNOW_KERNEL = ATMOS / "physics" / "fnc_calculateSnowRainParams.sqf"
PHASE = ATMOS / "state" / "fnc_applyPrecipitationPhase.sqf"
SIMUL = ATMOS / "state" / "fnc_updateSimulWeather.sqf"
WINDY = ATMOS / "state" / "fnc_updateWindyCoef.sqf"
ENGINE_TEMP = THERMAL / "fnc_readEngineAmbientTemperature.sqf"
WARN = CORE / "fnc_warnManualOverride.sqf"
WAVES = REPO / "addons" / "maritime" / "functions" / "fnc_updateEngineWaves.sqf"
LIGHTNINGS = ATMOS / "state" / "fnc_updateEngineLightnings.sqf"
ICING = ATMOS / "physics" / "fnc_calculateAirframeIcing.sqf"
TURBULENCE = ATMOS / "physics" / "fnc_calculateTurbulence.sqf"
TICK = CORE / "fnc_updateEnvironment.sqf"
ATMOS_PREP = REPO / "addons" / "atmos" / "XEH_PREP.hpp"

DB = Path.home() / ".local" / "share" / "arma3-wiki" / "commands"

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _code_only(text: str) -> str:
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


def _top_level_split(array_text: str) -> list[str]:
    """Split the body of an SQF array on its top-level commas."""
    parts: list[str] = []
    depth = 0
    current = ""
    in_string = False
    for ch in array_text:
        if ch == '"':
            in_string = not in_string
        if not in_string:
            if ch in "[(":
                depth += 1
            elif ch in "])":
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append(current.strip())
                current = ""
                continue
        current += ch
    if current.strip():
        parts.append(current.strip())
    return parts


def snow_params() -> list[str]:
    """The 17-element array the pure kernel returns."""
    body = _code_only(_read(SNOW_KERNEL))
    start = body.index("[")
    end = body.rindex("]")
    return _top_level_split(body[start + 1 : end])


class TestSnowRainParams(unittest.TestCase):
    """The RainParticles array, in the order the DB `rainParams` page lists."""

    ELEMENTS = 17
    SNOW_FLAG = 15

    def test_the_array_has_the_documented_length(self) -> None:
        self.assertEqual(len(snow_params()), self.ELEMENTS)

    def test_the_snow_flag_is_set(self) -> None:
        self.assertEqual(snow_params()[self.SNOW_FLAG], "true")

    def test_the_shipped_texture_and_its_drop_count_agree(self) -> None:
        # The DB names snowflake4/8/16 with drop counts 4/8/16.  The 4-flake
        # atlas pairs with texDropCount 4.
        self.assertEqual(snow_params()[0], '"a3\\data_f\\snowflake4_ca.paa"')
        self.assertEqual(snow_params()[1], "4")


class TestPhaseBridge(unittest.TestCase):
    def setUp(self) -> None:
        self.live = _code_only(_read(PHASE))

    def test_client_only(self) -> None:
        self.assertIn("if (!hasInterface) exitWith", self.live)

    def test_writes_the_params_form_and_the_reset(self) -> None:
        self.assertIn("setRain (call FUNC(calculateSnowRainParams))", self.live)
        self.assertIn("setRain []", self.live)

    def test_only_the_snow_phase_draws_snow(self) -> None:
        self.assertIn('private _snow = (_phase == "snow")', self.live)

    def test_one_write_per_phase_change(self) -> None:
        self.assertRegex(
            self.live,
            r"if \(_written isEqualTo _phase\) exitWith",
            "the bridge rewrites the params every tick",
        )

    def test_runs_from_the_environment_tick(self) -> None:
        self.assertIn("EFUNC(atmos,applyPrecipitationPhase)", _read(TICK))

    def test_prepped(self) -> None:
        prep = _read(ATMOS_PREP)
        self.assertIn("PREPS(state,applyPrecipitationPhase)", prep)
        self.assertIn("PREPS(physics,calculateSnowRainParams)", prep)


class TestSimulWeather(unittest.TestCase):
    def setUp(self) -> None:
        self.live = _code_only(_read(SIMUL))

    def test_client_only(self) -> None:
        self.assertIn("if (!hasInterface) exitWith", self.live)

    def test_sets_the_cloud_structure_axis(self) -> None:
        self.assertIn("simulSetHumidity (", self.live)

    def test_probe_reads_both_commands(self) -> None:
        self.assertIn("simulInClouds _pos", self.live)
        self.assertIn("simulCloudDensity _pos", self.live)

    def test_publishes_the_probe(self) -> None:
        self.assertIn("QEGVAR(core,simulInClouds)", self.live)
        self.assertIn("QEGVAR(core,simulCloudDensity)", self.live)

    def test_gated_on_the_simul_setting(self) -> None:
        self.assertIn("simulWeatherLayers", self.live)

    def test_runs_from_the_environment_tick(self) -> None:
        self.assertIn("EFUNC(atmos,updateSimulWeather)", _read(TICK))

    def test_prepped(self) -> None:
        self.assertIn("PREPS(state,updateSimulWeather)", _read(ATMOS_PREP))


class TestProbeConsumers(unittest.TestCase):
    """The icing and turbulence models take the real in-cloud probe."""

    def test_icing_reads_the_probe(self) -> None:
        live = _code_only(_read(ICING))
        self.assertIn("QEGVAR(core,simulCloudDensity)", live)
        self.assertIn("QEGVAR(core,simulInClouds)", live)

    def test_turbulence_is_the_boundary_layer_dissipation(self) -> None:
        # In-cloud turbulence has no held law; the EDR is the boundary-layer
        # dissipation (fnc_turbulenceDissipation).
        self.assertIn("FUNC(turbulenceDissipation)", _code_only(_read(TURBULENCE)))


class TestWindyCoef(unittest.TestCase):
    def setUp(self) -> None:
        self.live = _code_only(_read(WINDY))

    def test_client_only(self) -> None:
        self.assertIn("if (!hasInterface) exitWith", self.live)

    def test_sets_the_three_element_form(self) -> None:
        self.assertIn(
            "enableEnvironment [environmentEnabled, environmentEnabled, _coef]",
            self.live,
        )

    def test_preserves_the_ambient_switches(self) -> None:
        # AEE does not own ambient life or sound: the engine state is passed
        # through instead of forcing true.
        self.assertNotIn("enableEnvironment [true", self.live)

    def test_clamped_to_the_engine_range(self) -> None:
        self.assertIn("max 0 min 1", self.live)

    def test_uses_the_modelled_wind_at_height(self) -> None:
        self.assertIn("FUNC(getLocalWind)", self.live)
        self.assertIn("getTerrainHeightASL", self.live)

    def test_prepped(self) -> None:
        self.assertIn("PREPS(state,updateWindyCoef)", _read(ATMOS_PREP))


class TestManualOverrideVerdict(unittest.TestCase):
    def test_both_bridges_warn(self) -> None:
        for path in (WAVES, LIGHTNINGS):
            with self.subTest(path=path.name):
                self.assertIn("EFUNC(core,warnManualOverride)", _read(path))

    def test_the_warning_fires_once(self) -> None:
        live = _code_only(_read(WARN))
        self.assertIn("QGVAR(manualOverrideWarned)", live)
        self.assertRegex(
            live,
            r"getVariable \[QGVAR\(manualOverrideWarned\), false\]\) exitWith",
        )

    def test_the_verdict_is_the_command_db_wording(self) -> None:
        # The DB states the flag; no command reads or sets it.
        for path in (WAVES, LIGHTNINGS):
            with self.subTest(path=path.name):
                self.assertIn("Manual Override", _read(path))


class TestEngineTemperature(unittest.TestCase):
    def setUp(self) -> None:
        self.live = _code_only(_read(ENGINE_TEMP))

    def test_reads_the_engine_triple(self) -> None:
        self.assertIn("ambientTemperature", self.live)

    def test_publishes_air_black_and_white(self) -> None:
        self.assertIn("QEGVAR(core,engineAirTemperature)", self.live)
        self.assertIn("QEGVAR(core,engineBlackSurfaceTemperature)", self.live)
        self.assertIn("QEGVAR(core,engineWhiteSurfaceTemperature)", self.live)

    def test_writes_no_engine_temperature(self) -> None:
        # The engine has no air-temperature setter (command DB), so the bridge
        # must not invent one.
        self.assertNotIn("setAmbientTemperature", self.live)


class TestNoGustsWriter(unittest.TestCase):
    def test_the_new_code_does_not_write_gusts(self) -> None:
        for path in (PHASE, SIMUL, WINDY, ENGINE_TEMP):
            with self.subTest(path=path.name):
                self.assertNotIn("setGusts", _code_only(_read(path)))


class TestCommandDbCrossCheck(unittest.TestCase):
    """Cross-check the command facts against the local command DB.

    The DB is a machine-local checkout of acemod/arma3-wiki, so the check
    skips where it is absent. It never fails for its absence.
    """

    def _page(self, command: str) -> str:
        if not (DB / f"{command}.yml").is_file():
            self.skipTest(f"command DB not present: {DB}")
        return (DB / f"{command}.yml").read_text(encoding="utf-8")

    def test_setrain_has_the_params_form_since_2_8(self) -> None:
        page = self._page("setRain")
        self.assertIn("RainParticles", page)
        self.assertRegex(page, r"major:\s*2\s*\n\s*minor:\s*8")

    def test_rainparams_lists_the_snow_flag(self) -> None:
        self.assertIn("_snow", self._page("rainParams"))

    def test_simulsetHumidity_is_the_cloud_cover_setter(self) -> None:
        page = self._page("simulSetHumidity")
        self.assertIn("simul cloud cover", page)
        self.assertIn("2.18", page)

    def test_the_probe_commands_exist(self) -> None:
        self.assertIn("in clouds", self._page("simulInClouds"))
        self.assertIn("density", self._page("simulCloudDensity").lower())

    def test_windycoef_is_since_2_12(self) -> None:
        page = self._page("enableEnvironment")
        self.assertIn("windyCoef", page)
        self.assertRegex(page, r"major:\s*2\s*\n\s*minor:\s*12")

    def test_ambienttemperature_is_since_2_6_and_read_only(self) -> None:
        page = self._page("ambientTemperature")
        self.assertRegex(page, r"major:\s*2\s*\n\s*minor:\s*6")
        self.assertIn("blackSurfaceTemperature", page)

    def test_waves_and_lightnings_need_manual_override(self) -> None:
        for command in ("setWaves", "setLightnings"):
            with self.subTest(command=command):
                self.assertIn("Manual Override", self._page(command))

    def test_no_command_sets_the_manual_override_flag(self) -> None:
        if not DB.is_dir():
            self.skipTest(f"command DB not present: {DB}")
        setters = [
            path.name
            for path in DB.glob("*.yml")
            if re.search(r"(?i)manualOverride", path.read_text(encoding="utf-8"))
        ]
        self.assertEqual(setters, [], f"a command exposes the flag: {setters}")


if __name__ == "__main__":
    unittest.main()
