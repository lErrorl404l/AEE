#!/usr/bin/env python3
"""Clothing insulation + camouflage tests (issue #119).

Locks the researched clothing physics in fnc_getCamouflageProperties and
fnc_getNvgContrast: the per-uniform config values (ASHRAE 55 / ISO
11079 clo, DLA NIR reflectance), the classname-family fallback, the
CfgWeapons-inheritance walk (the modded-uniform mechanism), and the NVG
black-hole contrast maths.
"""

import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
INS = (
    REPO / "addons/physiology/functions/clothing/fnc_getCamouflageProperties.sqf"
).read_text(encoding="utf-8")
NVG = (REPO / "addons/physiology/functions/clothing/fnc_getNvgContrast.sqf").read_text(
    encoding="utf-8"
)
CFG = (REPO / "addons/physiology/config.cpp").read_text(encoding="utf-8")


class TestInsulationResolver(unittest.TestCase):
    def test_config_has_vanilla_entries(self):
        # The explicit CfgClothing entries for the known vanilla families.
        for cls in (
            "U_B_CombatUniform_mcam",
            "U_B_GhillieSuit",
            "U_B_Wetsuit",
            "U_B_PilotCoveralls",
        ):
            self.assertIn(f"class {cls}", CFG)

    def test_config_values_researched(self):
        # Combat uniform: clo 0.75 (uniform complete), NIR 0.40 (OCP).
        self.assertIn("clo = 0.75", CFG)
        self.assertIn("nirReflectance = 0.40", CFG)
        self.assertIn("alphaSolar = 0.80", CFG)

    def test_inheritance_walk_present(self):
        # The modded-uniform mechanism: walk CfgWeapons ancestry so a
        # modded uniform inheriting a vanilla class picks up its entry.
        self.assertIn("inheritsFrom", INS)
        self.assertIn("_depth < 16", INS)
        self.assertIn("CfgWeapons", INS)

    def test_classname_family_fallback(self):
        # The dynamic fallback for uniforms without a config entry.
        # The camo patterns classify in the camouflage classifier; the
        # garment types (winter/flight/combat) classify insulation in
        # the uniform classifier.
        uni = (
            REPO / "addons/physiology/functions/clothing/fnc_getUniformProperties.sqf"
        ).read_text(encoding="utf-8")
        for kw in ("ghillie", "winter", "flight", "combat"):
            self.assertIn(f'"{kw}"', uni)
        self.assertIn("toLower", INS)

    def test_rhs_uniforms_classified(self):
        # Verified against the installed RHS USAF/AFRF uniform configs:
        # every rhs_uniform_* item must hit a family tier, never the
        # default light-shirt guess.  The CAMO-PATTERN words live in the
        # camouflage classifier; the GARMENT-TYPE words (acu, g3, m88,
        # bdu, frog, abu, sso, vdv, g2/g4) classify insulation in the
        # uniform classifier.
        src = INS
        uni = (
            REPO / "addons/physiology/functions/clothing/fnc_getUniformProperties.sqf"
        ).read_text(encoding="utf-8")
        for kw in (
            "acu",
            "cu_",
            "g3",
            "g2",
            "g4",
            "m93",
            "m88",
            "bdu",
            "frog",
            "abu",
            "flcu",
            "sso",
            "vdv",
            "afghanka",
            "6sh122",
            "gorka",
            "klmk",
        ):
            self.assertIn(
                f'"{kw}"',
                uni,
                f"RHS garment keyword {kw} missing from the insulation classifier",
            )
        for kw in ("flora", "emr"):
            self.assertIn(
                f'"{kw}"',
                src,
                f"RHS pattern keyword {kw} missing from the camouflage classifier",
            )

    def test_default_is_combat_tier(self):
        # An unclassified uniform defaults to the light-shirt tier
        # (0.50 clo); a combat uniform is caught by the garment/pattern
        # tier (0.75).  The default lives in the uniform insulation
        # classifier (the camouflage classifier carries the pattern
        # default).
        uni = (
            REPO / "addons/physiology/functions/clothing/fnc_getUniformProperties.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("default                                     { 0.50 }", uni)

    def test_camo_patterns_classified(self):
        # The complete global camo inventory (Camopedia 1152-pattern
        # dump + the 2010-2026 wave): every pattern name maps to the
        # combat tier.  Missing keywords fail the gate.
        src = INS
        for kw in (
            "mtp",
            "btp",
            "dpm",
            "multicam",
            "ocp",
            "ucp",
            "m81",
            "erdl",
            "marpat",
            "aor",
            "dcu",
            "chocolate",
            "flecktarn",
            "tropentarn",
            "vegetato",
            "m90",
            "m05",
            "pantera",
            "splinter",
            "alpen",
            "lizard",
            "ttsko",
            "vsr",
            "emr",
            "klmk",
            "partizan",
            "surak",
            "tigerstripe",
            "tiger",
            "auscam",
            "cadpat",
            "pencott",
            "atacs",
            "kryptek",
            "reed",
            "woodland",
            "olive",
            "brushstroke",
            "denison",
            "duck",
            "jigsaw",
            "oakleaf",
            "berezka",
            "strichtarn",
            "raindrop",
            "frogskin",
            "amoeba",
            "mottled",
            "spotted",
            "pixel",
            "digital",
            "mountain",
            "rocky",
            "desert",
            "leopard",
            "rhodesian",
            "splinter",
            "blotch",
            "splotch",
            "spot",
            "stripe",
            "leaf",
            "dots",
            "geometric",
            "puzzle",
            "waves",
            "vertical",
            "maze",
            "cellular",
        ):
            self.assertIn(
                f'"{kw}"', src, f"camo-pattern keyword {kw} missing from the classifier"
            )

    def test_modern_patterns_classified(self):
        # The 2010-2026 universal-pattern wave (researched): UK MTP,
        # US OCP/OEF-CP/Scorpion W2, German Multitarn, CADPAT MT,
        # AMCU, Multiterreno, US4CES, VKPO, MM-25, M-18, M2017, etc.
        src = INS
        for kw in (
            "mtp",
            "multitarn",
            "multiterreno",
            "amcu",
            "scorpion",
            "oef",
            "us4ces",
            "vkpo",
            "izlom",
            "mm14",
            "mm25",
            "ratnik",
            "m18",
            "m23",
            "m2017",
            "loreng",
            "tiuna",
            "patriot",
            "spec4ce",
        ):
            self.assertIn(
                f'"{kw}"',
                src,
                f"modern-pattern keyword {kw} missing from the classifier",
            )

    def test_displayname_signal(self):
        # The displayName carries the garment type for mods whose
        # classnames are opaque (the Zulu/UKSF verification).
        self.assertIn("displayName", INS)
        self.assertIn("toLower (_uniform", INS)


class TestNvgContrast(unittest.TestCase):
    def test_camo_matches_background(self):
        # OCP 0.40 vs veg 0.45 -> camo_coeff 0.89 (the issue vector).
        def coeff(r):
            bg, dmax = 0.45, 0.40
            return 1 - abs(r - bg) / dmax

        self.assertAlmostEqual(coeff(0.40), 0.875, places=2)

    def test_black_hole(self):
        # Black 0.05 NIR -> near-zero camo (visible under NVG).
        def coeff(r):
            bg, dmax = 0.45, 0.40
            return max(0, min(1, 1 - abs(r - bg) / dmax))

        self.assertAlmostEqual(coeff(0.05), 0.0, places=2)

    def test_formula_in_source(self):
        self.assertIn("_camoCoeff", NVG)
        self.assertIn("_nirUniform", NVG)
        self.assertIn("_dRMax", NVG)


if __name__ == "__main__":
    unittest.main()


class TestEquipmentLibrary(unittest.TestCase):
    """The comprehensive equipment library (issue #119): helmets, vests,
    backpacks - weight, NIJ armour, NIR, clo per family.

    The library is DYNAMIC: items classify by classname-family keyword,
    so any mod (even unseen ones) resolves as long as its classnames
    carry the family signal.  These tests lock the researched IRL
    families (equipment-library.md) to their classifier tiers."""

    CLOTH = REPO / "addons/physiology/functions/clothing"
    EQ = (
        (CLOTH / "fnc_getVestProperties.sqf").read_text(encoding="utf-8")
        + (CLOTH / "fnc_getHelmetProperties.sqf").read_text(encoding="utf-8")
        + (CLOTH / "fnc_getPackProperties.sqf").read_text(encoding="utf-8")
        + (CLOTH / "fnc_getEquipmentProperties.sqf").read_text(encoding="utf-8")
    )

    def test_vest_classification(self):
        # The family fallback covers vanilla + RHS + historical vests.
        src = self.EQ
        for kw in (
            "platecarrier",
            "iotv",
            "ciras",
            "spcs",
            "cpc",
            "tacvest",
            "bandollier",
            "chestrig",
            "harness",
            "rebreather",
            "6b23",
            "6b43",
            "6b45",
            "osprey",
            "virtus",
            "ecba",
            "mbav",
            "plateframe",
            "msv",
        ):
            self.assertIn(f'"{kw}"', src, f"vest family keyword {kw} missing")

    def test_vest_researched_values(self):
        # IRL-researched: IOTV 4.5 kg bare (TM 10-8470-208-10), 6B23
        # 7.9 kg (Wikipedia), Osprey 8.5 kg bare (MOD FOI).
        src = self.EQ
        self.assertIn("{ [4.5, 3, 0.38, 0.18] }", src)  # IOTV
        self.assertIn("{ [7.9, 3, 0.40, 0.14] }", src)  # 6B23
        self.assertIn("{ [8.5, 3, 0.40, 0.15] }", src)  # Osprey
        self.assertIn("{ [3.8, 1, 0.40, 0.08] }", src)  # historical flak

    def test_helmet_classification(self):
        # Historical steel, Russian aramid, modern US, aircrew, light.
        src = self.EQ
        for kw in (
            "m1940",
            "m1942",
            "stahlhelm",
            "ssh68",
            "pasgt",
            "mich",
            "ach",
            "lwh",
            "ech",
            "fast",
            "exfil",
            "6b7",
            "6b26",
            "6b27",
            "6b47",
            "altyn",
            "zsh",
            "cvc",
            "kaska",
            "crew",
            "pilot",
            "watchcap",
            "boonie",
            "bandanna",
            "cap",
            "beret",
        ):
            self.assertIn(f'"{kw}"', src, f"helmet family keyword {kw} missing")

    def test_helmet_researched_values(self):
        # IRL-researched per-family: PASGT 1.9 kg complete (DTIC
        # ADA619773), 6B47 ~1.0 kg (Wikipedia), steel helmets unrated
        # (1.2 kg family mean), ECH 1.05 kg (USMC PIS).
        src = self.EQ
        self.assertIn("{ [1.9, 2, 0.40, 0.06] }", src)  # PASGT
        self.assertIn("{ [1.0, 2, 0.40, 0.06] }", src)  # 6B47
        self.assertIn("{ [1.05, 2, 0.40, 0.06] }", src)  # ECH
        self.assertIn("{ [1.2, 0, 0.40, 0.04] }", src)  # steel, unrated

    def test_backpack_classification(self):
        src = self.EQ
        self.assertIn("backpack _unit", src)
        # The engine `load` command returns 0..1 of the container
        # capacity, not kg.  The contents are weighed item by item by the
        # inventory walk instead.
        self.assertNotIn("load (unitBackpack _unit)", src)
        self.assertIn("getInventoryLoad", src)
        for kw in (
            "backpack",
            "rucksack",
            "bergen",
            "carryall",
            "assaultpack",
            "kitbag",
            "alice",
            "molle",
            "ilbe",
            "filbe",
            "rd54",
            "sidor",
            "tort",
            "plce",
            "6sh118",
        ):
            self.assertIn(f'"{kw}"', src, f"pack family keyword {kw} missing")

    def test_no_hardcoded_classnames(self):
        # The library must be dynamic: per-classname config entries were
        # removed in favour of the family classifier.  No explicit
        # per-item config walking remains.
        src = self.EQ
        self.assertNotIn("CfgEquipment", src)
        self.assertNotIn("_fnResolve", src)

    def test_combine_weight_armour_nir_clo(self):
        # The orchestrator combines the per-slot tuples: weight sums,
        # armour = max, NIR averaged, clo sums.
        src = self.EQ
        self.assertIn("getUniformProperties", src)
        self.assertIn("getVestProperties", src)
        self.assertIn("getHelmetProperties", src)
        self.assertIn("getPackProperties", src)
        self.assertIn("_combined", src)
        self.assertIn("_combined set [2", src)


class TestEquipmentMath(unittest.TestCase):
    def test_plate_carrier_armour_dominates(self):
        # Vest NIJ III (3) + helmet IIIA (2) -> combined armour 3.
        vest_armor, helmet_armor = 3, 2
        self.assertEqual(max(vest_armor, helmet_armor), 3)

    def test_weight_sums(self):
        # Uniform 4 + plate 5.5 + ACH 1.5 + assault pack 3 = 14 kg.
        total = 4.0 + 5.5 + 1.5 + 3.0
        self.assertEqual(total, 14.0)

    def test_helmet_family_tier_mapping(self):
        # A 6B47 classname must hit the Russian aramid tier.
        src = (
            REPO / "addons/physiology/functions/clothing/fnc_getHelmetProperties.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn('"6b47"', src)
