#!/usr/bin/env python3
"""Device library research verification (issue #215).

Locks the researched NVG/thermal/optic device values from
sensor-device-library.md to their classifier tiers in the three device
functions.  A tier value that drifts from research fails the gate.

Run: python3 -m unittest tools/tests/test_device_values.py
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
NVG = (REPO / "addons/nightvision/functions/fnc_getNvgDeviceProperties.sqf").read_text(
    encoding="utf-8"
)
THERMAL = (
    REPO / "addons/thermal/functions/sensor/fnc_getThermalDeviceProperties.sqf"
).read_text(encoding="utf-8")
OPTIC = (REPO / "addons/optics/functions/sensor/fnc_getOpticProperties.sqf").read_text(
    encoding="utf-8"
)


def extract_tiers(source):
    """Return {keyword: tier_string} from the standalone switch.

    The PAS-13 variant cases gate their two-character variant token
    ("v1"/"v2"/"v3") on the family flag `_isPas`, so the mirror restores
    the family keywords for any condition that uses the flag.
    """
    m = re.search(r"switch \(true\) do \{(.*?)\n\};", source, re.S)
    if not m:
        raise SystemExit("switch block not found")
    body = m.group(1)
    tiers = {}
    for case in re.finditer(r"case\s*\((.*?)\):\s*\{(\s*\[[^\]]+\]\s*)\};", body, re.S):
        cond, tier = case.group(1), case.group(2)
        kws = re.findall(r'find "([^"]+)"', cond)
        if "_isPas" in cond:
            kws = ["pas-13", "pas13"] + kws
        tier = re.sub(r"\s+", " ", tier).strip()
        for kw in kws:
            tiers[kw] = tier
    return tiers


NVG_TIERS = extract_tiers(NVG)
THERMAL_TIERS = extract_tiers(THERMAL)
OPTIC_TIERS = extract_tiers(OPTIC)


class TestNvgDeviceValues(unittest.TestCase):
    def assert_tier(self, kw, gen, sens, res, w, tubes, fov):
        self.assertIn(kw, NVG_TIERS, f"NVG keyword {kw} missing")
        gen_str = re.sub(r"[^A-Z0-9]+", "", NVG_TIERS[kw].split(",")[0])
        self.assertEqual(gen_str, gen, msg=f"{kw} generation")
        nums = NVG_TIERS[kw].split(",", 1)[1]  # strip the generation string
        parts = [float(x) for x in re.findall(r"[0-9.]+", nums)]
        self.assertAlmostEqual(parts[0], sens, delta=1, msg=f"{kw} sensitivity")
        self.assertAlmostEqual(parts[1], res, delta=1, msg=f"{kw} resolution")
        self.assertAlmostEqual(parts[2], w, delta=0.01, msg=f"{kw} weight")
        self.assertEqual(int(parts[3]), tubes, msg=f"{kw} tube count")

    def test_pvs14(self):
        # PVS-14: Gen 3 GaAs, 1100 uA/lm, 64 lp/mm, 355 g, mono, 40 deg.
        self.assert_tier("pvs14", "GEN3", 1100, 64, 0.355, 1, 40)

    def test_gpnvg(self):
        # GPNVG-18: filmless 4x tubes, 2000 uA/lm, 72 lp/mm, 0.79 kg.
        self.assert_tier("gpnvg", "PVS31", 2000, 72, 0.79, 4, 97)

    def test_pvs31(self):
        # PVS-31A: filmless binocular, <0.45 kg.
        self.assert_tier("pvs31", "PVS31", 2000, 72, 0.45, 2, 40)

    def test_pvs7(self):
        # PVS-7: Gen 2 multialkali 550, 28 lp/mm, 0.68 kg.
        self.assert_tier("pvs7", "GEN2", 550, 28, 0.68, 1, 40)

    def test_russian_gen1(self):
        # 1PN63/1PN58: Gen 1 S-25, 250 uA/lm, 30 lp/mm.
        self.assert_tier("1pn63", "GEN1", 250, 30, 1.5, 1, 40)
        self.assert_tier("1pn58", "GEN1", 250, 30, 1.5, 1, 40)


class TestThermalDeviceValues(unittest.TestCase):
    def assert_tier(self, kw, netd, resx, resy, w, refresh, cooled, band):
        self.assertIn(kw, THERMAL_TIERS, f"thermal keyword {kw} missing")
        tier = THERMAL_TIERS[kw]
        parts = [float(x) for x in re.findall(r"[0-9.]+", tier)]
        self.assertEqual(len(parts), 6, f"{kw} tuple must be six numeric fields")
        self.assertAlmostEqual(parts[0], netd, delta=0.001, msg=f"{kw} NETD")
        self.assertEqual(int(parts[1]), resx, msg=f"{kw} resX")
        self.assertEqual(int(parts[2]), resy, msg=f"{kw} resY")
        self.assertAlmostEqual(parts[3], w, delta=0.01, msg=f"{kw} weight")
        self.assertEqual(int(parts[4]), refresh, msg=f"{kw} refreshHz")
        self.assertEqual(int(parts[5]), cooled, msg=f"{kw} cooled")
        # The band is the seventh tuple entry, appended after the six numeric
        # fields.  It is a word, so it cannot be parsed with the number regex.
        band_match = re.search(r'"(\w+)"\s*\]\s*$', tier)
        self.assertIsNotNone(band_match, f"{kw} tuple must end with a band word")
        assert band_match is not None
        self.assertEqual(band_match.group(1), band, msg=f"{kw} band")

    def test_the_band_is_per_device_not_derived_from_cooled(self):
        # The band cannot be derived from the cooled flag: a cooled MCT is
        # LWIR (Catherine-MP LW) and a cooled MWIR device is not (Sophie
        # Ultima).  These two pins make the per-device value explicit.
        self.assert_tier("catherine", 0.025, 1280, 1024, 7.9, 50, 1, "lwir")
        self.assert_tier("ultima", 0.025, 640, 512, 2.5, 50, 1, "mwir")

    def test_cooled_observation_class(self):
        # doc L118-L123, one tuple per device (the old code folded four
        # different cooled devices into a single 640x512 tuple).
        self.assert_tier("catherine", 0.025, 1280, 1024, 7.9, 50, 1, "lwir")
        self.assert_tier("ultima", 0.025, 640, 512, 2.5, 50, 1, "mwir")
        self.assert_tier("recon", 0.025, 640, 480, 1.9, 50, 1, "mwir")
        self.assert_tier("jim", 0.025, 384, 288, 2.8, 50, 1, "mwir")

    def test_pas13_variants(self):
        # doc L113-L115: the three PAS-13E(V) variants differ in
        # resolution and weight; the old code gave V2/V3 one weight.
        self.assert_tier("v1", 0.05, 320, 240, 0.885, 30, 0, "lwir")
        self.assert_tier("v2", 0.05, 640, 480, 1.134, 30, 0, "lwir")
        self.assert_tier("v3", 0.05, 640, 480, 1.497, 30, 0, "lwir")
        # A PAS-13 with no variant token selects the 640x480 MWTS class.
        self.assert_tier("pas13", 0.05, 640, 480, 1.134, 30, 0, "lwir")

    def test_uncooled_families(self):
        self.assert_tier("coti", 0.05, 320, 240, 0.15, 30, 0, "lwir")
        self.assert_tier("envg", 0.04, 640, 480, 1.133, 30, 0, "lwir")
        self.assert_tier("sophie", 0.05, 384, 288, 2.0, 50, 0, "lwir")
        self.assert_tier("shakhin", 0.05, 640, 480, 2.2, 50, 0, "lwir")
        self.assert_tier("mowgli", 0.05, 320, 240, 1.5, 50, 0, "lwir")
        self.assert_tier("thermion", 0.025, 640, 480, 0.9, 50, 0, "lwir")
        self.assert_tier("helion", 0.04, 384, 288, 0.5, 50, 0, "lwir")
        self.assert_tier("scout", 0.05, 640, 512, 0.34, 30, 0, "lwir")

    def test_bare_variant_tokens_are_family_gated(self):
        # The variant tokens must not be free-standing: the source must
        # gate each on the PAS-13 family flag, never match "v1" alone.
        for variant in ("v1", "v2", "v3"):
            self.assertIn(f'_isPas && (_t find "{variant}" >= 0)', THERMAL)


class TestOpticValues(unittest.TestCase):
    def assert_tier(self, kw, mag, obj, fov, w):
        self.assertIn(kw, OPTIC_TIERS, f"optic keyword {kw} missing")
        parts = [float(x) for x in re.findall(r"[0-9.]+", OPTIC_TIERS[kw])]
        self.assertAlmostEqual(parts[0], mag, delta=0.1, msg=f"{kw} magnification")
        self.assertAlmostEqual(parts[1], obj, delta=1, msg=f"{kw} objective")
        self.assertAlmostEqual(parts[2], fov, delta=0.5, msg=f"{kw} FOV")

    def test_acog(self):
        # ACOG TA31: 4x32, 7 deg FOV, 0.42 kg.
        self.assert_tier("acog", 4, 32, 7, 0.42)
        self.assert_tier("rco", 4, 32, 7, 0.42)

    def test_pso(self):
        # PSO-1: 4x24, 6 deg, 0.60 kg.
        self.assert_tier("pso", 4, 24, 6, 0.60)

    def test_sniper(self):
        # S&B PM II / ATACR: 10x class, 56 mm objective, ~1 kg.
        self.assert_tier("atacr", 10, 56, 3, 1.05)
        self.assert_tier("pmii", 10, 56, 3, 1.05)

    def test_reddot(self):
        # Aimpoint T-2 / CompM4: 1x, no objective FOV.
        self.assert_tier("compm", 1, 23, 0, 0.27)
        self.assert_tier("t-2", 1, 23, 0, 0.27)


if __name__ == "__main__":
    unittest.main()
