#!/usr/bin/env python3
"""Runtime weapon resolver tests.

The weapon layer holds one datum: the rifling twist. Two weapons in the
same chambering can differ (M24 1:11.2, M40A5 1:12), so the resolver
returns the weapon's own twist and the shot resolution prefers it over
the cartridge standard.

Run: python3 tools/tests/test_runtime_weapons.py
"""

import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation.validate_ballistics_data import RANGES  # noqa: E402

SQF = (REPO / "addons/ballistics/functions/fnc_getWeaponData.sqf").read_text(
    encoding="utf-8"
)


def table():
    m = re.search(r"private _TABLE = \[(.*?)\n\];", SQF, re.S)
    return re.findall(
        r'\["([^"]+)", "([^"]*)", ([0-9.]+), ([0-9.]+), "([^"]*)", ([0-9.]+)\]',
        m.group(1),
    )


class TestWeaponResolver(unittest.TestCase):
    def test_same_chambering_different_barrels(self):
        # The M24 and the M40A5 are both 7.62x51 NATO, and their barrels
        # differ. The catalogue must keep them apart.
        rows = {r[0]: r for r in table()}
        self.assertIn("m24", rows)
        self.assertIn("m40a5", rows)
        self.assertNotEqual(rows["m24"][2], rows["m40a5"][2])
        self.assertAlmostEqual(float(rows["m24"][2]), 0.28448, places=5)
        self.assertAlmostEqual(float(rows["m40a5"][2]), 0.3048, places=5)

    def test_every_row_has_an_alias(self):
        for row in table():
            self.assertTrue(row[1], f"{row[0]} has no alias")

    def test_no_mod_prefix_enters_the_catalogue(self):
        for prefix in ("MSS_", "MCC_", "RHS_", "CUP_"):
            self.assertNotIn(prefix, SQF, f"{prefix} is a mod patch")


class TestWiring(unittest.TestCase):
    def test_shot_prefers_the_weapon_twist(self):
        shot = (REPO / "addons/ballistics/functions/fnc_resolveShot.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("getWeaponData", shot)
        self.assertIn("_twist = _weaponData select 1", shot)

    def test_spin_rate_is_returned(self):
        shot = (REPO / "addons/ballistics/functions/fnc_resolveShot.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("2 * pi * _mv / _twist", shot)

    def test_registered(self):
        prep = (REPO / "addons/ballistics/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("getWeaponData", prep)

    def test_a_compilation_never_becomes_a_value(self):
        # The corpus is tier 5. It may generate a lead, never an entry.
        db = json.loads(
            (REPO / "data/ballistics/weapons.json").read_text(encoding="utf-8")
        )
        sources = json.loads(
            (REPO / "data/ballistics/sources.json").read_text(encoding="utf-8")
        )
        for rec in db:
            for field, entry in rec["values"].items():
                self.assertFalse(
                    str(entry.get("source", "")).startswith("corpus_"),
                    f"{rec['weapon_id']}.{field} uses a compilation",
                )
        for source in sources:
            self.assertFalse(
                source["source_id"].startswith("corpus_"),
                "a compilation source is registered",
            )

    def test_identity_carries_no_manufacturer(self):
        # The maker is a field, never part of the key. A maker+model alias
        # is a deliberate matching aid, because a mod classname often
        # carries the maker, so it is allowed and it must be exactly the
        # maker joined to the key.
        db = json.loads(
            (REPO / "data/ballistics/weapons.json").read_text(encoding="utf-8")
        )
        for rec in db:
            maker = re.sub(r"[^a-z0-9]", "", rec.get("manufacturer", "").lower())
            # The key may lead with the maker when the model name does,
            # because "Glock 17" and "Sako 75" are the product names. The
            # mechanical maker prefix of the old corpus is removed by
            # gen_designations, which keeps the old form as an alias. The
            # rule this test can hold is the alias rule below: the maker
            # alone must never identify a weapon.
            key = re.sub(r"[^a-z0-9]", "", rec["weapon_id"].lower())
            for alias in rec.get("aliases", []):
                if maker and alias.startswith(maker):
                    # A maker-prefixed alias must still carry the model
                    # key, so the maker alone never identifies a weapon.
                    self.assertIn(
                        key,
                        re.sub(r"[^a-z0-9]", "", alias.lower()),
                        f"{rec['weapon_id']} alias {alias} lacks the key",
                    )

    def test_catalogue_is_sourced(self):
        db = json.loads(
            (REPO / "data/ballistics/weapons.json").read_text(encoding="utf-8")
        )
        self.assertGreater(len(db), 20)
        for rec in db:
            for field, entry in rec["values"].items():
                self.assertTrue(
                    entry.get("source"), f"{rec['weapon_id']}.{field} has no source"
                )
                self.assertNotEqual(
                    entry.get("grade"),
                    "derived",
                    f"{rec['weapon_id']}.{field} is derived",
                )


class TestPerArmTypeTwist(unittest.TestCase):
    def test_a_cartridge_can_carry_both_scopes(self):
        db = json.loads(
            (REPO / "data/ballistics/cartridges.json").read_text(encoding="utf-8")
        )
        by_id = {r["cartridge_id"]: r for r in db}
        mag = by_id["44_remington_magnum"]["values"]
        self.assertIn("standard_twist_pistol_m", mag)
        self.assertIn("standard_twist_rifle_m", mag)
        self.assertNotEqual(
            mag["standard_twist_pistol_m"]["value"],
            mag["standard_twist_rifle_m"]["value"],
        )
        # The generic value follows the arm type the cartridge belongs to.
        self.assertEqual(
            mag["standard_twist_m"]["value"], mag["standard_twist_pistol_m"]["value"]
        )

    def test_no_scope_pair_is_recorded_as_a_conflict(self):
        conflicts = json.loads(
            (REPO / "data/ballistics/conflicts.json").read_text(encoding="utf-8")
        )
        scopes = {"saami_z299_3", "saami_z299_4"}
        for c in conflicts:
            self.assertFalse(
                {c.get("source_a"), c.get("source_b")} <= scopes,
                f"{c.get('entity')} records two scopes as a conflict",
            )

    def test_the_resolver_selects_by_weapon_type(self):
        shot = (REPO / "addons/ballistics/functions/fnc_resolveShot.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("_twistPistol", shot)
        self.assertIn("_twistRifle", shot)
        self.assertIn("== 2", shot)


class TestWeaponMassBand(unittest.TestCase):
    """The weapon mass unit contract (issue #234).

    Eight pistol rows held grams under the kg unit (294 to 992). The band
    lives in the data validator, so this corpus check and the gate read the
    same numbers and cannot drift apart.
    """

    def test_the_band_rejects_the_gram_error(self):
        low, high = RANGES["mass_kg"]
        for grams in (294.0, 317.0, 674.0, 737.0, 799.0, 850.0, 881.0, 992.0):
            self.assertFalse(low <= grams <= high, f"{grams} passed the band")

    def test_every_weapon_mass_is_inside_the_band(self):
        low, high = RANGES["mass_kg"]
        db = json.loads(
            (REPO / "data/ballistics/weapons.json").read_text(encoding="utf-8")
        )
        for rec in db:
            entry = rec["values"].get("mass_kg")
            if entry is None:
                continue
            self.assertEqual(entry["unit"], "kg", rec["weapon_id"])
            self.assertTrue(
                low <= entry["value"] <= high,
                f"{rec['weapon_id']}: {entry['value']} kg",
            )


class TestWeaponMassBand(unittest.TestCase):
    """Issue #234: the pistol masses must be kilograms, not grams.

    Eight Ruger rows once recorded grams under unit "kg" (a Ruger LCP read
    294 "kg").  A mass consumer is wrong by 1000x for those rows, so the
    band test below holds every row to a plausible small-arms mass and pins
    the eight corrected rows to their crisply published weights.
    """

    PISTOLS = {
        "lcp": 0.294,
        "lcpii": 0.317,
        "markiv": 0.799,
        "security9": 0.674,
        "singlesix": 0.992,
        "sp101": 0.737,
        "sr1911": 0.881,
        "wrangler": 0.850,
    }

    def setUp(self):
        self.db = json.loads(
            (REPO / "data/ballistics/weapons.json").read_text(encoding="utf-8")
        )

    def test_every_mass_is_in_kilograms(self):
        for rec in self.db:
            entry = rec["values"].get("mass_kg")
            if entry is None:
                continue
            with self.subTest(weapon=rec["weapon_id"]):
                self.assertEqual(entry["unit"], "kg")
                # A small arm is 0.2 kg to 20 kg. Anything above the band is
                # the grams-under-kg defect or a heavier weapon class.
                self.assertGreaterEqual(entry["value"], 0.2)
                self.assertLessEqual(entry["value"], 20.0)

    def test_the_eight_pistols_hold_their_kg_value(self):
        rows = {rec["weapon_id"]: rec for rec in self.db}
        for weapon, kg in self.PISTOLS.items():
            with self.subTest(weapon=weapon):
                self.assertIn(weapon, rows)
                entry = rows[weapon]["values"]["mass_kg"]
                self.assertAlmostEqual(entry["value"], kg, places=3)
                self.assertEqual(entry["grade"], "documented")

    def test_the_corpus_median_is_a_real_small_arm(self):
        # The defect was detectable by the corpus statistics, so pin them.
        values = sorted(
            rec["values"]["mass_kg"]["value"]
            for rec in self.db
            if "mass_kg" in rec["values"]
        )
        self.assertGreater(len(values), 100)
        median = values[len(values) // 2]
        self.assertGreater(median, 1.0)
        self.assertLess(median, 6.0)


class TestConflictLedger(unittest.TestCase):
    """Issue #248: one record per distinct conflict.

    The ledger is written by appending, so a second run of the generator
    duplicated every record it wrote: 471 records for 140 distinct conflicts.
    The ledger is what a reviewer reads to see the disagreements, so a
    duplicate inflates every count taken from it.
    """

    def setUp(self):
        self.records = json.loads(
            (REPO / "data/ballistics/conflicts.json").read_text(encoding="utf-8")
        )

    def test_no_duplicate_conflict_group(self):
        seen: dict = {}
        for rec in self.records:
            key = (
                rec.get("entity"),
                rec.get("field"),
                rec.get("value_a"),
                rec.get("value_b"),
            )
            with self.subTest(key=key):
                self.assertNotIn(key, seen, f"duplicate conflict record for {key}")
            seen[key] = rec

    def test_every_record_names_two_values_and_two_sources(self):
        for rec in self.records:
            with self.subTest(entity=rec.get("entity")):
                self.assertNotEqual(rec.get("value_a"), rec.get("value_b"))
                self.assertTrue(rec.get("source_a"))
                self.assertTrue(rec.get("source_b"))


if __name__ == "__main__":
    unittest.main()
