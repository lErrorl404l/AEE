#!/usr/bin/env python3
"""Source precedence tests for the vehicle binder (tools/validation/gen_vehicle_bindings.py).

A mod root must add classes and never shadow a game class. The binder reads
every game source before any mod source, and the mod roots keep the order they
are given. These tests pin that contract on the packing and loose passes.

They build a temporary game root and temporary mod roots. The packed test
creates empty ``.pbo`` files, which are globbed by name and never read. The
loose test creates only ``config.cpp`` files, so no packed addon is inspected
and no game install is needed.

Run: python3 -m unittest tools.tests.test_vehicle_bindings_order -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_vehicle_bindings as g  # noqa: E402


class ScanPbosTest(unittest.TestCase):
    def _roots(self, tmp: Path) -> tuple[Path, Path, Path]:
        game = tmp / "Arma 3"
        (game / "Addons").mkdir(parents=True)
        for name in ("soft_f.pbo", "weapons_f.pbo", "other.pbo"):
            (game / "Addons" / name).write_bytes(b"")
        low = tmp / "735566597"
        low.mkdir()
        (low / "po_main.pbo").write_bytes(b"")
        high = tmp / "843425103"
        high.mkdir()
        (high / "rhs_c_a2port_car.pbo").write_bytes(b"")
        return game, low, high

    def test_game_packs_precede_every_mod_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game, low, high = self._roots(Path(tmp))
            order = [loc for loc, _ in g._scan_pbos(game, [low, high])]
        # A lower numeric mod id must not sort ahead of the game.
        self.assertEqual(
            order,
            [
                "Addons/soft_f.pbo",
                "Addons/weapons_f.pbo",
                "735566597/po_main.pbo",
                "843425103/rhs_c_a2port_car.pbo",
            ],
        )

    def test_mod_order_is_the_cli_order_not_the_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game, low, high = self._roots(Path(tmp))
            order = [loc for loc, _ in g._scan_pbos(game, [high, low])]
        self.assertEqual(
            order[-2:],
            [
                "843425103/rhs_c_a2port_car.pbo",
                "735566597/po_main.pbo",
            ],
        )

    def test_game_pass_keeps_the_vehicle_addon_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game, low, high = self._roots(Path(tmp))
            order = [loc for loc, _ in g._scan_pbos(game, [low, high])]
        self.assertNotIn("Addons/other.pbo", order)


class ConfigTextsTest(unittest.TestCase):
    def test_every_game_source_precedes_every_mod_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = root / "Arma 3"
            game.mkdir()
            (game / "config.cpp").write_text("class CfgPatches {};\n", encoding="utf-8")
            low = root / "735566597"
            low.mkdir()
            (low / "config.cpp").write_text("class CfgPatches {};\n", encoding="utf-8")
            high = root / "843425103"
            high.mkdir()
            (high / "config.cpp").write_text("class CfgPatches {};\n", encoding="utf-8")
            locators = [
                loc for loc, _ in g._config_texts(game, root / "scratch", [high, low])
            ]
        game_at = locators.index("config.cpp")
        self.assertLess(game_at, locators.index("843425103/config.cpp"))
        self.assertLess(game_at, locators.index("735566597/config.cpp"))
        self.assertLess(
            locators.index("843425103/config.cpp"),
            locators.index("735566597/config.cpp"),
        )


if __name__ == "__main__":
    raise SystemExit(unittest.main())
