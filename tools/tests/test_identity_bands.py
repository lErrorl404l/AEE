#!/usr/bin/env python3
"""Identity property-band tests (the ballistics and clothing fallbacks).

Each generated band table is the property fallback of its matcher: a
weapon, cartridge, projectile or equipment item whose identity text
resolves to no catalogue alias is matched by its own live properties. The
shared selector ``aee_*_fnc_selectBand`` reads a table and the live
properties, and it never guesses.

The engine calls cannot run in this harness, so the selector rule is
mirrored here in Python and pinned against the same tables the SQF reads.
Each committed table is proven equal to a fresh render, so the mirror and
the SQF always select over the same rows. The matcher sources are checked
structurally for the fallback call and the PREP registration.

Run: python3 -m unittest tools.tests.test_identity_bands -v
"""

from __future__ import annotations

import ast
import contextlib
import io
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_equipment_data as gen_equipment  # noqa: E402
from tools.validation import gen_runtime_cartridges as gen_cartridges  # noqa: E402
from tools.validation import gen_runtime_projectiles as gen_projectiles  # noqa: E402
from tools.validation import gen_runtime_weapons as gen_weapons  # noqa: E402

BALLISTICS = REPO / "addons" / "ballistics" / "functions"
CLOTHING = REPO / "addons" / "physiology" / "functions" / "clothing"

WEAPON_MATCH = BALLISTICS / "fnc_getWeaponData.sqf"
CARTRIDGE_MATCH = BALLISTICS / "fnc_getCartridgeData.sqf"
PROJECTILE_MATCH = BALLISTICS / "fnc_getProjectileData.sqf"
EQUIPMENT_MATCH = CLOTHING / "fnc_getItemMass.sqf"

WEAPON_BANDS = BALLISTICS / "fnc_getWeaponBands.sqf"
CARTRIDGE_BANDS = BALLISTICS / "fnc_getCartridgeBands.sqf"
PROJECTILE_BANDS = BALLISTICS / "fnc_getProjectileBands.sqf"
EQUIPMENT_BANDS = CLOTHING / "fnc_getEquipmentBands.sqf"


def parse_table(path: Path) -> list[list[object]]:
    """Return the rows of a generated ``private _table`` block."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"private _table = \[(.*?)\n\];", text, re.S)
    if match is None:
        raise AssertionError(f"{path.name} has no band table")
    rows: list[list[object]] = []
    for line in match.group(1).strip().splitlines():
        line = line.strip().rstrip(",")
        if line.startswith("[") and line.endswith("]"):
            parsed = ast.literal_eval(line)
            if not isinstance(parsed, list):
                raise AssertionError(f"{path.name} row is not a list: {line}")
            rows.append(parsed)
    return rows


def select_band(rows, token, primary, secondary=0.0):
    """Mirror of aee_*_fnc_selectBand. Returns the row, or []."""
    if not rows or primary <= 0:
        return []
    held = [r[2] for r in rows if (token == "" or r[1] == token) and r[2] > 0]
    if not held:
        return []
    held.sort()
    gaps = []
    for index in range(len(held) - 1):
        if held[index] > 0:
            gaps.append((held[index + 1] - held[index]) / held[index])
    cap = -1.0
    if len(gaps) >= 2:
        gaps.sort()
        last = len(gaps) - 1
        q1 = gaps[int(last * 0.25)]
        q3 = gaps[int(last * 0.75)]
        cap = q3 + 1.5 * (q3 - q1)

    min_distance = min(abs(value - primary) for value in held)
    near: list[float] = []
    for value in held:
        if abs(value - primary) == min_distance and value not in near:
            near.append(value)
    if len(near) > 1:
        return []
    if cap >= 0 and min_distance > cap * near[0]:
        return []

    hits = 0
    best: list[object] = []
    min_secondary = -1.0
    for row in rows:
        if (
            (token == "" or row[1] == token)
            and row[2] > 0
            and abs(row[2] - primary) == min_distance
        ):
            secondary_distance = 0.0
            if row[3] > 0 and secondary > 0:
                secondary_distance = abs(row[3] - secondary)
            if min_secondary < 0 or secondary_distance < min_secondary:
                min_secondary = secondary_distance
                hits = 1
                best = row
            elif secondary_distance == min_secondary:
                hits += 1
    if hits == 1 and best:
        return best
    return []


def fresh(generator) -> int:
    """Run a generator's check mode without printing its report."""
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        try:
            return generator.check_outputs()
        except SystemExit as exit:  # pragma: no cover - defensive
            return int(exit.code or 0)


class TestSelectBandRule(unittest.TestCase):
    """The selector rule itself, on synthetic rows."""

    def test_nearest_primary_resolves(self):
        rows = [["a", "t", 10.0, 0], ["b", "t", 20.0, 0]]
        self.assertEqual(select_band(rows, "t", 21.0)[0], "b")

    def test_token_filters(self):
        rows = [["a", "x", 10.0, 0], ["b", "y", 10.0, 0]]
        self.assertEqual(select_band(rows, "y", 10.0)[0], "b")
        self.assertEqual(select_band(rows, "z", 10.0), [])

    def test_an_empty_token_accepts_every_row(self):
        rows = [["a", "x", 10.0, 0], ["b", "y", 20.0, 0]]
        self.assertEqual(select_band(rows, "", 20.0)[0], "b")

    def test_a_tie_between_distinct_values_selects_no_row(self):
        rows = [["a", "t", 10.0, 0], ["b", "t", 20.0, 0]]
        self.assertEqual(select_band(rows, "t", 15.0), [])

    def test_an_absent_primary_selects_no_row(self):
        rows = [["a", "t", 0, 0], ["b", "t", 0, 0]]
        self.assertEqual(select_band(rows, "t", 10.0), [])

    def test_secondary_breaks_a_primary_tie(self):
        rows = [["a", "t", 10.0, 1.0], ["b", "t", 10.0, 5.0]]
        # Both rows sit at the nearest primary. A held secondary picks one.
        self.assertEqual(select_band(rows, "t", 10.0, 4.5)[0], "b")
        # Without a secondary the pair is ambiguous.
        self.assertEqual(select_band(rows, "t", 10.0), [])

    def test_the_cap_refuses_an_outlying_live_value(self):
        # Held primaries at 1, 1.1, 1.2, 1.3 give a tight resolution. A live
        # value of 50 is outside the fence and selects no row.
        rows = [
            ["a", "t", 1.0, 0],
            ["b", "t", 1.1, 0],
            ["c", "t", 1.2, 0],
            ["d", "t", 1.3, 0],
        ]
        self.assertEqual(select_band(rows, "t", 50.0), [])


class TestBandTablesFresh(unittest.TestCase):
    """Each committed band table equals a fresh render of its generator."""

    def test_weapon_bands_fresh(self):
        self.assertEqual(fresh(gen_weapons), 0)

    def test_cartridge_bands_fresh(self):
        self.assertEqual(fresh(gen_cartridges), 0)

    def test_projectile_bands_fresh(self):
        self.assertEqual(fresh(gen_projectiles), 0)

    def test_equipment_bands_fresh(self):
        self.assertEqual(fresh(gen_equipment), 0)


class TestBandRows(unittest.TestCase):
    """Every row carries a non-empty identity and a primary column."""

    def check(self, path: Path, columns: int):
        rows = parse_table(path)
        self.assertGreater(len(rows), 0, f"{path.name} is empty")
        for row in rows:
            self.assertEqual(len(row), columns, f"{path.name} row width: {row}")
            self.assertTrue(row[0], f"{path.name} row has no id: {row}")

    def test_weapon(self):
        self.check(WEAPON_BANDS, 6)

    def test_cartridge(self):
        self.check(CARTRIDGE_BANDS, 9)

    def test_projectile(self):
        self.check(PROJECTILE_BANDS, 6)

    def test_equipment(self):
        self.check(EQUIPMENT_BANDS, 5)


class TestModdedItemsResolve(unittest.TestCase):
    """A modded item that the name tables miss resolves on its properties."""

    def test_a_modded_12_7x108_weapon_resolves(self):
        # The 12.7x108 chambering holds one catalogue weapon with a published
        # mass. A modded class in that chambering and at that mass resolves.
        row = select_band(parse_table(WEAPON_BANDS), "12_7_x_108", 16.7)
        self.assertEqual(row[0], "m93")

    def test_a_modded_460_weapon_resolves(self):
        row = select_band(parse_table(WEAPON_BANDS), "460_s_w_magnum", 2.809)
        self.assertEqual(row[0], "460xvr")

    def test_a_modded_145mm_round_resolves(self):
        row = select_band(parse_table(CARTRIDGE_BANDS), "", 14.5)
        self.assertEqual(row[0], "145x114")

    def test_a_modded_105mm_round_resolves(self):
        row = select_band(parse_table(CARTRIDGE_BANDS), "", 105.0)
        self.assertEqual(row[0], "105mm_m68")

    def test_a_modded_416_bullet_resolves(self):
        row = select_band(parse_table(PROJECTILE_BANDS), "", 10.57)
        self.assertEqual(row[0], "hornady_atip_416_500")

    def test_a_modded_helmet_resolves(self):
        row = select_band(parse_table(EQUIPMENT_BANDS), "helmet", 1.36)
        self.assertEqual(row[0], "ihps")

    def test_a_modded_vest_resolves(self):
        row = select_band(parse_table(EQUIPMENT_BANDS), "vest", 10.0)
        self.assertEqual(row[0], "spcs")


class TestMatcherWiring(unittest.TestCase):
    """Each matcher runs the band after its name ladder, never before."""

    def check_fallback(self, path: Path, bands_call: str):
        text = path.read_text(encoding="utf-8")
        self.assertIn("FUNC(selectBand)", text, f"{path.name} does not select a band")
        self.assertIn(bands_call, text, f"{path.name} does not read its band table")
        # The fallback guard: the band runs only when the name match is empty.
        self.assertIn("if (_match isEqualTo []) then {", text)

    def test_weapon(self):
        self.check_fallback(WEAPON_MATCH, "FUNC(getWeaponBands)")

    def test_cartridge(self):
        self.check_fallback(CARTRIDGE_MATCH, "FUNC(getCartridgeBands)")

    def test_projectile(self):
        self.check_fallback(PROJECTILE_MATCH, "FUNC(getProjectileBands)")

    def test_equipment(self):
        text = EQUIPMENT_MATCH.read_text(encoding="utf-8")
        self.assertIn("FUNC(selectBand)", text)
        self.assertIn("FUNC(getEquipmentBands)", text)
        self.assertIn('if ((_match == 0) && (_known != "")) then {', text)

    def test_selector_is_registered(self):
        ballistics = (REPO / "addons" / "ballistics" / "XEH_PREP.hpp").read_text(
            encoding="utf-8"
        )
        physiology = (REPO / "addons" / "physiology" / "XEH_PREP.hpp").read_text(
            encoding="utf-8"
        )
        for name in (
            "selectBand",
            "getWeaponBands",
            "getCartridgeBands",
            "getProjectileBands",
        ):
            self.assertIn(f"PREP({name});", ballistics, f"{name} is not registered")
        self.assertIn("PREPS(clothing,selectBand);", physiology)
        self.assertIn("PREPS(clothing,getEquipmentBands);", physiology)

    def test_the_selector_never_invents(self):
        # The selector returns the row or an empty array. There is no default
        # and no guessed identity.
        for path in (
            BALLISTICS / "fnc_selectBand.sqf",
            CLOTHING / "fnc_selectBand.sqf",
        ):
            text = path.read_text(encoding="utf-8")
            self.assertIn("_hits == 1", text, f"{path.name} has no ambiguity guard")
            self.assertIn("_nearCount > 1", text, f"{path.name} has no tie guard")
            self.assertIn("_cap", text, f"{path.name} has no resolution bound")


class TestNoProvenance(unittest.TestCase):
    """No agent, model or tooling provenance is committed in the artefacts."""

    def test_no_provenance(self):
        marked = (
            "Agent:",
            "opencode-go",
            "deepseek",
            "glm-",
            "anthropic",
            "claude",
        )
        for path in (
            WEAPON_MATCH,
            CARTRIDGE_MATCH,
            PROJECTILE_MATCH,
            EQUIPMENT_MATCH,
            WEAPON_BANDS,
            CARTRIDGE_BANDS,
            PROJECTILE_BANDS,
            EQUIPMENT_BANDS,
            BALLISTICS / "fnc_selectBand.sqf",
            CLOTHING / "fnc_selectBand.sqf",
        ):
            text = path.read_text(encoding="utf-8").lower()
            for marker in marked:
                self.assertNotIn(marker.lower(), text, f"{path.name} carries {marker}")


if __name__ == "__main__":
    unittest.main()
