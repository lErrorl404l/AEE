#!/usr/bin/env python3
"""Runtime projectile resolver tests.

The resolver reports every coefficient the database holds for a bullet,
each against its own standard, with its grade. It must never report a
derived value, and it must never substitute one standard for another.

Run: python3 tools/tests/test_runtime_projectiles.py
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
SQF = (REPO / "addons/ballistics/functions/fnc_getProjectileData.sqf").read_text(
    encoding="utf-8"
)


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def table():
    m = re.search(r"private _TABLE = \[(.*?)\n\];", SQF, re.S)
    rows = re.findall(
        r'\["([^"]+)", "([^"]*)", ([0-9.]+), ([0-9.]+), "([^"]*)", ([0-9.]+)\]',
        m.group(1),
    )
    out = []
    for pid, aliases, mass, dia, coeffs, length in rows:
        parsed = {}
        for triple in coeffs.split("|"):
            if not triple:
                continue
            model, value, grade = triple.split(":")
            parsed[model] = (float(value), grade)
        out.append(
            (pid, aliases.split("|"), float(mass), float(dia), parsed, float(length))
        )
    return out


def defaults():
    m = re.search(r"private _DEFAULTS = \[(.*?)\n\];", SQF, re.S)
    return dict(re.findall(r'\["([^"]+)", "([^"]+)"\]', m.group(1)))


CARTRIDGE = {
    "B_556x45_Ball": "556x45_nato",
    "B_762x51_Ball": "762x51_nato",
    "B_127x99_Ball": "50_bmg",
    "CUP_30Rnd_762x39": "762x39",
}


def resolve(ammo):
    toks = [t for t in re.split(r"[-_. ]+", ammo.lower()) if t]
    rows = table()
    for row in rows:
        for alias in row[1]:
            if alias and alias in toks:
                return row
    by_id = {row[0]: row for row in rows}
    cid = CARTRIDGE.get(ammo)
    if cid and cid in defaults():
        return by_id.get(defaults()[cid])
    return None


class TestProjectileResolver(unittest.TestCase):
    def test_mod_bullet_carries_both_standards(self):
        # The Hornady 225 gr ELD Match is published against both G1 and
        # G7, so both are reported and the caller chooses.
        hit = resolve("MSS_300NM_225ELDM")
        self.assertIsNotNone(hit, "the mod classname did not resolve")
        self.assertTrue(hit[0].startswith("hornady_eldm_30_225"))
        self.assertAlmostEqual(hit[4]["G1"][0], 0.777, places=3)
        self.assertAlmostEqual(hit[4]["G7"][0], 0.391, places=3)

    def test_military_round_reports_the_measured_standard(self):
        # 5.56x45 NATO fires M855. Aberdeen Proving Ground measured its
        # G7 coefficient, so G7 is held and G1 is not claimed falsely.
        hit = resolve("B_556x45_Ball")
        self.assertEqual(hit[0], "apg_m855")
        self.assertAlmostEqual(hit[4]["G7"][0], 0.151, places=3)
        self.assertEqual(hit[4]["G7"][1], "measured")

    def test_no_derived_value_is_reported(self):
        for row in table():
            for model, (_, grade) in row[4].items():
                self.assertNotEqual(
                    grade, "derived", f"{row[0]} reports a derived {model}"
                )

    def test_every_model_held_is_reported(self):
        # The count of coefficient entries must equal the count in the
        # database, so nothing is silently dropped by the projection.
        db = json.loads(
            (REPO / "data/ballistics/projectiles.json").read_text(encoding="utf-8")
        )
        expected = 0
        for rec in db:
            expected += sum(
                1
                for f, e in rec["values"].items()
                if f.startswith("bc_") and e.get("grade") != "derived"
            )
        actual = sum(len(row[4]) for row in table())
        self.assertEqual(
            actual, expected, "the projection dropped or added a coefficient"
        )


class TestGeneratedFile(unittest.TestCase):
    def test_coefficient_values_are_numbers(self):
        # The coefficients travel as a "MODEL:value:grade" string, so
        # the value must be parsed back to a number. A string here made
        # a caller compare a string with a number at run time, which
        # HEMTT cannot see and only the server test caught.
        self.assertIn("parseNumber", SQF)

    def test_file_is_generated(self):
        self.assertIn("GENERATED runtime projection", SQF)
        self.assertIn("gen_runtime_projectiles.py", SQF)

    def test_registered(self):
        prep = (REPO / "addons/ballistics/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("getProjectileData", prep)

    def test_covers_the_database(self):
        db = json.loads(
            (REPO / "data/ballistics/projectiles.json").read_text(encoding="utf-8")
        )
        with_alias = {
            r["projectile_id"]
            for r in db
            if any(len(normalise(n)) >= 3 for n in r.get("names", []))
        }
        ids = {row[0] for row in table()}
        missing = with_alias - ids
        self.assertFalse(missing, f"missing from the table: {sorted(missing)[:5]}")


if __name__ == "__main__":
    unittest.main()
