#!/usr/bin/env python3
"""Research verification for the equipment classifier (issue #119).

Every tier in fnc_getEquipmentProperties.sqf must carry the researched
value from equipment-library.md.  This test extracts the (keywords ->
tier) mapping from the SQF and asserts the tier VALUES for each
researched family equal the research table.

The research table is the source of truth (equipment-library.md, all
values from manufacturer datasheets / army manuals / Wikipedia).  A
tier value that drifts from its research anchor fails this gate.

Run: python3 -m unittest tools/tests/test_equipment_values.py
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
FNC = (
    REPO / "addons/physiology/functions/clothing/fnc_getEquipmentProperties.sqf"
).read_text(encoding="utf-8")


def extract_tiers(slot_var):
    """Return {keyword: tier_string} from the switch on _<slot>."""
    m = re.search(
        rf"{slot_var} = switch \(true\) do \{{(.*?)\n    \}};",
        FNC,
        re.S,
    )
    if not m:
        raise SystemExit(f"switch block for _{slot_var} not found")
    body = m.group(1)
    tiers = {}
    for case in re.finditer(r"case\s*\((.*?)\):\s*\{(\s*\[[^\]]+\]\s*)\};", body, re.S):
        cond, tier = case.group(1), case.group(2)
        kws = re.findall(r'find "([^"]+)"', cond)
        tier = re.sub(r"\s+", " ", tier).strip()
        for kw in kws:
            tiers[kw] = tier
    return tiers


HELMET = extract_tiers("helmet")
VEST = extract_tiers("vest")
PACK = extract_tiers("pack")


class TestHelmetValues(unittest.TestCase):
    """Researched helmet weights (equipment-library.md)."""

    def assert_tier(self, kw, weight, armor, nir=0.40, clo=None, msg=""):
        self.assertIn(kw, HELMET, f"keyword {kw} missing")
        parts = [float(x) for x in re.findall(r"[0-9.]+", HELMET[kw])]
        self.assertAlmostEqual(
            parts[0], weight, delta=0.02, msg=f"{kw} weight (research {weight} kg)"
        )
        self.assertEqual(int(parts[1]), armor, msg=f"{kw} NIJ armour")
        if clo is not None:
            self.assertAlmostEqual(
                parts[3], clo, delta=0.01, msg=f"{kw} clo (research {clo})"
            )

    def test_historical_steel(self):
        # Stahlhelm M35/40/42 0.81-1.23 kg, M1 ~1.4, SSh-68 1.3.
        # Family mean 1.2 kg, unrated (armor 0).
        self.assert_tier("m1940", 1.2, 0, clo=0.04)
        self.assert_tier("stahlhelm", 1.2, 0, clo=0.04)
        self.assert_tier("ssh68", 1.2, 0, clo=0.04)

    def test_russian_aramid(self):
        # 6B47 ~1.0 kg (Wikipedia), 6B7-1M 1.1-1.2, 6B26/27 0.95-1.25,
        # 6B28 ~1.3.  All GOST 2 ~IIIA (armor 2).
        self.assert_tier("6b47", 1.0, 2, clo=0.06)
        self.assert_tier("6b7", 1.15, 2, clo=0.06)
        self.assert_tier("6b26", 1.1, 2, clo=0.06)
        self.assert_tier("6b28", 1.3, 2, clo=0.06)

    def test_heavy_sf(self):
        # Altyn ~2.1 kg with visor (titanium + aramid), IIA-class.
        self.assert_tier("altyn", 2.1, 2, clo=0.08)

    def test_pasgt(self):
        # PASGT 1.4 kg shell / 1.9 kg complete (DTIC ADA619773), IIIA.
        self.assert_tier("pasgt", 1.9, 2, clo=0.06)

    def test_modern_us(self):
        # MICH 1.36-1.63, ACH 1.36-1.72 (mean 1.5), IIIA.
        self.assert_tier("mich", 1.5, 2, clo=0.07)
        self.assert_tier("ach", 1.5, 2, clo=0.07)
        # ECH 1.0-1.1 (UHMWPE, USMC PIS).
        self.assert_tier("ech", 1.05, 2, clo=0.06)
        # Ops-Core FAST 0.63-0.89 shell, IIIA.
        self.assert_tier("opscore", 0.9, 2, clo=0.06)

    def test_aircrew(self):
        # HGU-55/P 0.91-1.1 kg, impact only (armor 1).
        self.assert_tier("hgu", 1.1, 1, nir=0.45, clo=0.15)
        # DH-132 ~1.4 kg frag.
        self.assert_tier("cvc", 1.4, 1, clo=0.05)


class TestVestValues(unittest.TestCase):
    """Researched vest weights (equipment-library.md)."""

    def assert_tier(self, kw, weight, armor, clo=None, msg=""):
        self.assertIn(kw, VEST, f"keyword {kw} missing")
        parts = [float(x) for x in re.findall(r"[0-9.]+", VEST[kw])]
        self.assertAlmostEqual(
            parts[0], weight, delta=0.05, msg=f"{kw} weight (research {weight} kg)"
        )
        self.assertEqual(int(parts[1]), armor, msg=f"{kw} NIJ armour")
        if clo is not None:
            self.assertAlmostEqual(
                parts[3], clo, delta=0.01, msg=f"{kw} clo (research {clo})"
            )

    def test_russian_6b(self):
        # 6B2 4.2-4.8 (mean 4.5), ~IIIA.  6B3T 12.2 / 6B3TM-01 8.2.
        self.assert_tier("6b2", 4.5, 2, clo=0.12)
        self.assert_tier("6b3", 10.0, 3, clo=0.13)
        # 6B4 12.0 / 6B4-01 7.6 (mean 9.5), ~III.
        self.assert_tier("6b4", 9.5, 3, clo=0.13)
        # 6B5 series 3-11.5 (mean 7.0), II-IIIA.
        self.assert_tier("6b5", 7.0, 2, clo=0.13)
        # 6B13 Zabralo 7-11 (mean 9.0), ~III.
        self.assert_tier("6b13", 9.0, 3, clo=0.14)
        # 6B23 7.2-10.2 full (7.9 steel front), III-IV.
        self.assert_tier("6b23", 7.9, 3, clo=0.14)
        # 6B43 9-13, 6B45 8-13 (mean 9-11), GOST 5a/6a ~III/IV.
        self.assert_tier("6b45", 9.0, 3, clo=0.15)

    def test_us_modern(self):
        # IOTV 4.47 kg bare (TM 10-8470-208-10), IIIA + IV plates.
        self.assert_tier("iotv", 4.5, 3, clo=0.18)
        # SPCS ~2.7 kg carrier, IV plates.
        self.assert_tier("spcs", 2.7, 3, clo=0.16)
        # CIRAS ~1.8 kg carrier, IIIA + IV plates.
        self.assert_tier("ciras", 3.5, 3, clo=0.15)
        # MBAV 7.3 kg.
        self.assert_tier("mbav", 5.5, 3, clo=0.16)

    def test_uk(self):
        # Osprey 8-9 kg bare (MOD FOI), Virtus 5-6 kg bare.
        self.assert_tier("osprey", 8.5, 3, clo=0.15)
        self.assert_tier("virtus", 5.5, 3, clo=0.14)
        # ECBA 4-5 kg aramid soft.
        self.assert_tier("ecba", 4.5, 2, clo=0.10)

    def test_historical_flak(self):
        # M-1952 3.8 kg, M-69 3.8 kg, unrated soft.
        self.assert_tier("m69", 3.8, 1, clo=0.08)
        self.assert_tier("m1952", 3.8, 1, clo=0.08)


class TestPackValues(unittest.TestCase):
    """Researched pack empty weights (equipment-library.md)."""

    def assert_tier(self, kw, weight, msg=""):
        self.assertIn(kw, PACK, f"keyword {kw} missing")
        parts = [float(x) for x in re.findall(r"[0-9.]+", PACK[kw])]
        self.assertAlmostEqual(
            parts[0], weight, delta=0.05, msg=f"{kw} weight (research {weight} kg)"
        )

    def test_irl_packs(self):
        self.assert_tier("rd54", 1.3)  # rf-gk.ru
        self.assert_tier("sidor", 2.2)  # 25-30 L class
        self.assert_tier("tort", 2.15)  # mbcgear
        self.assert_tier("alice", 3.2)  # Glens Surplus
        self.assert_tier("molle", 3.6)  # TM 10-8465-236-10
        self.assert_tier("ilbe", 3.6)  # Wikipedia/olive-drab
        self.assert_tier("filbe", 4.3)  # Venture Surplus
        self.assert_tier("plce", 2.45)  # SOS Outdoors
        self.assert_tier("virtus", 3.5)  # Becketts

    def test_vanilla_packs(self):
        # Vanilla assault 3.0, tactical 3.5, field 4.0, kitbag 4.0,
        # bergen 5.0, carryall 6.0 (empty weights).
        self.assert_tier("assaultpack", 3.0)
        self.assert_tier("tacticalpack", 3.5)
        self.assert_tier("fieldpack", 4.0)
        self.assert_tier("kitbag", 4.0)
        self.assert_tier("bergen", 5.0)
        self.assert_tier("carryall", 6.0)


if __name__ == "__main__":
    unittest.main()
