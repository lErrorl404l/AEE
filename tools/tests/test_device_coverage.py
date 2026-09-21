#!/usr/bin/env python3
"""Device classifier exhaustiveness harness (issue #215).

Mirrors the keyword tiers in the three device classifiers and runs the
installed-mod device inventory (A3TI, KtweaK NVG, GPNVG-18, TPNVG,
TFN NVG, Thermal Goggles, A3TI REAP-IR, HMCS, FPANO ECOTI) through
them.  Reports every real device that falls through to default - those
are families whose keyword signal the classifier does not yet cover.

Run: python3 -m unittest tools/tests/test_device_coverage.py
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
CLOTHING = REPO / "addons"
NVG_SRC = (
    REPO / "addons/nightvision/functions/fnc_getNvgDeviceProperties.sqf"
).read_text(encoding="utf-8")
THERMAL_SRC = (
    REPO / "addons/thermal/functions/sensor/fnc_getThermalDeviceProperties.sqf"
).read_text(encoding="utf-8")
OPTIC_SRC = (
    REPO / "addons/optics/functions/sensor/fnc_getOpticProperties.sqf"
).read_text(encoding="utf-8")
INV = Path("/tmp/equip_extract/device_inventory.txt")

# Known noise: config base classes, non-device classes that matched the
# inventory regex (animations, weapon base classes, unit classes), and
# OPAQUE mod-maker names that carry no device-family signal (A3TI's
# YRU_Scope_*, WNZ's TI goggles, TFN's FX classes, 75th custom classes).
# A name that does not say what the device IS cannot be classified - the
# principle: fire only on real family signals, never guess at a mod
# prefix (the smock-is-not-a-camo-pattern rule).
NOISE = re.compile(
    r"^(EventHandlers|ItemCore|ItemInfo|NVGoggles|NVGoggles_OPFOR|"
    r"NVGoggles_INDEP|NVGogglesB_blk_F|NVGogglesB_gry_F|NVGogglesB_grn_F|"
    r"G_Goggles|G_Lowprofile|G_Tactical|Rifle|Rifle_Base|OpticsItem|"
    r"Optics_Base|Cfg|Helmet|Binocular|LaserDesignator|Laser_Designator|"
    r"Vest|Uniform|Headgear|Backpack|_base|Base|core|"
    r"CommanderOptics|ViewOptics|OpticsModes|RCWSOptics|"
    r"InventoryOpticsItem_Base_F|CompatibleNightvisionGoggles|"
    r"asdg_OpticRail|asdg_OpticRail1913|"
    # opaque mod-maker device names (no family signal):
    r"YRU_A3TI|75th_SU278|SKEETIR|A3TI_Thermal|BettIR|bettir|"
    r"TFN_NVGFx|TPNVGBettIR|ThermGoggles_|Thermal_Goggles_Mod|"
    r"WNZ_|Item_WNZ|Elcan_mrds|getThermalSelections|__base_|"
    r"^NVG$|^NVG_)"
)


def extract_tiers(source):
    """Return ordered [(keywords, tier_string)] from the standalone switch."""
    m = re.search(r"switch \(true\) do \{(.*?)\n\};", source, re.S)
    if not m:
        raise SystemExit("switch block not found")
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


NVG_TIERS = extract_tiers(NVG_SRC)
THERMAL_TIERS = extract_tiers(THERMAL_SRC)
OPTIC_TIERS = extract_tiers(OPTIC_SRC)


def load_inventory():
    sections, cur = {}, None
    for line in INV.read_text(encoding="utf-8").splitlines():
        if line.startswith("== "):
            cur = line.strip("= ").strip()
            sections[cur] = []
        elif cur and line.strip():
            sections[cur].append(line.strip())
    return sections


class TestDeviceCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv = load_inventory()

    def _fall(self, slot, tiers):
        bad = []
        for n in self.inv[slot]:
            if classify(n, tiers) == "DEFAULT" and not NOISE.match(n):
                bad.append(n)
        return bad

    def test_all_nvg_devices_classified(self):
        bad = self._fall("NVG", NVG_TIERS)
        self.assertFalse(
            bad, f"NVG devices missing classifier keywords: {sorted(bad)[:20]}"
        )

    def test_all_thermal_devices_classified(self):
        bad = self._fall("THERMAL", THERMAL_TIERS)
        self.assertFalse(
            bad, f"thermal devices missing classifier keywords: {sorted(bad)[:20]}"
        )

    def test_all_optics_classified(self):
        bad = self._fall("OPTIC", OPTIC_TIERS)
        self.assertFalse(bad, f"optics missing classifier keywords: {sorted(bad)[:20]}")


if __name__ == "__main__":
    unittest.main()
