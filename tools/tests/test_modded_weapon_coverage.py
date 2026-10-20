#!/usr/bin/env python3
"""Modded weapon and armament coverage, locked count by count.

The installed mods change under the project and the scan that measures them
lies outside the repository, so the measurement itself cannot run in CI. What
CAN be locked is the resolution: data/munition/modded_coverage.json holds
every modded class each table scores and the catalogue row the runtime ladder
reached for it, and this suite runs the same ladder over those identities.

A corpus edit that stops a modded weapon resolving fails here, and so does an
edit that starts resolving a class the corpus cannot justify. The expected
counts are repeated in this file on purpose: changing what the modded set
resolves to means changing the lock deliberately.

Run: python3 -m unittest tools.tests.test_modded_weapon_coverage
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools import report_match_coverage as coverage  # noqa: E402
from tools.validation import identity_designations  # noqa: E402
from tools.validation import register_munition_source  # noqa: E402
from tools.validation.munition_kind import (  # noqa: E402
    is_munition,
    kind_of,
    screened,
)

LOCK = ROOT / "data" / "munition" / "modded_coverage.json"
CATALOGUE = ROOT / "data" / "munition" / "catalogue"
REGISTRY = ROOT / "data" / "munition" / "sources.json"

# The modded coverage this corpus delivers, table by table: resolved, total.
EXPECTED = {
    "small arms": (116, 118),
    "carried launchers": (18, 18),
    "vehicle armament": (335, 374),
}

# Every modded class this work closed, and the row it resolves to. These are
# the reason the corpus holds the entries it now holds.
CLOSED = {
    "FIR_BDU57 BDU-57 LGTR": "lgtr",
    "FIR_GCS1 GCS-1 500lb": "gcs1",
    "FIR_Mk12 Mk 12 Autocannon": "colt_mk12_cannon",
    "FIR_Poniard_Launcher Poniard": "logir_poniard",
    "rhs_weap_2k4 2K4": "drakon_3m7",
    "rhs_weap_2p130 2P130-1": "rocket_9m41",
    "rhs_weap_gi2 GI-2": "denel_gi2",
    "rhs_weap_m70c M70 Commando": "m70_60mm_mortar",
    "rksla3_wpn_dy90 DY-90": "ty90",
    "rksla3_wpn_dy90_sam DY90": "ty90",
    "rksla3_wpn_gau22pod GAU-22/A Pod": "gau12_equalizer",
    "rksla3_wpn_hmp250_pod HMP250 Gun pod": "fn_hmp250",
    "rksla3_wpn_hmp400_pod HMP400 Gun pod": "fn_hmp400",
    "rksla3_wpn_qjk99_127_1_pod QJK99-12.7-1 Gunpod": "qjk99_gun",
    "rksla3_wpn_uk1000gp UK 1000lb GP": "uk_1000lb_gp",
    "rksla3_wpn_uk500gp UK 500lb GP": "uk_500lb_gp",
}

# The entries this work wrote hold no figure: the source states the identity
# and no figure the corpus holds, so the row is a labelled zero throughout.
IDENTITY_ONLY = (
    "drakon_3m7",
    "fn_hmp250",
    "fn_hmp400",
    "gcs1",
    "lgtr",
    "m70_60mm_mortar",
    "qjk99_gun",
    "rocket_9m41",
    "uk_1000lb_gp",
    "uk_500lb_gp",
)

# Every excluded armament class is equipment, and this is the kind it names.
EQUIPMENT_KINDS = {
    "cockpit switch": 7,
    "countermeasure": 10,
    "generic label": 1,
    "leaflet dispenser": 1,
    "recon pod": 4,
    "ship launcher cell": 3,
    "weapon bay": 1,
}


def lock() -> dict:
    return json.loads(LOCK.read_text(encoding="utf-8"))


def matchers() -> dict:
    """The two ladders the measurement uses, over the generated tables."""
    return {
        "small arms": coverage.weapon_matcher(coverage.weapon_table()),
        "carried launchers": coverage.weapon_matcher(coverage.weapon_table()),
        "vehicle armament": coverage.matcher(
            coverage.munition_rows(coverage.MUNITION_TABLE)
        ),
    }


def resolve(match, label: str, classname: str, display: str):
    """The catalogue row a ladder reaches for one game class, or None."""
    hit = match(classname + " " + display)
    if not hit:
        return None
    return hit["id"] if label == "vehicle armament" else hit


def entry(cid: str) -> dict:
    doc = json.loads((CATALOGUE / f"{cid}.json").read_text(encoding="utf-8"))
    return next(e for e in doc["entries"] if e["catalogue_id"] == cid)


class TestLockedResolution(unittest.TestCase):
    """Every modded class resolves exactly as it did when the set was measured."""

    @classmethod
    def setUpClass(cls):
        cls.doc = lock()
        cls.match = matchers()

    def test_the_locked_counts_hold(self):
        for label, (want_hit, want_total) in EXPECTED.items():
            table = self.doc["tables"][label]
            rows = table["rows"]
            hit = sum(
                1
                for classname, display, _ in rows
                if resolve(self.match[label], label, classname, display)
            )
            self.assertEqual(
                (hit, len(rows)),
                (want_hit, want_total),
                f"{label}: resolved/total moved",
            )
            self.assertEqual(
                (table["resolved"], table["total"]),
                (want_hit, want_total),
                f"{label}: the fixture disagrees with the lock",
            )

    def test_every_class_resolves_to_the_row_it_did(self):
        wrong = []
        for label, table in self.doc["tables"].items():
            for classname, display, expected in table["rows"]:
                got = resolve(self.match[label], label, classname, display)
                if got != expected:
                    wrong.append(f"{classname}: {got!r} != {expected!r}")
        self.assertEqual(wrong, [], "\n".join(wrong))

    def test_closed_classes_resolve_and_stay_closed(self):
        for identity, expected in CLOSED.items():
            self.assertEqual(
                resolve(
                    self.match["vehicle armament"],
                    "vehicle armament",
                    *identity.split(" ", 1),
                ),
                expected,
                identity,
            )

    def test_unresolved_classes_are_documented_with_a_reason(self):
        unresolved = {
            classname
            for table in self.doc["tables"].values()
            for classname, _display, row in table["rows"]
            if row is None
        }
        self.assertEqual(unresolved, set(self.doc["unresolved_reasons"]))
        for classname, reason in self.doc["unresolved_reasons"].items():
            self.assertGreater(len(reason), 80, f"{classname}: no real reason")

    def test_every_table_was_measured(self):
        for label, table in self.doc["tables"].items():
            self.assertGreater(table["total"], 0, label)


class TestEquipmentExclusions(unittest.TestCase):
    """A class excluded from the armament set genuinely names equipment."""

    @classmethod
    def setUpClass(cls):
        cls.doc = lock()
        cls.excluded = doc_rows(cls.doc)

    def test_each_exclusion_names_an_equipment_kind(self):
        for kind, members in self.doc["excluded_equipment"].items():
            for classname, display in members:
                self.assertTrue(
                    kind_of(display) or screened(display, classname),
                    f"{classname}: excluded as {kind} but names no kind",
                )

    def test_the_kinds_and_their_counts_are_the_locked_ones(self):
        got = {k: len(v) for k, v in self.doc["excluded_equipment"].items()}
        self.assertEqual(got, EQUIPMENT_KINDS)

    def test_a_gun_pod_is_scored_not_excluded(self):
        # A gun pod holds a real gun, and the catalogue names the gun. The
        # pod is therefore scored against the armament table, and the
        # GAU-22/A pod resolves through the GAU-12/GAU-22 row.
        excluded = {row[0] for members in self.excluded.values() for row in members}
        for classname in (
            "rksla3_wpn_gau22pod",
            "rksla3_wpn_gp19_pod",
            "rksla3_wpn_hmp250_pod",
        ):
            self.assertNotIn(classname, excluded)
        for display in ("GAU-22/A Pod", "HMP250 Gun pod", "GP19 Gunpod"):
            self.assertTrue(is_munition(display), display)

    def test_a_sensor_pod_is_excluded(self):
        for display in ("Litening Pod", "Sniper XR Pod", "TARPS", "Targeting Pod"):
            self.assertEqual(kind_of(display), "recon pod", display)
            self.assertFalse(is_munition(display), display)

    def test_the_vls_cell_is_excluded_while_its_round_is_named(self):
        # The Mk 41 classes are launcher cells (equipment), and the missile
        # each cell holds is a munition the corpus names on its own.
        cells = {row[0] for row in self.excluded["ship launcher cell"]}
        self.assertEqual(
            cells, {"FIR_Mk41_VLS_AG", "FIR_Mk41_VLS_ESSM", "FIR_Mk41_VLS_SM"}
        )
        match = coverage.matcher(coverage.munition_rows(coverage.MUNITION_TABLE))
        self.assertEqual(
            resolve(match, "vehicle armament", "RIM-162", "ESSM"), "rim162_essm"
        )
        self.assertEqual(
            resolve(match, "vehicle armament", "SM-2", "Standard Missile"),
            "standard_missile",
        )


def doc_rows(doc):
    return {
        kind: [tuple(row) for row in members]
        for kind, members in doc["excluded_equipment"].items()
    }


class TestIdentityOnlyEntries(unittest.TestCase):
    """A row the sources give no figure about still NAMES the item."""

    def test_identity_only_rows_hold_no_figure(self):
        for cid in IDENTITY_ONLY:
            item = entry(cid)
            self.assertEqual(item["values"], {}, cid)
            self.assertTrue(item["canonical_name"].strip(), cid)
            self.assertTrue(item["aliases"], cid)

    def test_every_value_cites_a_held_source(self):
        held = {s["source_id"] for s in json.loads(REGISTRY.read_text("utf-8"))}
        for path in sorted(CATALOGUE.glob("*.json")):
            for item in json.loads(path.read_text("utf-8"))["entries"]:
                for field, value in item["values"].items():
                    self.assertIn(
                        value["source"],
                        held,
                        f"{item['catalogue_id']}.{field} cites an unheld source",
                    )


class TestIdentityRules(unittest.TestCase):
    """The rules a modded class needs to resolve, or to be refused."""

    def test_a_nominal_weight_is_not_a_designation(self):
        keys = identity_designations.designations(
            "500 lb General-Purpose Bomb", "500 lb GP"
        )
        self.assertNotIn("500lb", keys)
        self.assertIn("500lbgp", keys)

    def test_a_named_designation_survives(self):
        self.assertIn("mk82", identity_designations.designations("Mk 82"))

    def test_every_held_munition_source_matches_its_digest(self):
        self.assertEqual(register_munition_source.verify(), 0)


if __name__ == "__main__":
    unittest.main()
