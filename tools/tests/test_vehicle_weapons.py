#!/usr/bin/env python3
"""Vehicle-weapon integration tests (phase 4).

Locks the phase-4 ballistics integration:

- the load projection resolves a cannon, autocannon or heavy machine gun
  round to the sourced service velocity where the interior model is
  deferred;
- the shot path consults the load for a cannon calibre;
- the cannon recoil term uses the Lagrange approximation and the
  small-arms factors are unchanged;
- the cannon penetration branch is deferred with a precise statement.

Run: python3 tools/tests/test_vehicle_weapons.py
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
BALL = REPO / "addons/ballistics/functions"
ARM = REPO / "addons/armour/functions"
LOAD_SQF = (BALL / "fnc_getLoadData.sqf").read_text(encoding="utf-8")
SHOT = (BALL / "fnc_resolveShot.sqf").read_text(encoding="utf-8")
RECOIL = (BALL / "fnc_calculateRecoil.sqf").read_text(encoding="utf-8")
GATE = (ARM / "fnc_penetrationGate.sqf").read_text(encoding="utf-8")
DERIVE = (BALL / "fnc_deriveCartridge.sqf").read_text(encoding="utf-8")


def load_rows():
    m = re.search(r"private _TABLE = \[(.*?)\n\];", LOAD_SQF, re.S)
    if m is None:
        return []
    return re.findall(
        r'\["([^"]*)", "([^"]*)", "([^"]*)", '
        r'([0-9.]+), ([0-9.]+), ([0-9.]+), "([^"]*)"\]',
        m.group(1),
    )


class TestLoadProjection(unittest.TestCase):
    def test_rows_carry_a_source_grade(self):
        rows = load_rows()
        self.assertGreater(len(rows), 5)
        for row in rows:
            self.assertTrue(row[0], f"{row[1]} has no alias")
            self.assertTrue(row[2], f"{row[1]} has no cartridge")
            self.assertGreater(float(row[3]), 0, f"{row[1]} has no velocity")
            self.assertTrue(row[6], f"{row[1]} has no grade")

    def test_cannon_and_autocannon_loads_present(self):
        ids = {r[1] for r in load_rows()}
        for load_id in (
            "20x102_m55a2_load",
            "25x137_m919_load",
            "30x113_m789_load",
            "30x173_mk239_load",
            "40x53_m430_load",
            "105mm_m456_load",
            "120mm_m830_load",
            "125mm_m88_load",
        ):
            self.assertIn(load_id, ids)

    def test_values_match_the_database(self):
        loads = {
            r["load_id"]: r
            for r in json.loads(
                (REPO / "data/ballistics/loads.json").read_text(encoding="utf-8")
            )
        }
        for row in load_rows():
            rec = loads[row[1]]
            mv = rec["values"]["service_velocity_ms"]["value"]
            self.assertAlmostEqual(float(row[3]), mv, places=2, msg=row[1])

    def test_bare_calibre_is_not_an_alias(self):
        # 30mm names two cartridges (30x113 and 30x173), so it must not
        # select a load on its own.
        for row in load_rows():
            for alias in row[0].split("|"):
                self.assertFalse(
                    re.fullmatch(r"[0-9]+mm", alias),
                    f"{row[1]} carries the bare bore {alias}",
                )

    def test_ambiguous_round_token_has_more_than_one_owner(self):
        # "apfsds" names the 25 mm M919, the 120 mm M829 and the 125 mm
        # M88. The runtime resolves the tie with the calibre token.
        owners = [r[1] for r in load_rows() if "apfsds" in r[0].split("|")]
        self.assertGreater(len(owners), 1)


class TestWiring(unittest.TestCase):
    def test_load_resolver_registered(self):
        prep = (REPO / "addons/ballistics/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("getLoadData", prep)

    def test_shot_consults_the_load(self):
        self.assertIn("getLoadData", SHOT)
        self.assertIn("_cartridgeCalibre >= 20", SHOT)

    def test_bare_apfsds_does_not_take_120mm(self):
        # The 120 mm APFSDS row must require the calibre, so a 25 mm or
        # 30 mm long rod does not take the 120 mm M829 velocity.
        self.assertIn('_a find "120mm" >= 0 && _a find "apfsds" >= 0', DERIVE)


class TestCannonRecoil(unittest.TestCase):
    def test_cannon_uses_the_lagrange_term(self):
        self.assertIn('_arm == "cannon"', RECOIL)
        self.assertIn("0.5 * _chargeKg", RECOIL)

    def test_small_arms_factors_unchanged(self):
        for factor in ("1.25", "1.50", "1.75"):
            self.assertIn(factor, RECOIL)

    def test_the_source_is_named(self):
        header = RECOIL.split("*/")[0]
        self.assertIn("cannon", header)
        self.assertIn("AMCP 706-150", header)


class TestCannonPenetrationDeferral(unittest.TestCase):
    def test_the_missing_inputs_are_named(self):
        for token in ("rod length", "obliquity", "shaped-charge jet"):
            self.assertIn(token, GATE)

    def test_the_small_arms_rule_is_unchanged(self):
        self.assertIn("(v/1000) * caliber * 15", GATE)

    def test_no_cannon_model_is_applied(self):
        # The deferral may name a candidate model, but none is applied:
        # the only penetration computation is still the bisurf rule.
        self.assertEqual(GATE.count("_penMM ="), 1)


if __name__ == "__main__":
    unittest.main()
