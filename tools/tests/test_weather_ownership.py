#!/usr/bin/env python3
"""Single-owner contract for the engine weather.

AEE gives each engine weather quantity exactly one writer, so a modelled value
is not overwritten by a second model on the same machine (ADR-041). The
lighting binder used to write `setHumidity` and `setGusts` on the server behind
`aee_lighting_weatherOwnership`; that write is retired. Humidity is now owned by
the atmos writer, per client, and the engine owns the gust signal outright.

This suite pins three facts the code and the documentation must keep:

  * the retired lighting write is gone, and nothing writes `setGusts`;
  * the single humidity writer is the atmos engine-weather writer;
  * the ownership table in ``docs/engine/engine-weather-writer.md`` names, for
    every quantity, the one file that writes it, and that file writes it.

Run: python3 -m unittest tools.tests.test_weather_ownership
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"
DOC = REPO / "docs" / "engine" / "engine-weather-writer.md"
LIGHTING = ADDONS / "lighting" / "functions" / "lighting" / "fnc_applyWorldLighting.sqf"
ATMOS_WRITER = ADDONS / "atmos" / "functions" / "state" / "fnc_applyEngineWeather.sqf"
CONFIG_DOC = REPO / "docs" / "wiki" / "chapters" / "configuration.qmd"

# The quantities the table must cover, with the command token each row pins.
REQUIRED = {
    "wind": "setWind",
    "gusts": "setGusts",
    "humidity": "setHumidity",
    "overcast": "setOvercast",
    "rain": "setRain",
    "fog": "setFog",
    "waves": "setWaves",
}

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_TABLE_HEADER = "| Quantity | Command | Command locality | Owner |"
_BACKTICKED = re.compile(r"`([^`]+)`")


def code_only(text: str) -> str:
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


def sqf_sources() -> list[Path]:
    return sorted(ADDONS.rglob("*.sqf"))


def ownership_rows() -> list[list[str]]:
    """The rows of the ownership table in the engine weather writer doc.

    Rows are [quantity, command, locality, owner]. The table starts at its
    header row and ends at the first non-table line, so the other tables in
    the page are never read.
    """
    lines = DOC.read_text(encoding="utf-8").splitlines()
    start = lines.index(_TABLE_HEADER)
    rows: list[list[str]] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 4:
            rows.append(cells)
    return rows


class TestRetiredWriteGone(unittest.TestCase):
    def test_lighting_writes_no_engine_weather(self) -> None:
        live = code_only(LIGHTING.read_text(encoding="utf-8"))
        self.assertNotIn(
            "setHumidity", live, "the lighting binder still writes humidity"
        )
        self.assertNotIn("setGusts", live, "the lighting binder still writes gusts")

    def test_no_addon_writes_setgusts(self) -> None:
        writers = [
            p
            for p in sqf_sources()
            if "setGusts" in code_only(p.read_text(encoding="utf-8"))
        ]
        self.assertEqual(
            writers, [], "the engine owns the gust signal; nothing writes setGusts"
        )

    def test_the_retired_setting_is_gone_everywhere(self) -> None:
        hits = [
            p.as_posix()
            for p in ADDONS.rglob("*")
            if p.is_file()
            and "weatherOwnership" in p.read_text(encoding="utf-8", errors="replace")
        ]
        self.assertEqual(
            hits, [], f"aee_lighting_weatherOwnership still referenced: {hits}"
        )
        self.assertNotIn(
            "aee_lighting_weatherOwnership", CONFIG_DOC.read_text(encoding="utf-8")
        )


class TestSingleOwner(unittest.TestCase):
    def test_humidity_owner_is_the_atmos_writer(self) -> None:
        self.assertIn(
            "setHumidity (", code_only(ATMOS_WRITER.read_text(encoding="utf-8"))
        )

    def test_humidity_has_exactly_one_writer(self) -> None:
        writers = [
            p
            for p in sqf_sources()
            if "setHumidity" in code_only(p.read_text(encoding="utf-8"))
        ]
        self.assertEqual(writers, [ATMOS_WRITER])


class TestOwnershipTableMatchesTheCode(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = ownership_rows()

    def test_the_table_covers_every_required_quantity(self) -> None:
        quantities = {row[0] for row in self.rows}
        missing = set(REQUIRED) - quantities
        self.assertEqual(missing, set(), f"the ownership table omits {sorted(missing)}")

    def test_every_row_names_the_command_and_the_owner_file(self) -> None:
        for quantity, command, _locality, owner in self.rows:
            with self.subTest(quantity=quantity):
                self.assertEqual(
                    command.strip("`"),
                    REQUIRED.get(quantity, command.strip("`")),
                    f"{quantity} names the wrong command",
                )
                if owner.lower().startswith("none"):
                    continue
                self.assertTrue(
                    _BACKTICKED.search(owner),
                    f"{quantity} names no owner file",
                )

    def test_each_owner_file_writes_its_command(self) -> None:
        for quantity, command, _locality, owner in self.rows:
            token = command.strip("`")
            if owner.lower().startswith("none"):
                with self.subTest(quantity=quantity):
                    self.assertEqual(
                        REQUIRED[quantity], token, "the no-owner row is not gusts"
                    )
                    continue
            path = REPO / _BACKTICKED.search(owner).group(1)
            with self.subTest(quantity=quantity):
                self.assertTrue(
                    path.is_file(), f"{quantity} owner does not exist: {path}"
                )
                self.assertIn(
                    token,
                    code_only(path.read_text(encoding="utf-8")),
                    f"{path} does not write {token}",
                )


if __name__ == "__main__":
    unittest.main()
