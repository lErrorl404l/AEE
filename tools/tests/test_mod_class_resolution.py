#!/usr/bin/env python3
"""Modded-class resolution locks (vehicle and aircraft identity ladders).

The runtime matchers name a game class from the class text and the display
name alone. A modded class resolves when its own text carries a designation
the catalogue entry publishes: the exact mapped class, a curated alias, a
keyword or the closest layer. It resolves to nothing when the text carries
no such designation, and that is the correct answer - the matcher never
guesses.

This module locks the modded gaps that were closed and the modded classes
that stay open on purpose. Each closed class names the catalogue entry it
must resolve to. Each open class is listed with the reason it stays open, so
a later change that closes or breaks one shows up here.

The two tables are independent. The vehicle table closed twenty-one modded
classes: the RHS M1237 RG-33L "Plus" and M1239 SOCOM AUV families, the
PHAN Typhoon truck, the four Tahoe marks, the RHS Object 681, the Jbad
Caterpillar 789D, and the five the counterpart research closed (the SUV, the
Hatchback, the two Van re-uses and the RHS civilian Zamak retexture). The
aircraft table closed one: the base game's fictional AR-2 Darter, whose
display name the wiki ties to the Parrot AR.Drone 2.0. Every remaining
aircraft gap is an ArmaFPV first-person-view drone whose own text ("Crocus
AT TI") states no designation any published source holds, so a row would
have to invent one.

The remaining nineteen vehicle gaps are locked below with the reason each
stays open, and data/vehicle/MODDED_CLASS_GAPS.md holds the same table with
its evidence. The KamAZ-4310 entry publishes the real truck and binds the
Arma 3 Zamak classes through the wiki's own statement ("Zamak is simply
Kamaz spelt backwards, which is the name of the company that designs the
real-life "KamAZ-4310" family of trucks that the Zamak is based on"). The
Project OPFOR KAMAZ trucks are retextures of that Zamak, but no source
states the chain and their own text carries no 4310 token, so they stay
open. An alias on the maker word would close them and capture the RHS
KamAZ-5350 at the same time. That is a false answer, not a closure.

Run: python3 -m unittest tools.tests.test_mod_class_resolution -v
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

VEHICLE_MATCH = REPO / "addons" / "vehicles" / "functions" / "fnc_getVehicleMatch.sqf"
AIRCRAFT_MATCH = REPO / "addons" / "flight" / "functions" / "fnc_getAircraftMatch.sqf"

# The shortest alias or keyword the closest layer accepts, as the runtime does.
SCAN_MIN = 3

# Modded classes that must resolve, with the catalogue entry that names them.
# The class and the display name are the ones the installed content declares.
CLOSED_VEHICLE_CASES: tuple[tuple[str, str, str], ...] = (
    ("rhsusf_M1237_M2_usarmy_d", "M1237 (O-GPK/M2)", "bae_systems_rg_33l_6x6"),
    ("rhsusf_M1237_M2_usarmy_wd", "M1237 (O-GPK/M2)", "bae_systems_rg_33l_6x6"),
    ("rhsusf_M1237_MK19_usarmy_d", "M1237 (O-GPK/Mk19)", "bae_systems_rg_33l_6x6"),
    ("rhsusf_M1237_MK19_usarmy_wd", "M1237 (O-GPK/Mk19)", "bae_systems_rg_33l_6x6"),
    (
        "rhsusf_M1239_socom_d",
        "M1239 AUV",
        "bae_systems_rg_33l_socom_armored_utility_vehicle_auv",
    ),
    (
        "rhsusf_M1239_M2_socom_d",
        "M1239 AUV (CROWS/M2)",
        "bae_systems_rg_33l_socom_armored_utility_vehicle_auv",
    ),
    (
        "rhsusf_M1239_MK19_socom_d",
        "M1239 AUV (CROWS/Mk19)",
        "bae_systems_rg_33l_socom_armored_utility_vehicle_auv",
    ),
    (
        "rhsusf_M1239_M2_Deploy_socom_d",
        "M1239 AUV Deploy (CROWS/M2)",
        "bae_systems_rg_33l_socom_armored_utility_vehicle_auv",
    ),
    (
        "rhsusf_M1239_MK19_Deploy_socom_d",
        "M1239 AUV Deploy (CROWS/Mk19)",
        "bae_systems_rg_33l_socom_armored_utility_vehicle_auv",
    ),
    ("CBRN_Typhoon_Truck", "Typhoon Truck", "kamaz_63968_typhoon_k"),
    ("tahoe_08", "Chevrolet Tahoe", "chevrolet_tahoe_gmt900"),
    ("tahoe_ltz_08", "Chevrolet Tahoe VIP", "chevrolet_tahoe_gmt900"),
    ("tahoe_UNM", "Chevrolet Tahoe Security", "chevrolet_tahoe_gmt900"),
    ("tahoe_LUMI", "Chevrolet Tahoe'08 Lumi Edition", "chevrolet_tahoe_gmt900"),
    ("rhs_Ob_681_2", "Obyekt-681-2", "object_681"),
    ("Jbad_cat_dumper", "Cat 789D", "caterpillar_789d"),
    # Closed by the 2026-10-20 counterpart research: each display name now
    # carries a maker or a model the wiki names, so the ladder resolves it.
    ("LOP_SUV_base", "SUV", "bmw_x6_concept"),
    ("LOP_Hatchback_base", "Hatchback", "hyundai_iblue_concept"),
    ("CBRN_Containment_Vehicle", "Van (Utility)", "mercedes_benz_sprinter"),
    ("Gendarmerie_CBRN_Vehicle", "Van (Utility)", "mercedes_benz_sprinter"),
    ("RHS_Civ_Truck_02_transport_F", "Zamak Transport", "kamaz_4310"),
)

# Modded classes that stay open on the vehicle side, with the reason.
# A class whose chain passes StaticWeapon is an emplacement, not a vehicle:
# the same kind rule gen_vehicle_bindings.py applies ("a ground class is a
# LandVehicle that is not a StaticWeapon"). A catalogue of real vehicles is
# never scored against a tripod mount, a MANPADS post or a towed howitzer.
VEHICLE_EMPLACEMENT_CASES: tuple[str, ...] = (
    "rhs_m2staticmg_base",
    "RHS_M2StaticMG_MiniTripod_base",
    "RHS_MK19_TriPod_base",
    "RHS_Stinger_AA_pod_Base",
    "RHS_M119_base",
)

# A mod that re-uses a base-game FICTIONAL vehicle carries the base game's
# own unresolved identity: the display name is the fictional one ("Offroad",
# "SUV", "Hatchback", "Zamak Transport", "Van (Utility)") and the class text
# states no real designation. The Arma 3 Offroad is the one that stays open
# after the counterpart research: its real identity is a composite (Audi Q7
# pickup-concept front, Mitsubishi L200 rear), so a class text that names
# only the fictional name names neither donor. The SUV, Hatchback, Van and
# RHS Zamak re-uses now resolve and are locked as closed cases below.
VEHICLE_FICTIONAL_REUSE_CASES: tuple[tuple[str, str, str], ...] = (
    (
        "LOP_Offroad_base",
        "Offroad",
        "fictional Offroad display; the real identity is a two-donor composite and the text names neither donor",
    ),
    (
        "LOP_Offroad_M2_base",
        "Offroad (M2)",
        "fictional Offroad display; the same composite identity, plus an Arma-only M2 mount",
    ),
    (
        "CBRN_Offroad",
        "Offroad",
        "fictional Offroad display; the same composite identity as the base game",
    ),
    (
        "LOP_AA_Offroad",
        "ANA Offroad",
        "fictional Offroad display behind a faction prefix; the text names no donor",
    ),
    (
        "LOP_AA_Offroad_Police",
        "ANP Offroad",
        "fictional Offroad display behind a faction prefix; the text names no donor",
    ),
    (
        "LOP_AA_Offroad_M2",
        "ANA Offroad (M2)",
        "fictional Offroad display behind a faction prefix; the text names no donor",
    ),
    (
        "LOP_AA_Offroad_M2_Police",
        "ANP Offroad (M2)",
        "fictional Offroad display behind a faction prefix; the text names no donor",
    ),
)

# A modded class whose text names only the maker, or only a family. The
# KamAZ trucks of Project OPFOR are retextures of the Arma 3 Truck_02 Zamak
# and state "KAMAZ" plus a body word. No class name and no display name in
# the installed content carries a model token: the scan holds no "4310"
# anywhere, so the maker plus a body cannot name the KamAZ-4310 without
# capturing the RHS KamAZ-5350 classes at the same time. The family base
# classes (FMTV, the LOP "_base" scaffolding) state a family, and a family is
# not one vehicle, so the catalogue correctly refuses to name one. The Zamak
# classes these trucks retexture are bound to the KamAZ-4310, but no read
# source states the retexture chain, so the retextures stay open.
VEHICLE_MAKER_OR_FAMILY_CASES: tuple[tuple[str, str, str], ...] = (
    (
        "LOP_KAMAZ_fuel_base",
        "KamAZ (fuel)",
        "maker plus fuel body; the model is not published for this retexture",
    ),
    (
        "LOP_UKR_KAMAZ_Fuel",
        "KAMAZ (fuel)",
        "maker plus fuel body; the model is not published for this retexture",
    ),
    (
        "LOP_CDF_KAMAZ_Fuel",
        "KAMAZ (fuel)",
        "maker plus fuel body; the model is not published for this retexture",
    ),
    (
        "LOP_IRAN_KAMAZ_Fuel",
        "KAMAZ (fuel)",
        "maker plus fuel body; the model is not published for this retexture",
    ),
    (
        "LOP_SYR_KAMAZ_Fuel",
        "KAMAZ (fuel)",
        "maker plus fuel body; the model is not published for this retexture",
    ),
    (
        "LOP_KAMAZ_cov_base",
        "KAMAZ (covered)",
        "maker plus covered body; the model is not published for this retexture",
    ),
    (
        "LOP_KAMAZ_trans_base",
        "KAMAZ (open)",
        "maker plus open body; the model is not published for this retexture",
    ),
    (
        "LOP_KAMAZ_rep_base",
        "KAMAZ (repair)",
        "maker plus repair body; the model is not published for this retexture",
    ),
    (
        "LOP_KAMAZ_med_base",
        "Kamaz Medical",
        "maker plus medical body; the model is not published for this retexture",
    ),
    (
        "LOP_KAMAZ_ammo_base",
        "KAMAZ (ammo)",
        "maker plus ammo body; the model is not published for this retexture",
    ),
    (
        "rhsusf_fmtv_base",
        "FMTV",
        "family label with no M-number token in the class name or the display",
    ),
    (
        "LOP_Nissan_PKM_base",
        "Nissan (PKM)",
        "maker plus the fitted PKM; no model is published for this technical",
    ),
)

# Modded aircraft gaps. Every one is an ArmaFPV FPV drone or its base class.
# No published source designates a "Crocus" FPV drone, so the corpus cannot
# name them without inventing a designation. The base game's "AR-2 Darter"
# display now resolves to the Parrot AR.Drone 2.0 and is locked as closed.
AIRCRAFT_OPEN_CASES: tuple[tuple[str, str], ...] = (
    ("ARMAFPV_Crocus_AT_Base", "Crocus AT"),
    ("ARMAFPV_Crocus_AP_Base", "Crocus AP"),
    ("O_Crocus_AT_TI", "Crocus AT TI"),
    ("O_Crocus_AP_TI", "Crocus AP TI"),
    ("B_Crocus_AT_TI", "Crocus AT TI"),
    ("B_Crocus_AP_TI", "Crocus AP TI"),
    ("I_Crocus_AT_TI", "Crocus AT TI"),
    ("I_Crocus_AP_TI", "Crocus AP TI"),
)

# The modded aircraft classes that resolve. The drone_base_F row is the base
# game's fictional quadcopter; the wiki names the Parrot AR.Drone 2.0 for it
# at grade "resemblance", which is enough for the keyword layer.
CLOSED_AIRCRAFT_CASES: tuple[tuple[str, str, str], ...] = (
    ("drone_base_F", "AR-2 Darter", "parrot_ar_drone_2"),
)


def fold(text: str) -> str:
    """Fold an identity to its lookup key, as the runtime normalise does."""
    return "".join(char for char in text.lower() if char.isascii() and char.isalnum())


def rows(path: Path) -> list[dict[str, object]]:
    """Parse the generated identity table of one matcher file."""
    out: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith('["'):
            continue
        parts = re.findall(r'"([^"]*)"', stripped)
        if len(parts) <= 6:
            continue
        out.append(
            {
                "id": parts[0],
                "classes": [x for x in parts[4].split("|") if x],
                "aliases": [x for x in parts[5].split("|") if x],
                "keywords": [x for x in parts[6].split("|") if x],
            }
        )
    return out


def resolve(table: list[dict[str, object]], name: str, display: str = "") -> str | None:
    """Mirror the runtime ladder: exact class, alias, keyword, closest.

    Layer one reads the CLASS alone, the later layers read the identity text
    the engine holds (class name, raw display name and its localisation).
    """
    identity = name + " " + display
    key = fold(name)
    query = fold(identity)
    tokens = {fold(token) for token in re.split(r"[ _\-.]+", identity) if fold(token)}
    hit = [row for row in table if key in row["classes"]]
    if len(hit) == 1:
        return str(hit[0]["id"])
    if len(hit) > 1:
        return None
    hit = [row for row in table if tokens & set(row["aliases"])]
    if len(hit) == 1:
        return str(hit[0]["id"])
    if len(hit) > 1:
        return None
    hit = [
        row
        for row in table
        if any(len(word) >= SCAN_MIN and word in query for word in row["keywords"])
    ]
    if len(hit) == 1:
        return str(hit[0]["id"])
    if len(hit) > 1:
        return None
    best: dict[str, object] | None = None
    best_score = runner_up = best_count = best_name = 0
    tie = False
    for row in table:
        terms = row["aliases"] + row["keywords"]
        score = sum(
            len(word) * (2 if any(char.isdigit() for char in word) else 1)
            for word in terms
            if len(word) >= SCAN_MIN and word in query
        )
        if score < SCAN_MIN:
            continue
        count = len(terms)
        longest = max((len(word) for word in terms), default=0)
        if score > best_score:
            runner_up, best_score, best = best_score, score, row
            best_count, best_name, tie = count, longest, False
        elif score == best_score:
            if count < best_count:
                best, best_count, best_name, tie = row, count, longest, False
            elif count == best_count:
                if longest < best_name:
                    best, best_name, tie = row, longest, False
                elif longest == best_name:
                    tie = True
        if score < best_score:
            runner_up = max(runner_up, score)
    if best is not None and not tie and best_score > runner_up:
        return str(best["id"])
    return None


class ClosedModdedVehicleTest(unittest.TestCase):
    """Every closed modded vehicle class resolves to the entry that names it."""

    table: list[dict[str, object]] = []

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = rows(VEHICLE_MATCH)

    def test_the_closed_modded_vehicle_class_count_is_twenty_one(self) -> None:
        self.assertEqual(21, len(CLOSED_VEHICLE_CASES))

    def test_each_closed_modded_vehicle_class_resolves(self) -> None:
        for name, display, want in CLOSED_VEHICLE_CASES:
            with self.subTest(game_class=name):
                self.assertEqual(want, resolve(self.table, name, display))

    def test_the_rg33l_plus_alias_names_one_entry(self) -> None:
        # M1237 is the uparmoured RG-33L "Plus" designation the held WarWheels
        # index states, so it must index one entry and no other.
        owners = [row["id"] for row in self.table if "m1237" in row["aliases"]]
        self.assertEqual(["bae_systems_rg_33l_6x6"], owners)

    def test_the_m1239_alias_names_one_entry(self) -> None:
        owners = [row["id"] for row in self.table if "m1239" in row["aliases"]]
        self.assertEqual(
            ["bae_systems_rg_33l_socom_armored_utility_vehicle_auv"], owners
        )

    def test_the_tahoe_alias_names_one_entry(self) -> None:
        owners = [row["id"] for row in self.table if "tahoe" in row["aliases"]]
        self.assertEqual(["chevrolet_tahoe_gmt900"], owners)


class OpenModdedVehicleTest(unittest.TestCase):
    """Every open modded vehicle class stays open, for a stated reason."""

    table: list[dict[str, object]] = []

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = rows(VEHICLE_MATCH)

    def test_a_static_weapon_emplacement_is_never_named_as_a_vehicle(self) -> None:
        for name in VEHICLE_EMPLACEMENT_CASES:
            with self.subTest(game_class=name):
                self.assertIsNone(resolve(self.table, name))

    def test_the_open_modded_vehicle_class_count_is_nineteen(self) -> None:
        # Seven fictional re-uses and twelve maker or family names. The count
        # is the measured modded gap list, so a class that leaves one table
        # has to arrive in another. The five StaticWeapon emplacements are
        # excluded from the denominator by kind, so they are not gaps.
        total = len(VEHICLE_FICTIONAL_REUSE_CASES) + len(VEHICLE_MAKER_OR_FAMILY_CASES)
        self.assertEqual(19, total)

    def test_every_open_class_states_a_one_line_reason(self) -> None:
        for name, _display, reason in (
            VEHICLE_FICTIONAL_REUSE_CASES + VEHICLE_MAKER_OR_FAMILY_CASES
        ):
            with self.subTest(game_class=name):
                self.assertTrue(reason.strip())
                self.assertNotIn("\n", reason)

    def test_a_fictional_display_re_use_stays_open(self) -> None:
        for name, display, _reason in VEHICLE_FICTIONAL_REUSE_CASES:
            with self.subTest(game_class=name):
                self.assertIsNone(resolve(self.table, name, display))

    def test_a_maker_or_family_name_stays_open(self) -> None:
        for name, display, _reason in VEHICLE_MAKER_OR_FAMILY_CASES:
            with self.subTest(game_class=name):
                self.assertIsNone(resolve(self.table, name, display))


class Kamaz4310EntryTest(unittest.TestCase):
    """The KamAZ-4310 entry publishes the truck and binds the Zamak classes.

    The wiki states the relation: "Zamak is simply Kamaz spelt backwards ...
    the real-life "KamAZ-4310" family of trucks that the Zamak is based on".
    That statement carries the Arma 3 Zamak classes to the entry. It does not
    carry the Project OPFOR KAMAZ retextures: no source says they retexture the
    Zamak, and a "kamaz" alias would also capture the RHS KamAZ-5350 classes,
    which is a false answer, so those classes stay open.
    """

    table: list[dict[str, object]] = []

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = rows(VEHICLE_MATCH)

    def test_the_entry_holds_only_sourced_values(self) -> None:
        capture = json.loads(
            (REPO / "data/vehicle/catalogue/kamaz_4310.json").read_text(
                encoding="utf-8"
            )
        )
        entries = [e for e in capture["entries"] if e["catalogue_id"] == "kamaz_4310"]
        self.assertEqual(1, len(entries))
        values = entries[0]["values"]
        self.assertTrue(values)
        for field, held in values.items():
            with self.subTest(field=field):
                for key in ("unit", "source", "locator", "state", "grade"):
                    self.assertTrue(held.get(key))

    def test_the_entry_advertises_the_model_and_not_the_maker(self) -> None:
        row = [r for r in self.table if r["id"] == "kamaz_4310"]
        self.assertEqual(1, len(row))
        terms = set(row[0]["aliases"]) | set(row[0]["keywords"])
        self.assertIn("kamaz4310", terms)
        self.assertNotIn("kamaz", terms)
        self.assertNotIn("4310", terms)

    def test_no_installed_kamaz_class_resolves_to_the_entry(self) -> None:
        for name, display, _reason in VEHICLE_MAKER_OR_FAMILY_CASES:
            if "KAMAZ" not in name.upper():
                continue
            with self.subTest(game_class=name):
                self.assertNotEqual("kamaz_4310", resolve(self.table, name, display))

    def test_the_rhs_kamaz_5350_still_resolves_to_the_5350(self) -> None:
        self.assertEqual(
            "kamaz_5350_mustang",
            resolve(self.table, "rhs_kamaz5350", "KamAZ-5350 Mustang"),
        )


class OpenModdedAircraftTest(unittest.TestCase):
    """The modded aircraft gaps stay open and the closed set is locked."""

    table: list[dict[str, object]] = []

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = rows(AIRCRAFT_MATCH)

    def test_the_closed_modded_aircraft_class_count_is_one(self) -> None:
        self.assertEqual(1, len(CLOSED_AIRCRAFT_CASES))

    def test_each_closed_modded_aircraft_class_resolves(self) -> None:
        for name, display, want in CLOSED_AIRCRAFT_CASES:
            with self.subTest(game_class=name):
                self.assertEqual(want, resolve(self.table, name, display))

    def test_every_modded_aircraft_gap_stays_open(self) -> None:
        for name, display in AIRCRAFT_OPEN_CASES:
            with self.subTest(game_class=name):
                self.assertIsNone(resolve(self.table, name, display))


if __name__ == "__main__":
    unittest.main()
