#!/usr/bin/env python3
"""Equipment classifier exhaustiveness harness (issue #119).

Mirrors the keyword tiers in fnc_getEquipmentProperties.sqf and runs
the ENTIRE known inventory (vanilla + RHS AFRF/USAF/GREF) through them.
Asserts that every real equipment family is classified - the only
allowed fall-throughs are known inventory noise (config base classes,
animation skeletons, vehicle weapons, cosmetics) and the ballistic
helmet default (which IS the correct IIIA tier for H_HelmetB).

The exhaustive principle: if the family signal exists in the classname
(helmet/vest/pack type + era + protection class), the classifier must
catch it.  Run as part of run_tests.py.

Run: python3 -m unittest tools/tests/test_equipment_classifier.py
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
CLOTHING = REPO / "addons/physiology/functions/clothing"
FNC_UNIFORM = (CLOTHING / "fnc_getUniformProperties.sqf").read_text(encoding="utf-8")
FNC_VEST = (CLOTHING / "fnc_getVestProperties.sqf").read_text(encoding="utf-8")
FNC_HELMET = (CLOTHING / "fnc_getHelmetProperties.sqf").read_text(encoding="utf-8")
FNC_GOGGLE = (CLOTHING / "fnc_getGoggleProperties.sqf").read_text(encoding="utf-8")
FNC_PACK = (CLOTHING / "fnc_getPackProperties.sqf").read_text(encoding="utf-8")
FNC_EQUIP = (CLOTHING / "fnc_getEquipmentProperties.sqf").read_text(encoding="utf-8")
INV = Path("/tmp/equip_extract/inventory.txt")

# The inventory is extracted from the INSTALLED game + RHS configs - a
# local artefact, not in CI.  When it is absent the coverage check
# skips (the classname-family verification needs the extraction); the
# SQF keywords are still verified by test_clothing / test_equipment_values.
if not INV.exists():
    raise unittest.SkipTest("equipment inventory not extracted (local-only check)")

# Known noise: config base classes, hitpoint classes, animation
# skeletons, vehicle-mounted weapons, cosmetic items.  These are NOT
# real equipment items; the inventory extraction picks them up from
# shared config.cpp files.  A fall-through to any of these is fine.
NOISE = re.compile(
    r"^(EventHandlers|Face|Head|HeadGearItem|HitpointsProtectionInfo|"
    r"InventoryItem_Base_F|InventoryMuzzleItem_Base_F|InventoryOpticsItem_Base_F|"
    r"ItemCore|ItemInfo|reference|1PN138|Abdomen|Body|Chest|Diaphragm|Neck|"
    r"Vest_Camo_Base|Bag_Base|Steerable_Parachute_F|TransportItems|"
    r"TransportMagazines|rhs_gear_OFF|rhs_cossack_base|rhs_uniform_cossack|"
    r"rhs_xmas_antlers|rhsusf_Bowman|rhsusf_Rhino|B_GMG|B_HMG|B_UAV|"
    r"B_Parachute|B_[0-9]_|B_[A-Z]$|B_AFV|B_APC|B_Boat|B_Brigade|B_Captain|"
    r"B_Aegis|B_Combat|B_Support|B_Curator|B_1|B_2|B_3|B_4|B_5|B_6|B_A|"
    r"rhs_d6_Parachute|rhsusf_eject_Parachute|rhs_1PN138|_xx_)"
)


def extract_tiers(slot_var, source=None):
    """Return ordered [(keywords, tier_string)] from the switch on _<slot>.
    The per-slot files return a standalone `switch (true) do {...};`."""
    if source is None:
        source = FNC_EQUIP
    m = re.search(
        rf"switch \(true\) do \{{(.*?)\n\}};",
        source,
        re.S,
    )
    if not m:
        raise SystemExit(f"switch block for _{slot_var} not found")
    body = m.group(1)
    tiers = []
    for case in re.finditer(r"case\s*\((.*?)\):\s*\{(\s*\[[^\]]+\]\s*)\};", body, re.S):
        cond, tier = case.group(1), case.group(2)
        kws = re.findall(r'find "([^"]+)"', cond)
        tiers.append((kws, re.sub(r"\s+", " ", tier).strip()))
    return tiers


def classify(name, tiers):
    n = name.lower()
    for kws, tier in tiers:
        if any(k in n for k in kws):
            return tier
    return "DEFAULT"


# Vanilla goggles families (G_ classes) - every one must classify.
VANILLA_GOGGLES = [
    "G_Balaclava_blk",
    "G_Bandanna_aviator",
    "G_Combat",
    "G_Diving",
    "G_Lady_Blue",
    "G_Lowprofile",
    "G_Shades_Black",
    "G_Spectacles",
    "G_Sport_Blackred",
    "G_Squares_Tinted",
    "G_Tactical_Clear",
    "G_Aviator",
    "G_Goggles_VR",
]


def load_inventory():
    sections, cur = {}, None
    for line in INV.read_text(encoding="utf-8").splitlines():
        if line.startswith("== "):
            cur = line.strip("= ").strip()
            sections[cur] = []
        elif cur and line.strip():
            sections[cur].append(line.strip())
    return sections


class TestClassifierExhaustiveness(unittest.TestCase):
    """Every real equipment family in the known inventory classifies."""

    @classmethod
    def setUpClass(cls):
        cls.inv = load_inventory()
        cls.helmet_tiers = extract_tiers("_h", FNC_HELMET)
        cls.vest_tiers = extract_tiers("_v", FNC_VEST)
        cls.pack_tiers = extract_tiers("_b", FNC_PACK)
        cls.goggle_tiers = extract_tiers("_g", FNC_GOGGLE)

    def _fall_through(self, slot, tiers):
        bad = []
        for n in self.inv[slot]:
            if classify(n, tiers) == "DEFAULT" and not NOISE.match(n):
                bad.append(n)
        return bad

    def test_all_helmets_classified(self):
        bad = self._fall_through("HELMETS", self.helmet_tiers)
        self.assertFalse(
            bad,
            f"helmet families missing classifier keywords: {sorted(bad)[:20]}",
        )

    def test_all_vests_classified(self):
        bad = self._fall_through("VESTS", self.vest_tiers)
        self.assertFalse(
            bad, f"vest families missing classifier keywords: {sorted(bad)[:20]}"
        )

    def test_all_packs_classified(self):
        bad = self._fall_through("PACKS", self.pack_tiers)
        self.assertFalse(
            bad, f"pack families missing classifier keywords: {sorted(bad)[:20]}"
        )

    def test_all_goggles_classified(self):
        # Every vanilla goggles-slot family must classify (no default).
        for name in VANILLA_GOGGLES:
            tier = classify(name, self.goggle_tiers)
            self.assertNotEqual(
                tier, "DEFAULT", f"goggles family {name} falls through to default"
            )

    def test_goggle_slot_wired(self):
        # The goggles slot is read and combined into the signature.
        self.assertIn("goggles _unit", FNC_GOGGLE)
        self.assertIn("getGoggleProperties", FNC_EQUIP)
        self.assertIn("_goggle select 0", FNC_EQUIP)

    def test_per_slot_functions_exist(self):
        # The split: one classifier file per slot.
        self.assertIn("getUniformProperties", FNC_EQUIP)
        self.assertIn("getVestProperties", FNC_EQUIP)
        self.assertIn("getHelmetProperties", FNC_EQUIP)
        self.assertIn("getPackProperties", FNC_EQUIP)

    def test_keywords_present_in_sqf(self):
        # The mirror's tier lists must be non-empty (extraction works).
        self.assertGreater(len(self.helmet_tiers), 10)
        self.assertGreater(len(self.vest_tiers), 10)
        self.assertGreater(len(self.pack_tiers), 8)
        self.assertGreater(len(self.goggle_tiers), 4)


if __name__ == "__main__":
    unittest.main()
