#!/usr/bin/env python3
"""Modded-class resolution locks (vehicle and aircraft identity ladders).

The runtime matchers name a game class from the class text and the display
name. The vehicle matcher has one more layer: where the text names nothing,
the ENGINE ancestry answers, from the config parent chain. A modded class
resolves when its own text carries a designation the catalogue entry
publishes - the exact mapped class, a curated alias, a keyword or the closest
layer - or, on the vehicle side, when it is a descendant of an ancestor the
table names AND its own text names what that ancestor's entry is. It resolves
to nothing when neither holds, and that is the correct answer: the matcher
never guesses.

This module locks the modded gaps that were closed and the modded classes
that stay open on purpose. Each closed class names the catalogue entry it
must resolve to; each inherited one also names the config chain that puts it
there. Each open class is listed with the reason it stays open, so a later
change that closes or breaks one shows up here.

The vehicle table closes thirty-nine modded classes: twenty-one by their own
text (the RHS M1237 RG-33L "Plus" and M1239 SOCOM AUV families, the PHAN
Typhoon truck, the four Tahoe marks, the RHS Object 681, the Jbad Caterpillar
789D, and the five the counterpart research closed), one more by the
identity-only entry its text names (the Project OPFOR Nissan pickup), and
seventeen by engine ancestry - the seven Arma 3 Offroad re-uses and the ten
Project OPFOR KAMAZ trucks, whose chain reaches the Zamak that the wiki ties
to the KamAZ-4310 family.

An inherited closure says the class IS that ancestor in the engine. It does
not say the mod's own paint names a different real vehicle, because where the
class text names a different article the rung refuses. The FMTV family now has
an identity-only entry too, but it stays open: every term that would reach
`rhsusf_fmtv_base` also reaches other classes, so the entry advertises none of
them and the class is refused rather than trade four classes for one.
`LOP_Nissan_PKM_base` closes on the maker alias, which names no other class.
The base game's fictional M4 Scorcher also stays open, and it is not a modded
gap.

The aircraft table closed one: the base game's fictional AR-2 Darter, whose
display name the wiki ties to the Parrot AR.Drone 2.0. Every remaining
aircraft gap is an ArmaFPV first-person-view drone whose own text ("Crocus
AT TI") states no designation any published source holds, so a row would have
to invent one.

The KamAZ-4310 entry publishes the real truck and binds the Arma 3 Zamak
classes through the wiki's own statement ("Zamak is simply Kamaz spelt
backwards, which is the name of the company that designs the real-life
"KamAZ-4310" family of trucks that the Zamak is based on"). The Project OPFOR
KAMAZ trucks carry no 4310 token, so no text layer may name them: an alias on
the maker word would also capture the RHS KamAZ-5350, which is a different
truck. The chain separates them, because the 5350 does not descend from the
Zamak.

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
    # Closed by the 2026-10-20 identity-only capture: the class names its
    # entry from its own text, so it never reaches the ancestry rung.
    ("LOP_Nissan_PKM_base", "Nissan (PKM)", "nissan_pickup_technical"),
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

# The modded classes the inherited rung closes: the class, its display, the
# config chain from the class to the nearest ancestor the table maps by
# classname, and the entry that ancestor names. A closure here says the class
# IS that ancestor in the engine, and that its own text names what the
# ancestor's entry is. It does not say the mod's paint names another article.
INHERITED_VEHICLE_CASES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "CBRN_Offroad",
        "Offroad",
        ("Offroad_01_civil_base_F", "Offroad_01_unarmed_base_F"),
        "offroad_q7_l200_composite",
    ),
    (
        "LOP_Offroad_base",
        "Offroad",
        ("Offroad_01_civil_base_F", "Offroad_01_unarmed_base_F"),
        "offroad_q7_l200_composite",
    ),
    (
        "LOP_AA_Offroad",
        "ANA Offroad",
        ("LOP_Offroad_base", "Offroad_01_civil_base_F", "Offroad_01_unarmed_base_F"),
        "offroad_q7_l200_composite",
    ),
    (
        "LOP_AA_Offroad_Police",
        "ANP Offroad",
        ("LOP_Offroad_base", "Offroad_01_civil_base_F", "Offroad_01_unarmed_base_F"),
        "offroad_q7_l200_composite",
    ),
    (
        "LOP_Offroad_M2_base",
        "Offroad (M2)",
        ("Offroad_01_armed_base_F", "Offroad_01_military_base_F", "Offroad_01_base_F"),
        "offroad_q7_l200_composite",
    ),
    (
        "LOP_AA_Offroad_M2",
        "ANA Offroad (M2)",
        (
            "LOP_Offroad_M2_base",
            "Offroad_01_armed_base_F",
            "Offroad_01_military_base_F",
            "Offroad_01_base_F",
        ),
        "offroad_q7_l200_composite",
    ),
    (
        "LOP_AA_Offroad_M2_Police",
        "ANP Offroad (M2)",
        (
            "LOP_Offroad_M2_base",
            "Offroad_01_armed_base_F",
            "Offroad_01_military_base_F",
            "Offroad_01_base_F",
        ),
        "offroad_q7_l200_composite",
    ),
    # The ten Project OPFOR KAMAZ retextures. Their chain reaches the Zamak,
    # which the catalogue maps to the KamAZ-4310 on the wiki's own statement,
    # and their own text carries the maker word "kamaz", so the rung answers.
    ("LOP_KAMAZ_fuel_base", "KamAZ (fuel)", ("O_Truck_02_fuel_F",), "kamaz_4310"),
    (
        "LOP_UKR_KAMAZ_Fuel",
        "KAMAZ (fuel)",
        ("LOP_KAMAZ_fuel_base", "O_Truck_02_fuel_F"),
        "kamaz_4310",
    ),
    (
        "LOP_CDF_KAMAZ_Fuel",
        "KAMAZ (fuel)",
        ("LOP_KAMAZ_fuel_base", "O_Truck_02_fuel_F"),
        "kamaz_4310",
    ),
    (
        "LOP_IRAN_KAMAZ_Fuel",
        "KAMAZ (fuel)",
        ("LOP_KAMAZ_fuel_base", "O_Truck_02_fuel_F"),
        "kamaz_4310",
    ),
    (
        "LOP_SYR_KAMAZ_Fuel",
        "KAMAZ (fuel)",
        ("LOP_KAMAZ_fuel_base", "O_Truck_02_fuel_F"),
        "kamaz_4310",
    ),
    ("LOP_KAMAZ_cov_base", "KAMAZ (covered)", ("O_Truck_02_covered_F",), "kamaz_4310"),
    ("LOP_KAMAZ_trans_base", "KAMAZ (open)", ("O_Truck_02_transport_F",), "kamaz_4310"),
    ("LOP_KAMAZ_rep_base", "KAMAZ (repair)", ("O_Truck_02_box_F",), "kamaz_4310"),
    ("LOP_KAMAZ_med_base", "Kamaz Medical", ("O_Truck_02_medical_F",), "kamaz_4310"),
    ("LOP_KAMAZ_ammo_base", "KAMAZ (ammo)", ("O_Truck_02_Ammo_F",), "kamaz_4310"),
)

# The base-game Offroad classes are mapped classes, so the exact layer names
# them and the rung is never reached. They are locked here to prove the rule
# is about the ENGINE ancestry and not about who declares the class.
EXACT_BASE_CASES: tuple[tuple[str, str, str], ...] = (
    ("Offroad_01_repair_base_F", "Offroad (Repair)", "offroad_q7_l200_composite"),
    ("Offroad_01_AT_base_F", "Offroad (AT)", "offroad_q7_l200_composite"),
    ("C_Offroad_01_repair_F", "Offroad (Services)", "offroad_q7_l200_composite"),
)

# The chain the identity-only closure walks. It ends at the engine's own Car
# class, the nearest ancestor the table maps, so a lock can prove the closure
# is the class text and not the ancestry.
IDENTITY_ONLY_VEHICLE_CASES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "LOP_Nissan_PKM_base",
        "Nissan (PKM)",
        ("PO_Pickup_PK_base", "Car_F", "Car"),
        "nissan_pickup_technical",
    ),
)

# The modded classes that stay open, with the reason. The FMTV family has an
# identity-only entry, but every term that would reach the class reaches
# another class too: fmtv as an alias stops 69 classes and moves four, and as
# a keyword it ties the four SOV classes that resolve on that layer.
_FMTV_TAIL = ("Truck_01_base_F", "Truck_F", "Car_F", "Car")

VEHICLE_OPEN_CASES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "rhsusf_fmtv_base",
        "FMTV",
        _FMTV_TAIL,
        "the family designation fmtv as an alias stops 69 classes and moves four; as a keyword it ties the four SOV classes, so their layer returns nothing",
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


def ancestor_blob(row: dict[str, object]) -> str:
    """The identity text one entry is published under, folded."""
    parts = [
        str(row["id"]),
        *[str(x) for x in row["aliases"]],
        *[str(x) for x in row["keywords"]],
    ]
    return fold("|".join(parts))


def claims(row: dict[str, object], tokens: set[str]) -> bool:
    """True when a class token names something the entry is identified by."""
    blob = ancestor_blob(row)
    return any(len(token) >= SCAN_MIN and token in blob for token in tokens)


def named_ancestor(
    table: list[dict[str, object]], name: str
) -> dict[str, object] | None:
    """The one entry that maps this ancestor classname, or None.

    The mapped-class test only: a mod may rewrite any ancestor's displayName,
    so the classname is the evidence and the text is not.
    """
    key = fold(name)
    hit = [row for row in table if key in row["classes"]]
    return hit[0] if len(hit) == 1 else None


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


def resolve(
    table: list[dict[str, object]],
    name: str,
    display: str = "",
    chain: tuple[str, ...] | None = None,
) -> str | None:
    """Mirror the runtime ladder: exact, alias, keyword, closest, inherited.

    Layer one reads the CLASS alone, the later layers read the identity text
    the engine holds (class name, raw display name and its localisation). The
    inherited layer needs the engine class tree, so the caller passes the
    config chain, nearest ancestor first. Without a chain it cannot run.
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
    if chain is None:
        return None
    # Layer 6: inherited. The nearest ancestor the table names answers, and
    # only for a class whose own text names that entry.
    tokens = {fold(token) for token in re.split(r"[ _\-.]+", identity) if fold(token)}
    for ancestor in chain:
        found = named_ancestor(table, ancestor)
        if found is None:
            continue
        return str(found["id"]) if claims(found, tokens) else None
    return None


class ClosedModdedVehicleTest(unittest.TestCase):
    """Every closed modded vehicle class resolves to the entry that names it."""

    table: list[dict[str, object]] = []

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = rows(VEHICLE_MATCH)

    def test_the_closed_modded_vehicle_class_count_is_twenty_two(self) -> None:
        self.assertEqual(22, len(CLOSED_VEHICLE_CASES))

    def test_each_closed_modded_vehicle_class_resolves(self) -> None:
        for name, display, want in CLOSED_VEHICLE_CASES:
            with self.subTest(game_class=name):
                self.assertEqual(want, resolve(self.table, name, display))

    def test_the_closed_modded_vehicle_class_count_is_thirty_nine(self) -> None:
        # Twenty-two by their own text and seventeen by engine ancestry.
        self.assertEqual(
            22 + 17, len(CLOSED_VEHICLE_CASES) + len(INHERITED_VEHICLE_CASES)
        )

    def test_each_inherited_class_is_a_descendant_of_the_ancestor_that_answers(
        self,
    ) -> None:
        # The chain is the claim. Its head is the class, its tail the nearest
        # ancestor the table names, and the entry is that ancestor's.
        for name, display, chain, want in INHERITED_VEHICLE_CASES:
            with self.subTest(game_class=name):
                self.assertGreater(len(chain), 0)
                self.assertEqual(want, resolve(self.table, name, display, chain))
                self.assertNotEqual(
                    want,
                    resolve(self.table, name, display),
                    "the class must have no identity of its own",
                )

    def test_a_mapped_base_class_is_named_by_the_exact_layer(self) -> None:
        for name, display, want in EXACT_BASE_CASES:
            with self.subTest(game_class=name):
                self.assertEqual(want, resolve(self.table, name, display))

    def test_an_inherited_class_needs_its_chain(self) -> None:
        for name, display, _chain, _want in INHERITED_VEHICLE_CASES:
            with self.subTest(game_class=name):
                self.assertIsNone(resolve(self.table, name, display))

    def test_ancestry_alone_names_nothing(self) -> None:
        # A class descended from a mapped class, whose own text names that
        # entry nowhere, is a different article. The rung refuses it, so a
        # short chain can never become a guess.
        self.assertIsNone(
            resolve(
                self.table,
                "Mod_Anonymous_Body",
                "",
                ("Offroad_01_base_F",),
            )
        )

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

    def gap_classes(self) -> dict:
        body = (REPO / "data/coverage/modded_gaps_vehicles.txt").read_text(
            encoding="utf-8"
        )
        out = {}
        for line in body.splitlines():
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            out[fields[0]] = fields[1]
        return out

    def test_every_class_in_the_gap_list_is_open(self) -> None:
        # The gap list is the measured worklist. If the matcher can name a
        # class the list calls open, the list is lying about the engine.
        for name, display in self.gap_classes().items():
            with self.subTest(game_class=name):
                self.assertIsNone(resolve(self.table, name, display))

    def test_every_documented_open_case_is_in_the_gap_list(self) -> None:
        listed = self.gap_classes()
        for name, display, _chain, _reason in VEHICLE_OPEN_CASES:
            with self.subTest(game_class=name):
                self.assertIn(name, listed)
                self.assertEqual(display, listed[name])

    def test_every_open_class_states_a_one_line_reason(self) -> None:
        for name, _display, _chain, reason in VEHICLE_OPEN_CASES:
            with self.subTest(game_class=name):
                self.assertTrue(reason.strip())
                self.assertNotIn("\n", reason)

    def test_an_open_class_is_refused_with_and_without_its_chain(self) -> None:
        # Open means the rung looked and refused, not that the chain is short:
        # these classes have a nearest named ancestor, and it is another
        # article.
        for name, display, chain, _reason in VEHICLE_OPEN_CASES:
            with self.subTest(game_class=name):
                self.assertIsNone(resolve(self.table, name, display))
                self.assertIsNone(resolve(self.table, name, display, chain))


class IdentityOnlyVehicleEntryTest(unittest.TestCase):
    """The two identity-only entries name a vehicle and hold no figure.

    Both exist because the class text names an article the ancestry does not.
    The Nissan closes on the maker alias. The FMTV entry names the family but
    advertises no match term, because every term that would reach its class
    also reaches another one, so that class stays open. The lock holds the
    entry shape as well as both outcomes: no figure, no invented model
    designation, no M-number, and no term that captures a class which already
    resolves elsewhere.
    """

    table: list[dict[str, object]] = []

    # The four M-number classes whose own name carries "fmtv". They resolved
    # to their own entries before the family entry existed, and they must
    # still do so after it.
    M_NUMBER_CASES: tuple[tuple[str, str, str], ...] = (
        (
            "rhsusf_M1078A1R_SOV_M2_D_fmtv_socom",
            "M1078A1R SOV (M2)",
            "m1078a1r_socom_sov",
        ),
        (
            "rhsusf_M1078A1R_SOV_M2_WD_fmtv_socom",
            "M1078A1R SOV (M2)",
            "m1078a1r_socom_sov",
        ),
        (
            "rhsusf_M1084A1R_SOV_M2_D_fmtv_socom",
            "M1084A1R SOV (M2)",
            "m1084a1r_socom_sov",
        ),
        (
            "rhsusf_M1084A1R_SOV_M2_WD_fmtv_socom",
            "M1084A1R SOV (M2)",
            "m1084a1r_socom_sov",
        ),
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = rows(VEHICLE_MATCH)

    def entry(self, name: str) -> dict[str, object]:
        capture = json.loads(
            (REPO / "data/vehicle/catalogue" / name).read_text(encoding="utf-8")
        )
        self.assertEqual(1, len(capture["entries"]))
        return capture["entries"][0]

    def test_each_entry_is_identity_only_and_holds_no_figure(self) -> None:
        for name in ("nissan_pickup_technical.json", "fmtv_family.json"):
            with self.subTest(capture=name):
                entry = self.entry(name)
                self.assertIs(True, entry["identity_only"])
                self.assertEqual({}, entry["values"])
                self.assertIs(False, entry["runtime_ready"])
                self.assertEqual("", entry["class_token"])

    def test_the_nissan_entry_asserts_the_maker_and_no_model(self) -> None:
        entry = self.entry("nissan_pickup_technical.json")
        self.assertEqual("Nissan", entry["maker"])
        self.assertEqual(["nissan"], entry["aliases"])
        self.assertNotIn("pkm", entry["aliases"])
        identity = fold(
            " ".join(str(entry[key]) for key in ("canonical_name", "model", "variant"))
        )
        for invented in ("d21", "navara", "hardbody"):
            self.assertNotIn(invented, identity)

    def test_the_nissan_class_resolves_from_its_own_text(self) -> None:
        name, display, _chain, want = IDENTITY_ONLY_VEHICLE_CASES[0]
        self.assertEqual(want, resolve(self.table, name, display))
        self.assertNotEqual(
            "honda_civic_6gen_sedan", resolve(self.table, name, display)
        )

    def test_the_family_entry_claims_no_m_number(self) -> None:
        entry = self.entry("fmtv_family.json")
        identity = fold(
            " ".join(
                [str(entry[key]) for key in ("canonical_name", "model", "variant")]
                + [str(x) for x in entry["aliases"]]
                + [str(x) for x in entry["keywords"]]
            )
        )
        self.assertIsNone(re.search(r"m10\d\d", identity))

    def test_the_family_entry_advertises_no_match_term(self) -> None:
        # The measured reason the class stays open: every term that reaches
        # rhsusf_fmtv_base also reaches another class, so the entry carries
        # none and the class is refused.
        row = [r for r in self.table if r["id"] == "fmtv_family"]
        self.assertEqual(1, len(row))
        self.assertEqual([], row[0]["aliases"])
        self.assertNotIn("fmtv", row[0]["keywords"])
        name, display, chain, _want = VEHICLE_OPEN_CASES[0]
        self.assertIsNone(resolve(self.table, name, display))
        self.assertIsNone(resolve(self.table, name, display, chain))

    def test_each_m_number_class_still_resolves_to_its_own_entry(self) -> None:
        for name, display, want in self.M_NUMBER_CASES:
            with self.subTest(game_class=name):
                self.assertEqual(want, resolve(self.table, name, display))

    def test_the_family_alias_would_capture_the_m_number_classes(self) -> None:
        # An alias is matched by equality, so fmtv as an alias answers the
        # classes whose own name carries the token and ties the rest, which
        # the strict mirror reads as no answer.
        family = [r for r in self.table if r["id"] == "fmtv_family"][0]
        fixed = [dict(r) for r in self.table if r["id"] != "fmtv_family"]
        fixed.append({**family, "aliases": ["fmtv"], "keywords": []})
        for name, display, want in self.M_NUMBER_CASES:
            with self.subTest(game_class=name):
                self.assertNotEqual(want, resolve(fixed, name, display))
        self.assertIsNone(resolve(fixed, "rhsusf_M1078A1P2_fmtv_usarmy", "M1078A1P2"))

    def test_the_family_keyword_would_tie_the_sov_classes(self) -> None:
        # A keyword is matched by substring, so fmtv on that layer meets the
        # SOV classes' own keyword and the layer yields two candidates. The
        # runtime returns nothing from a tied layer, so they stop resolving.
        family = [r for r in self.table if r["id"] == "fmtv_family"][0]
        fixed = [dict(r) for r in self.table if r["id"] != "fmtv_family"]
        fixed.append({**family, "aliases": [], "keywords": ["fmtv"]})
        for name, display, _want in self.M_NUMBER_CASES:
            with self.subTest(game_class=name):
                self.assertIsNone(resolve(fixed, name, display))


class Kamaz4310EntryTest(unittest.TestCase):
    """The KamAZ-4310 entry publishes the truck and binds the Zamak classes.

    The wiki states the relation: "Zamak is simply Kamaz spelt backwards ...
    the real-life "KamAZ-4310" family of trucks that the Zamak is based on".
    That statement carries the Arma 3 Zamak classes to the entry, and through
    the Zamak it carries the Project OPFOR KAMAZ retextures, because they are
    that body in another paint. It does not carry them by text: no retexture
    states the model, and a "kamaz" alias would also capture the RHS
    KamAZ-5350 classes, which is a false answer, so the maker word stays out
    of the entry's terms and the chain is what answers.
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

    def test_every_kamaz_retexture_reaches_the_entry_only_through_its_chain(
        self,
    ) -> None:
        # The retextures descend from the Zamak in config, and the catalogue
        # maps the Zamak to the KamAZ-4310 on the wiki's statement. The chain
        # is the evidence: no class text carries a model, so the text layers
        # never answer, and the maker word alone would also capture the
        # KamAZ-5350, a different truck.
        seen = 0
        for name, display, chain, want in INHERITED_VEHICLE_CASES:
            if "KAMAZ" not in name.upper():
                continue
            seen += 1
            with self.subTest(game_class=name):
                self.assertEqual("kamaz_4310", want)
                self.assertEqual(
                    "kamaz_4310", resolve(self.table, name, display, chain)
                )
                self.assertIsNone(resolve(self.table, name, display))
        self.assertEqual(10, seen)

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
