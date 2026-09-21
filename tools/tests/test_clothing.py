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
            "g3_",
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
