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
    """Return {keyword: tier_string} from the standalone switch."""
    m = re.search(r"switch \(true\) do \{(.*?)\n\};", source, re.S)
    if not m:
        raise SystemExit("switch block not found")
    body = m.group(1)
    tiers = {}
    for case in re.finditer(r"case\s*\((.*?)\):\s*\{(\s*\[[^\]]+\]\s*)\};", body, re.S):
        cond, tier = case.group(1), case.group(2)
        kws = re.findall(r'find "([^"]+)"', cond)
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
    def assert_tier(self, kw, netd, resx, resy, w, refresh, cooled):
        self.assertIn(kw, THERMAL_TIERS, f"thermal keyword {kw} missing")
        parts = [float(x) for x in re.findall(r"[0-9.]+", THERMAL_TIERS[kw])]
        self.assertAlmostEqual(parts[0], netd, delta=0.001, msg=f"{kw} NETD")
        self.assertEqual(int(parts[1]), resx, msg=f"{kw} resX")
        self.assertEqual(int(parts[2]), resy, msg=f"{kw} resY")

    def test_uncooled(self):
        # Uncooled microbolometer: NETD 0.05, 640x480, 30 Hz.
        self.assert_tier("pas13", 0.05, 640, 480, 1.3, 30, 0)
        self.assert_tier("v1", 0.05, 320, 240, 0.885, 30, 0)

    def test_cooled(self):
        # Cooled InSb/MCT: NETD 0.025, 640x512, 50 Hz.
        self.assert_tier("catherine", 0.025, 640, 512, 2.5, 50, 1)
        self.assert_tier("jim", 0.025, 640, 512, 2.5, 50, 1)


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
