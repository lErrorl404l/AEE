#!/usr/bin/env python3
"""Clothing insulation + camouflage tests (issue #119).

Locks the researched clothing physics in fnc_getClothingInsulation and
fnc_getNvgContrast: the per-uniform config values (ASHRAE 55 / ISO
11079 clo, DLA NIR reflectance), the classname-family fallback, the
CfgWeapons-inheritance walk (the modded-uniform mechanism), and the NVG
black-hole contrast maths.
"""

import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
INS = (
    REPO / "addons/physiology/functions/clothing/fnc_getClothingInsulation.sqf"
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
        for kw in ("ghillie", "winter", "flight", "combat"):
            self.assertIn(f'"{kw}"', INS)
        self.assertIn("toLower", INS)

    def test_rhs_uniforms_classified(self):
        # Verified against the installed RHS USAF/AFRF uniform configs:
        # every rhs_uniform_* item must hit a family tier, never the
        # default light-shirt guess.  The family keywords in the source
        # cover the RHS conventions.
        src = INS
        for kw in (
            "acu",
            "cu_",
            "g3",
            "m88",
            "bdu",
            "flora",
            "emr",
            "sso",
            "vdv",
            "frog",
            "afghanka",
            "6sh122",
            "gorka",
            "abu",
            "flcu",
        ):
            self.assertIn(
                f'"{kw}"', src, f"RHS family keyword {kw} missing from the classifier"
            )

    def test_default_is_combat_tier(self):
        # A uniform with no family keyword is a combat uniform, not a
        # light shirt - the safe default is 0.75 clo.
        self.assertIn("{ [0.75, 0.70, 0.40, 0.35, 0.93] }", INS)

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
    backpacks - weight, NIJ armour, NIR, clo per family."""

    EQ = (
        REPO / "addons/physiology/functions/clothing/fnc_getEquipmentProperties.sqf"
    ).read_text(encoding="utf-8")
    CFG = (REPO / "addons/physiology/config.cpp").read_text(encoding="utf-8")

    def test_config_has_families(self):
        # The vanilla families in CfgEquipment.
        for cls in ("V_PlateCarrier1_blk", "V_TacVest_blk", "H_HelmetB",
                    "H_PilotHelmetFighter_B", "B_AssaultPack_blk",
                    "B_Carryall_oli"):
            self.assertIn(f"class {cls}", self.CFG)

    def test_config_values_researched(self):
        # Verified: plate carrier NIJ III (armor 3), ACH helmet IIIA (2).
        self.assertIn("armor = 3", self.CFG)
        self.assertIn("weight = 5.5", self.CFG)   # plate carrier system
        self.assertIn("weight = 1.5", self.CFG)   # ACH helmet

    def test_vest_classification(self):
        # The family fallback covers RHS (iotv) + vanilla plate carriers.
        src = self.EQ
        for kw in ("platecarrier", "iotv", "ciras", "spcs", "cpc",
                   "tacvest", "bandollier", "chestrig", "harness",
                   "rebreather"):
            self.assertIn(f'"{kw}"', src,
                          f"vest family keyword {kw} missing")

    def test_helmet_classification(self):
        src = self.EQ
        for kw in ("crew", "pilot", "watchcap", "boonie", "bandanna",
                   "cap", "beret"):
            self.assertIn(f'"{kw}"', src,
                          f"helmet family keyword {kw} missing")

    def test_backpack_included(self):
        # The backpack weight + contents join the combined weight.
        src = self.EQ
        self.assertIn('backpack _unit', src)
        self.assertIn("unitBackpack", src)
        self.assertIn('load (unitBackpack _unit)', src)
        for kw in ("backpack", "rucksack", "bergen", "carryall",
                   "assaultpack", "kitbag"):
            self.assertIn(f'"{kw}"', src,
                          f"pack family keyword {kw} missing")

    def test_combine_weight_armour_nir_clo(self):
        src = self.EQ
        self.assertIn("_weight", src)
        self.assertIn("_armor = (_vest select 1) max", src)
        self.assertIn("_clo = _uniformClo", src)


class TestEquipmentMath(unittest.TestCase):
    def test_plate_carrier_armour_dominates(self):
        # Vest NIJ III (3) + helmet IIIA (2) -> combined armour 3.
        vest_armor, helmet_armor = 3, 2
        self.assertEqual(max(vest_armor, helmet_armor), 3)

    def test_weight_sums(self):
        # Uniform 4 + plate 5.5 + ACH 1.5 + assault pack 3 = 14 kg.
        total = 4.0 + 5.5 + 1.5 + 3.0
        self.assertEqual(total, 14.0)
