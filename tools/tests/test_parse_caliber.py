#!/usr/bin/env python3
"""Caliber parser tests (issue #167).

Verifies fnc_parseCaliber.sqf resolves the tank-cannon calibres added in
phase 2: 105 mm, 120 mm and 125 mm. The parser has two layers, the alias
match and the numeric conversion. The tests mirror both and check the
vehicle-weapon tokens a classname carries.

Run: python3 tools/tests/test_parse_caliber.py
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
SQF = (REPO / "addons/ballistics/functions/fnc_parseCaliber.sqf").read_text(
    encoding="utf-8"
)


def calibers():
    """Parse the _CALIBERS alias table from the SQF."""
    match = re.search(r"private _CALIBERS = \[(.*?)\n\];", SQF, re.S)
    assert match is not None
    block = match.group(1)
    rows = []
    for mm, canon, alias_text in re.findall(
        r'\[([0-9.]+),\s*"([^"]*)",\s*\[([^\]]*)\]\]', block
    ):
        rows.append((float(mm), canon, re.findall(r'"([^"]*)"', alias_text)))
    return rows


def resolve(name):
    """Mirror of fnc_parseCaliber: the alias layer, then the numeric layer."""
    n = name.lower()
    best_alias = []
    best_alias_len = 0
    for mm, canon, aliases in calibers():
        for alias in aliases:
            if alias in n and len(alias) > best_alias_len:
                best_alias, best_alias_len = [mm, canon, 1], len(alias)
    if best_alias:
        return best_alias
    matches = re.split(r"[0-9]", n)
    num = ""
    if len(matches) > 1:
        start = len(matches[0])
        length = len(n) - start - len(matches[1])
        if length > 0:
            num = n[start : start + length]
    if num == "":
        return [0, "", 0]
    val = float(num)
    if "." in num:
        mm = val
    elif 200 <= val < 600:
        if val in (300, 338, 357, 380, 400, 440, 450, 500):
            mm = val * 0.0254 * 10
        else:
            mm = val / 100
    else:
        mm = val
    best, best_diff = [0, "", 2], 999.0
    for row_mm, canon, _ in calibers():
        diff = abs(row_mm - mm)
        if diff < best_diff and diff < 0.5:
            best, best_diff = [row_mm, canon, 2], diff
    return best


class TestCannonCalibers(unittest.TestCase):
    def test_alias_tokens_resolve(self):
        for token, expected in [
            ("B_105mm_AP", 105.0),
            ("M68_cannon", 105.0),
            ("105x617", 105.0),
            ("M256_cannon", 120.0),
            ("120x570", 120.0),
            ("B_120mm_APFSDS", 120.0),
            ("2A46_125", 125.0),
            ("125x408", 125.0),
            ("B_125mm_APFSDS", 125.0),
        ]:
            self.assertEqual(resolve(token)[0], expected, token)

    def test_numeric_layer_resolves(self):
        for token, expected in [
            ("T105", 105.0),
            ("T120", 120.0),
            ("T125", 125.0),
        ]:
            self.assertEqual(resolve(token)[0], expected, token)

    def test_small_arms_still_resolve(self):
        self.assertEqual(resolve("B_556x45_Ball")[0], 5.56)
        self.assertEqual(resolve("B_762x51_Ball")[0], 7.62)

    def test_table_holds_the_cannon_rows(self):
        rows = {mm for mm, _, _ in calibers()}
        for mm in (105.0, 120.0, 125.0):
            self.assertIn(mm, rows)


if __name__ == "__main__":
    unittest.main()
