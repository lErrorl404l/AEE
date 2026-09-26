#!/usr/bin/env python3
"""Runtime cartridge resolver tests.

The resolver in fnc_getCartridgeData.sqf is generated from the verified
database. These tests mirror its matching rule in Python and check it
against the classnames a mod actually uses, so a regeneration cannot
silently break identity resolution.

Run: python3 tools/tests/test_runtime_cartridges.py
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
SQF = (REPO / "addons/ballistics/functions/fnc_getCartridgeData.sqf").read_text(
    encoding="utf-8"
)


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def table():
    # Row shape: [cartridge_id, aliases, calibre_mm, twist_m, pressure_mpa,
    # proof_mpa, twist_pistol_m, twist_rifle_m].  The resolver grew the two
    # arm-type twist scopes (issue: the pistol and rifle test barrels), so
    # the pattern names every field rather than a fixed six.
    m = re.search(r"private _TABLE = \[(.*?)\n\];", SQF, re.S)
    assert m is not None
    rows = re.findall(
        r'\["([^"]+)", "([^"]*)", '
        r"([0-9.]+), ([0-9.]+), ([0-9.]+), ([0-9.]+), ([0-9.]+), ([0-9.]+)\]",
        m.group(1),
    )
    return [
        (i, a.split("|"), float(c), float(t), float(p), float(pr))
        for i, a, c, t, p, pr, _pistol, _rifle in rows
    ]


def resolve(query):
    """The longest-alias substring rule, exactly as the SQF does."""
    q = normalise(query)
    best, best_len = [], 0
    for cid, aliases, cal, twist, press, proof in table():
        row_len = 0
        for alias in aliases:
            if alias and alias in q and len(alias) > row_len:
                row_len = len(alias)
        if row_len > best_len:
            best, best_len = [cid, cal, twist, press, proof], row_len
    return best


class TestRuntimeResolver(unittest.TestCase):
    def test_mod_classnames_resolve(self):
        # The forms a mod actually uses. 556x45 and 762x51 are the
        # compact forms a classname carries.
        for query, expected in [
            ("B_556x45_Ball", "556x45_nato"),
            ("B_762x51_Ball", "762x51_nato"),
            ("MSS_300NM_225ELDM", "300_norma_mag"),
            ("CUP_10Rnd_9x19", "9x19"),
            ("B_127x108_Ball", "127x108"),
        ]:
            self.assertEqual(resolve(query), resolve(query))  # determinism
            hit = resolve(query)
            self.assertTrue(hit, f"{query} did not resolve")
            self.assertEqual(hit[0], expected, f"{query} resolved to {hit[0]}")

    def test_unknown_classname_resolves_to_nothing(self):
        self.assertEqual(resolve("AEE_Nonexistent_Round_XYZ"), [])

    def test_twist_and_pressure_are_carried(self):
        # 5.56x45 NATO: twist 1:7 from the held M855 specification.
        hit = resolve("B_556x45_Ball")
        self.assertAlmostEqual(hit[2], 0.1778, places=4)
        self.assertAlmostEqual(hit[3], 445.0, places=1)

    def test_table_covers_the_database(self):
        rows = table()
        self.assertGreater(len(rows), 600)
        for row in rows:
            self.assertTrue(row[1], f"{row[0]} has no alias")


class TestGeneratedFile(unittest.TestCase):
    def test_file_is_generated(self):
        self.assertIn("GENERATED runtime projection", SQF)
        self.assertIn("gen_runtime_cartridges.py", SQF)

    def test_registered(self):
        prep = (REPO / "addons/ballistics/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("getCartridgeData", prep)

    def test_rows_match_the_database(self):
        db = json.loads(
            (REPO / "data/ballistics/cartridges.json").read_text(encoding="utf-8")
        )
        with_data = {
            r["cartridge_id"]
            for r in db
            if any(len(normalise(n)) >= 4 for n in r.get("names", []))
        }
        ids = {row[0] for row in table()}
        missing = with_data - ids
        self.assertFalse(
            missing, f"records missing from the runtime table: {sorted(missing)[:5]}"
        )


if __name__ == "__main__":
    unittest.main()
