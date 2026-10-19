#!/usr/bin/env python3
"""Fragmentation warhead resolution against the munition corpus (issue #107).

The fragmentation kernel needs the charge mass, the casing mass, the Gurney
constant, the geometry and the fragment count of the round it models.  This
suite executes the REAL resolver,
addons/blast/functions/fragmentation/fnc_getFragmentationWarhead.sqf, under
the sqf_lite harness and locks three things:

  the row shape and the kernel coupling are unchanged, so the callers of the
  kernel keep the same five-element cast;

  a real munition resolved through the corpus, read from
  data/munition/catalogue, gives the row its published figures derive, with
  the citation the corpus entry carries;

  a field the corpus does not publish is the labelled zero, never an
  estimate, and a missile is not forced onto the Mott fragment model.

The resolver calls aee_blast_fnc_getMunitionMatch, which reads the config
tree the harness does not hold.  The suite supplies that matcher and feeds
it the corpus entry itself, so the derivation is exercised end to end against
real published values.

Run: python3 -m unittest tools.tests.test_munition_fragmentation
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.tests.sqf_lite import run_sqf  # noqa: E402
from tools.validation.munition_kind import (  # noqa: E402
    KINDS,
    SCREEN_TERMS,
    is_munition,
    kind_of,
    screened,
)

FRAG = ROOT / "addons" / "blast" / "functions" / "fragmentation"
MUNITION_MATCH = (
    ROOT / "addons" / "blast" / "functions" / "munition" / "fnc_getMunitionMatch.sqf"
)
CATALOGUE = ROOT / "data" / "munition" / "catalogue"

# The curated rows, which must keep answering for their own munitions.
CURATED = {
    "M67": ["M67", 0.184, 0.216, 2700, "sphere", 1440],
    "M107": ["M107", 6.86, 36.34, 2370, "cylinder", 2000],
    "Mk82": ["Mk82", 87, 140, 2320, "cylinder", 10000],
    "RPG7": ["RPG7", 0.730, 1.87, 2900, "cylinder", 400],
}


def warhead(key: str, match: list | None = None):
    """Run the resolver with the matcher the harness cannot hold."""
    return run_sqf(
        FRAG / "fnc_getFragmentationWarhead.sqf",
        [key],
        {"__FUNC__getMunitionMatch": lambda *_args: match or []},
    )


def gurney(charge: float, casing: float, sqrt2e: float, geometry: str):
    return run_sqf(
        FRAG / "fnc_calculateGurneyVelocity.sqf",
        [charge, casing, sqrt2e, geometry],
    )


def corpus_entry(cid: str) -> dict:
    """The catalogue entry that names a munition, as the corpus holds it."""
    doc = json.loads((CATALOGUE / f"{cid}.json").read_text(encoding="utf-8"))
    return next(e for e in doc["entries"] if e["catalogue_id"] == cid)


def corpus_match(entry: dict) -> list:
    """The match row the runtime matcher returns for a catalogue entry.

    Built from the entry's own published values, in the order the value row
    carries: total, warhead, charge, calibre, length, filling.
    """
    values = entry["values"]

    def num(field: str) -> float:
        return float(values[field]["value"]) if field in values else 0

    filling = values["filling"]["value"] if "filling" in values else ""
    return [
        entry["catalogue_id"],
        entry["munition_type"],
        1,
        "exact_class",
        values["total_mass_kg"]["source"] if "total_mass_kg" in values else "",
        [
            num("total_mass_kg"),
            num("warhead_mass_kg"),
            num("charge_mass_kg"),
            num("calibre_mm"),
            num("length_mm"),
            filling,
        ],
    ]


class TestRowShapeUnchanged(unittest.TestCase):
    """The kernel cast and its callers keep the same shape (issue #107)."""

    def test_curated_rows_and_shape(self):
        for key, expected in CURATED.items():
            row = warhead(key)
            self.assertEqual(len(row), 6, key)
            self.assertEqual(row[0], key)
            self.assertEqual(row, expected)

    def test_row_still_drives_the_kernel(self):
        # The callers pass row[1..4] straight into the Gurney kernel.
        row = warhead("M107")
        self.assertAlmostEqual(gurney(row[1], row[2], row[3], row[4]), 985, delta=2)

    def test_no_match_is_empty(self):
        self.assertEqual(warhead("no_such_munition_42"), [])


class TestCorpusDerivation(unittest.TestCase):
    """Each element comes from a published corpus field (issue #107)."""

    def test_curated_munition_resolves_by_game_class(self):
        # A game class that names the Mk 82 takes the curated row, not a
        # corpus row derived from the entry's partial figures.
        entry = corpus_entry("mk82")
        self.assertEqual(warhead("BO_Mk82", corpus_match(entry)), CURATED["Mk82"])

    def test_corpus_row_with_citation(self):
        # Mark 84: 925 kg total, 429 kg warhead (wikipedia_mark_84_bomb),
        # Tritonal.  Case 925 - 429 = 496 kg.  496 / 0.014 = 35429 fragments.
        entry = corpus_entry("mk84")
        self.assertEqual(
            entry["values"]["total_mass_kg"]["source"], "wikipedia_mark_84_bomb"
        )
        self.assertTrue(entry["values"]["warhead_mass_kg"]["locator"])
        self.assertEqual(
            warhead("BO_Mk84", corpus_match(entry)),
            ["mk84", 429, 496, 2320, "cylinder", 35429],
        )

    def test_unpublished_filling_is_a_labelled_zero(self):
        # Mark 83 names PBXN-109. The Gurney register the kernel publishes
        # holds no figure for it, so the constant is the labelled zero and
        # the rest of the row is still derived.
        entry = corpus_entry("mk83")
        self.assertEqual(entry["values"]["filling"]["value"], "PBXN-109")
        self.assertEqual(
            warhead("BO_Mk83", corpus_match(entry)),
            ["mk83", 202, 245, 0, "cylinder", 17500],
        )

    def test_no_warhead_mass_is_a_labelled_zero_case(self):
        # FAB-250 holds a filling weight and no warhead weight, so the case
        # by difference cannot be taken and the count is the labelled zero.
        entry = corpus_entry("fab250")
        self.assertEqual(
            warhead("FAB250", corpus_match(entry)),
            ["fab250", 100, 0, 0, "cylinder", 0],
        )

    def test_grenade_is_a_sphere(self):
        entry = corpus_entry("ags30")
        self.assertEqual(entry["munition_type"], "grenade")
        self.assertEqual(warhead("AGS30", corpus_match(entry))[4], "sphere")

    def test_missile_is_not_forced_onto_mott(self):
        # The corpus publishes a warhead weight for a missile, not a casing
        # mass, and a blast-fragmentation warhead is not a Mott case.
        entry = corpus_entry("aim9_sidewinder")
        self.assertEqual(entry["munition_type"], "missile")
        self.assertEqual(
            warhead("BO_AIM9", corpus_match(entry)),
            ["aim9_sidewinder", 0, 0, 0, "", 0],
        )


class TestKindFilter(unittest.TestCase):
    """The kind filter separates a munition from a non-munition."""

    # Real scan rows: the classname and the display name the game declares.
    EQUIPMENT = (
        ("fza_gun_inhibit", "Cannon Inhibit", "cockpit switch"),
        ("fza_cannon_limit", "Burst Limit", "cockpit switch"),
        ("rksla3_wpn_masterarm", "MASTER ARM OFF", "cockpit switch"),
        ("SmokeLauncher", "Smoke Screen", "countermeasure"),
        ("FlareLauncher", "Flares", "countermeasure"),
        ("rhs_weap_DIRCM_Lipa", "Lipa DIRCM", "countermeasure"),
        ("FIR_TARPS", "TARPS", "recon pod"),
        ("FIR_PDU5B", "PDU-5/B", "leaflet dispenser"),
        ("FIR_Mk41_VLS_AG", "Mk 41 mod 20 VLS (AG)", "ship launcher cell"),
        (
            "DISCO_Buccaneer_InternalBombLauncher",
            "Internal bay - 1,000 lb HE",
            "weapon bay",
        ),
        ("FIR_RKT_Launcher", "Rocket Launcher", "generic label"),
    )

    def test_each_named_kind_is_excluded(self):
        for classname, display, kind in self.EQUIPMENT:
            self.assertFalse(is_munition(display), display)
            self.assertEqual(kind_of(display), kind, display)

    def test_each_named_kind_is_documented(self):
        documented = {kind for _phrase, kind, _screen in KINDS}
        for _classname, _display, kind in self.EQUIPMENT:
            self.assertIn(kind, documented)

    def test_real_munitions_are_not_excluded(self):
        for display in (
            "Mk 82",
            "AGM-114K Hellfire",
            "GBU-12 Paveway II",
            "CBU-87",
            "HMP250 Gun pod",
            "S-8",
        ):
            self.assertTrue(is_munition(display), display)

    def test_no_catalogue_entry_is_screened(self):
        # The runtime screen is a substring test on the folded identity. A
        # term that appeared in a catalogue entry could reject a munition
        # the corpus already names, so no entry may carry one.
        def fold(text: str) -> str:
            return "".join(c for c in text.lower() if c.isalnum())

        for path in sorted(CATALOGUE.glob("*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            for entry in doc.get("entries", []):
                identity = fold(
                    " ".join(
                        [entry.get("catalogue_id", ""), entry.get("canonical_name", "")]
                        + list(entry.get("aliases") or [])
                    )
                )
                for term in SCREEN_TERMS:
                    self.assertNotIn(term, identity, f"{entry['catalogue_id']}: {term}")

    def test_the_runtime_screen_reads_a_joined_classname(self):
        # The runtime folds the identity and tests a substring, so a class
        # that joins its words with an underscore is screened even though a
        # word-boundary pattern misses it. The coverage measurement uses the
        # same test, so the number it prints is the number the runtime gives.
        self.assertEqual(
            screened("FIR_Mk41_VLS_SM", "Standard Missile"), "ship launcher cell"
        )
        self.assertEqual(screened("Mk 82"), "")

    def test_generated_matcher_carries_the_screen(self):
        source = MUNITION_MATCH.read_text(encoding="utf-8")
        for term in SCREEN_TERMS:
            self.assertIn(f'"{term}"', source, term)


if __name__ == "__main__":
    unittest.main()
