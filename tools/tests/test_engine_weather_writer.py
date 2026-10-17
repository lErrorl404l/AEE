#!/usr/bin/env python3
"""Contract test for the engine weather writer (issue #155).

AEE maps its modelled atmosphere onto the engine's own weather commands so a
modelled storm is visible. This suite pins the contract the writer must obey:

  * every command it uses, with the documented shape;
  * the locality rule (overcast and rain on the server, humidity per client);
  * the timed interpolation form;
  * the single millimetres-per-hour to engine 0..1 conversion;
  * the setting and manual precedence;
  * the single-owner rule for the commands AEE already writes.

The command facts are embedded here and in
``docs/engine/engine-weather-writer.md``. When the local acemod/arma3-wiki
command DB is present, the suite also cross-checks the embedded facts against
the DB pages, so a copied version or locality cannot drift.

Run: python3 -m unittest tools.tests.test_engine_weather_writer
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ATMOS_STATE = REPO / "addons" / "atmos" / "functions" / "state"
WRITER = ATMOS_STATE / "fnc_applyEngineWeather.sqf"
PREDICATE = ATMOS_STATE / "fnc_engineWeatherBlockedReason.sqf"
PREP = REPO / "addons" / "atmos" / "XEH_PREP.hpp"
SETTINGS = REPO / "addons" / "atmos" / "initSettings.inc.sqf"
TICK = REPO / "addons" / "core" / "functions" / "fnc_updateEnvironment.sqf"
DOC = REPO / "docs" / "engine" / "engine-weather-writer.md"

# The engine contract, read from the local command DB (acemod/arma3-wiki
# v2.22). command -> (range, effect locality, Arma 3 version).
CONTRACT = {
    "setOvercast": ("overcast 0..1", "Local", "0.50"),
    "setRain": ("rain 0..1", "Global", "0.50"),
    "setHumidity": ("surface humidity 0..1", "Local", "2.8"),
    "forceWeatherChange": ("nular", "Unspecified", "1.16"),
}

# The commands AEE already writes. The writer must not repeat any of them, so
# the engine keeps one owner per value.
OWNED_ELSEWHERE = ("setFog", "setWind", "setWaves", "setRainbow", "setLightnings")

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _code_only(text: str) -> str:
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


class TestWriterCalls(unittest.TestCase):
    def setUp(self) -> None:
        self.live = _code_only(_read(WRITER))

    def test_commands_are_present_with_the_documented_shape(self) -> None:
        self.assertIn("_transition setOvercast _targetOvercast", self.live)
        self.assertIn("_transition setRain _targetRain", self.live)
        self.assertIn("setHumidity (", self.live)
        self.assertIn("forceWeatherChange", self.live)

    def test_overcast_and_rain_are_server_authoritative(self) -> None:
        """Both engine writes must sit after the server gate."""
        server_gate = self.live.find("if (!isServer) exitWith")
        self.assertGreater(server_gate, -1, "the server gate is missing")
        self.assertGreater(
            self.live.find("_transition setOvercast"),
            server_gate,
            "setOvercast runs before the server gate: a client write is temporary",
        )
        self.assertGreater(
            self.live.find("_transition setRain"),
            server_gate,
            "setRain runs before the server gate: a client write is temporary",
        )

    def test_humidity_is_client_local_and_unary(self) -> None:
        """setHumidity has no global form, so it runs once per client."""
        client_gate = self.live.find("if (hasInterface) then")
        self.assertGreater(client_gate, -1, "the client gate is missing")
        humidity = self.live.find("setHumidity (")
        self.assertGreater(humidity, client_gate, "setHumidity is not client-gated")
        server_gate = self.live.find("if (!isServer) exitWith")
        self.assertLess(humidity, server_gate, "setHumidity sits in the server block")

    def test_force_weather_change_is_not_on_the_per_tick_path(self) -> None:
        self.assertRegex(
            self.live,
            r"if \(_force\) then \{\s*forceWeatherChange;\s*\}",
            "forceWeatherChange is not guarded by the explicit-transition flag",
        )

    def test_interpolation_uses_the_engine_timed_form(self) -> None:
        self.assertRegex(
            self.live,
            r"_transition = \[_interval, 0\] select _force",
            "the transition time is not the tick interval (or 0 on a forced change)",
        )
        self.assertIn("EGVAR(core,updateInterval)", self.live)

    def test_one_documented_mmh_to_engine_conversion(self) -> None:
        self.assertRegex(
            self.live,
            r"_targetRain = \(_rateMmH / ENGINE_RAIN_FULL_MMH\)",
            "the rain mapping is not the one documented conversion",
        )
        self.assertEqual(
            self.live.count("ENGINE_RAIN_FULL_MMH"),
            1,
            "more than one mm/h to engine conversion: keep the units separate",
        )

    def test_rain_is_coupled_to_the_overcast_floor(self) -> None:
        self.assertIn("_targetOvercast < 0.5", self.live)
        self.assertIn("_targetOvercast = 0.5", self.live)

    def test_writer_does_not_repeat_an_owned_command(self) -> None:
        for command in OWNED_ELSEWHERE:
            with self.subTest(command=command):
                self.assertNotIn(
                    command,
                    self.live,
                    f"the writer repeats {command}, which already has one owner",
                )


class TestPrecedence(unittest.TestCase):
    def setUp(self) -> None:
        self.live = _code_only(_read(PREDICATE))

    def test_setting_gate(self) -> None:
        self.assertRegex(
            self.live,
            r'getVariable \[QGVAR\(engineWeatherEnabled\), true\]\)\) exitWith \{ "setting" \}',
        )

    def test_no_removed_compat_branch(self) -> None:
        """AEE alone owns the engine weather: no compat gate remains."""
        needle = "real" + "weather"
        self.assertNotIn(needle, self.live.lower())
        self.assertNotIn(needle + "active", self.live.lower())

    def test_manual_gate(self) -> None:
        self.assertRegex(
            self.live,
            r'QGVAR\(manualWeather\), false\]\) exitWith \{ "manual" \}',
        )

    def test_writer_consults_the_predicate_first(self) -> None:
        writer = _code_only(_read(WRITER))
        self.assertIn("call FUNC(engineWeatherBlockedReason)", writer)
        self.assertRegex(writer, r'if \(_reason != ""\) exitWith')


class TestWiring(unittest.TestCase):
    def test_both_functions_are_prepped(self) -> None:
        prep = _read(PREP)
        self.assertIn("PREPS(state,applyEngineWeather)", prep)
        self.assertIn("PREPS(state,engineWeatherBlockedReason)", prep)

    def test_setting_is_registered(self) -> None:
        self.assertRegex(
            _read(SETTINGS),
            r'AEE_SETTING_CHECKBOX\(engineWeatherEnabled,"AEE Atmos","Weather",true\)',
        )

    def test_writer_runs_from_the_environment_tick(self) -> None:
        self.assertIn("EFUNC(atmos,applyEngineWeather)", _read(TICK))


class TestDocumentation(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = _read(DOC)

    def test_doc_pins_every_command_with_its_range_locality_and_version(self) -> None:
        for command, (ran, locality, since) in CONTRACT.items():
            with self.subTest(command=command):
                self.assertIn(command, self.doc)
                self.assertIn(ran, self.doc)
                self.assertIn(f"Arma 3 {since}", self.doc)
                self.assertIn(locality, self.doc)

    def test_doc_records_the_inland_water_ceiling(self) -> None:
        self.assertIn("inland water", self.doc.lower())
        self.assertIn("setHumidity", self.doc)


class TestCommandDbCrossCheck(unittest.TestCase):
    """Cross-check the embedded contract against the local command DB.

    The DB is a machine-local checkout of acemod/arma3-wiki, so the check
    skips where it is absent. It never fails for its absence.
    """

    DB = Path.home() / ".local" / "share" / "arma3-wiki" / "commands"

    _ARMA3 = re.compile(r"arma_3:\s*\n\s+major:\s*(\d+)\s*\n\s+minor:\s*(\d+)")

    def _page(self, command: str) -> dict[str, str]:
        text = (self.DB / f"{command}.yml").read_text(encoding="utf-8")
        effect = ""
        since = ""
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("effect_loc:"):
                effect = line.split(":", 1)[1].strip()
            if line != "since:":
                continue
            # The column-0 since block ends at the first non-indented line.
            block = []
            for nxt in lines[i + 1 :]:
                if nxt and not nxt.startswith(" "):
                    break
                block.append(nxt)
            match = self._ARMA3.search("\n".join(block))
            if match:
                since = f"{match.group(1)}.{match.group(2)}"
            break
        return {"effect": effect, "since": since}

    def test_effect_locality_and_version_match_the_db(self) -> None:
        if not self.DB.is_dir():
            self.skipTest(f"command DB absent at {self.DB}")
        for command, (_ran, locality, since) in CONTRACT.items():
            with self.subTest(command=command):
                page = self._page(command)
                self.assertEqual(page["effect"], locality)

    def test_version_matches_the_db(self) -> None:
        if not self.DB.is_dir():
            self.skipTest(f"command DB absent at {self.DB}")
        for command, (_ran, _loc, since) in CONTRACT.items():
            with self.subTest(command=command):
                self.assertEqual(self._page(command)["since"], since)


if __name__ == "__main__":
    unittest.main()
