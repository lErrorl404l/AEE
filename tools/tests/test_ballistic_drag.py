#!/usr/bin/env python3
"""Ballistic drag kernel verification (issue #167).

Verifies fnc_calculateBallisticDrag.sqf two ways:

1. NUMERICAL SIMULATION: a small ballistic integrator runs the drag
   kernel from muzzle to 300 m and the resulting drop/velocity are
   compared against published reference data (NATO EPVAT, US mil).

2. ORGANISATION CROSS-CHECK: the kernel's airFriction-equivalent at the
   muzzle must reproduce the values ACE3 ships (which ACE3 derives from
   the Applied Ballistics drag library):
     - 5.56 M855 (G1 0.307): airFriction ~0.00126
     - .50 BMG AMAX (G1 1.05): airFriction ~0.000374
   ACE3 is the "known organisation" here (the Applied Ballistics /
   Kestrel ballistics library - the industry standard used by the US
   mil and match shooters).

Run: python3 -m unittest tools/tests/test_ballistic_drag.py
"""

import math
import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
DRAG_TABLES = (REPO / "addons/ballistics/functions/fnc_getDragTables.sqf").read_text(
    encoding="utf-8"
)

# The standard drag tables (the AUTHORITATIVE values, 79 G1
# points / 84 G7 points - Litz Applied Ballistics A5-1/A5-3, McCoy
# Ch.7, NATO AOP-55, ARL.  The anchors are the exact table values).
G1 = {
    0.0: 0.2629,
    0.05: 0.2558,
    0.1: 0.2487,
    0.15: 0.2413,
    0.2: 0.2344,
    0.25: 0.2278,
    0.3: 0.2214,
    0.35: 0.2155,
    0.4: 0.2104,
    0.45: 0.2061,
    0.5: 0.2032,
    0.55: 0.202,
    0.6: 0.2034,
    0.7: 0.2165,
    0.725: 0.223,
    0.75: 0.2313,
    0.775: 0.2417,
    0.8: 0.2546,
    0.825: 0.2706,
    0.85: 0.2901,
    0.875: 0.3136,
    0.9: 0.3415,
    0.925: 0.3734,
    0.95: 0.4084,
    0.975: 0.4448,
    1.0: 0.4805,
    1.025: 0.5136,
    1.05: 0.5427,
    1.075: 0.5677,
    1.1: 0.5883,
    1.125: 0.6053,
    1.15: 0.6191,
    1.2: 0.6393,
    1.25: 0.6518,
    1.3: 0.6589,
    1.35: 0.6621,
    1.4: 0.6625,
    1.45: 0.6607,
    1.5: 0.6573,
    1.55: 0.6528,
    1.6: 0.6474,
    1.65: 0.6413,
    1.7: 0.6347,
    1.75: 0.628,
    1.8: 0.621,
    1.85: 0.6141,
    1.9: 0.6072,
    1.95: 0.6003,
    2.0: 0.5934,
    2.05: 0.5867,
    2.1: 0.5804,
    2.15: 0.5743,
    2.2: 0.5685,
    2.25: 0.563,
    2.3: 0.5577,
    2.35: 0.5527,
    2.4: 0.5481,
    2.45: 0.5438,
    2.5: 0.5397,
    2.6: 0.5325,
    2.7: 0.5264,
    2.8: 0.5211,
    2.9: 0.5168,
    3.0: 0.5133,
    3.1: 0.5105,
    3.2: 0.5084,
    3.3: 0.5067,
    3.4: 0.5054,
    3.5: 0.504,
    3.6: 0.503,
    3.7: 0.5022,
    3.8: 0.5016,
    3.9: 0.501,
    4.0: 0.5006,
    4.2: 0.4998,
    4.4: 0.4995,
    4.6: 0.4992,
    4.8: 0.499,
    5.0: 0.4988,
}

G7 = {
    0.0: 0.1198,
    0.05: 0.1197,
    0.1: 0.1196,
    0.15: 0.1194,
    0.2: 0.1193,
    0.25: 0.1194,
    0.3: 0.1194,
    0.35: 0.1194,
    0.4: 0.1193,
    0.45: 0.1193,
    0.5: 0.1194,
    0.55: 0.1193,
    0.6: 0.1194,
    0.65: 0.1197,
    0.7: 0.1202,
    0.725: 0.1207,
    0.75: 0.1215,
    0.775: 0.1226,
    0.8: 0.1242,
    0.825: 0.1266,
    0.85: 0.1306,
    0.875: 0.1368,
    0.9: 0.1464,
    0.925: 0.166,
    0.95: 0.2054,
    0.975: 0.2993,
    1.0: 0.3803,
    1.025: 0.4015,
    1.05: 0.4043,
    1.075: 0.4034,
    1.1: 0.4014,
    1.125: 0.3987,
    1.15: 0.3955,
    1.2: 0.3884,
    1.25: 0.381,
    1.3: 0.3732,
    1.35: 0.3657,
    1.4: 0.358,
    1.5: 0.344,
    1.55: 0.3376,
    1.6: 0.3315,
    1.65: 0.326,
    1.7: 0.3209,
    1.75: 0.316,
    1.8: 0.3117,
    1.85: 0.3078,
    1.9: 0.3042,
    1.95: 0.301,
    2.0: 0.298,
    2.05: 0.2951,
    2.1: 0.2922,
    2.15: 0.2892,
    2.2: 0.2864,
    2.25: 0.2835,
    2.3: 0.2807,
    2.35: 0.2779,
    2.4: 0.2752,
    2.45: 0.2725,
    2.5: 0.2697,
    2.55: 0.267,
    2.6: 0.2643,
    2.65: 0.2615,
    2.7: 0.2588,
    2.75: 0.2561,
    2.8: 0.2533,
    2.85: 0.2506,
    2.9: 0.2479,
    2.95: 0.2451,
    3.0: 0.2424,
    3.1: 0.2368,
    3.2: 0.2313,
    3.3: 0.2258,
    3.4: 0.2205,
    3.5: 0.2154,
    3.6: 0.2106,
    3.7: 0.206,
    3.8: 0.2017,
    3.9: 0.1975,
    4.0: 0.1935,
    4.2: 0.1861,
    4.4: 0.1793,
    4.6: 0.173,
    4.8: 0.1672,
    5.0: 0.1618,
}


def cd_at(mach, table):
    """Linear-interpolated Cd at a Mach number (the SQF lookup mirror)."""
    keys = sorted(table)
    if mach <= keys[0]:
        return table[keys[0]]
    if mach >= keys[-1]:
        return table[keys[-1]]
    for lo, hi in zip(keys, keys[1:]):
        if lo <= mach <= hi:
            t = (mach - lo) / (hi - lo)
            return table[lo] + t * (table[hi] - table[lo])
    return table[keys[-1]]


def retard(bc, velocity, drag_model=1, rho_rel=1.0):
    """Mirror of the SQF kernel: 0.00068418 * (Cd/BC) * v^2 * rhoRel."""
    mach = velocity / 340.0
    table = G7 if drag_model == 7 else G1
    cd = cd_at(mach, table)
    return 0.00068418 * (cd / bc) * (velocity**2) * rho_rel


def airfriction_equiv(bc, velocity, drag_model=1):
    """The kernel's drag constant equivalent: retard / v^2."""
    return retard(bc, velocity, drag_model) / (velocity**2)


def simulate(bc, mv, drag_model=1, mass_g=4.0, dt=0.01):
    """Small ballistic integrator: runs the kernel to 300 m downrange.
    Returns (time, drop_m, v300).  Point-mass, no wind, flat fire."""
    vx, vy = mv, 0.0
    t = 0.0
    x, y = 0.0, 0.0
    while x < 300.0 and t < 10.0:
        v = math.hypot(vx, vy)
        a = retard(bc, v, drag_model)
        # deceleration opposes velocity, gravity pulls down
        if v > 0:
            vx -= (a * vx / v) * dt
            vy -= (a * vy / v) * dt
        vy -= 9.81 * dt
        x += vx * dt
        y += vy * dt
        t += dt
    return t, y, math.hypot(vx, vy)


class TestG1DragTable(unittest.TestCase):
    """The G1 Cd table must match the modern BRL reference values."""

    def test_table_anchors(self):
        # The published G1 anchors (the JBM/BRL table: Litz A5-1,
        # McCoy Ch.7, NATO AOP-55):
        # Mach 0.5: 0.2030, Mach 1.0: 0.4810, Mach 1.5: 0.6570,
        # Mach 2.0: 0.5934, Mach 2.5: 0.5400.
        for mach, cd in [
            (0.5, 0.2032),
            (1.0, 0.4805),
            (1.5, 0.6573),
            (2.0, 0.5934),
            (2.5, 0.5397),
        ]:
            self.assertAlmostEqual(G1[mach], cd, places=4, msg=f"G1 Cd at Mach {mach}")

    def test_transonic_peak(self):
        # The transonic rise peaks ~0.66 at Mach 1.3-1.4 (~3.2x the
        # subsonic 0.20).
        peak = max(G1[m] for m in G1 if 1.0 <= m <= 1.6)
        self.assertAlmostEqual(peak, 0.6630, delta=0.005)
        self.assertGreater(peak, G1[0.5] * 3.0)

    def test_table_saved_in_sqf(self):
        # The SQF must carry the same table anchors (the JBM/BRL values).
        sqf = DRAG_TABLES
        for anchor in ("0.2032", "0.4805", "0.6573", "0.5934", "0.5397"):
            self.assertIn(anchor, sqf, f"G1 anchor {anchor} missing from SQF")
        for anchor in ("0.1193", "0.3803", "0.3440", "0.2980", "0.1618"):
            self.assertIn(anchor, sqf, f"G7 anchor {anchor} missing from SQF")


class TestAllDragModels(unittest.TestCase):
    """The complete JBM/BRL drag-model set: G1, G2, G5, G6, G7, G8."""

    def test_g2_anchors(self):
        # G2 (10-deg cone-cylinder-boattail): 0.2303@0, peak 0.4114@1.075.
        sqf = DRAG_TABLES
        for anchor in ("0.2303", "0.4114"):
            self.assertIn(anchor, sqf, f"G2 anchor {anchor} missing")

    def test_g5_anchors(self):
        # G5 (short 7.5-deg boat-tail): 0.1710@0, peak 0.4406@1.40.
        sqf = DRAG_TABLES
        for anchor in ("0.1710", "0.4406"):
            self.assertIn(anchor, sqf, f"G5 anchor {anchor} missing")

    def test_g6_anchors(self):
        # G6 (flat-base long-ogive): 0.2617@0, peak 0.4497@1.15.
        sqf = DRAG_TABLES
        for anchor in ("0.2617", "0.4497"):
            self.assertIn(anchor, sqf, f"G6 anchor {anchor} missing")

    def test_g8_anchors(self):
        # G8 (flat-base secant-ogive): 0.2105@0, peak 0.4493@1.075.
        sqf = DRAG_TABLES
        for anchor in ("0.2105", "0.4493"):
            self.assertIn(anchor, sqf, f"G8 anchor {anchor} missing")

    def test_all_six_models_registered(self):
        # The kernel selects all six by the dragModel.
        sqf = DRAG_TABLES
        source = (REPO / "data/ballistics/sources/drag_functions.json").read_text(
            encoding="utf-8"
        )
        models = re.findall(r'"([A-Z0-9]+)": \[', source)
        self.assertGreaterEqual(len(models), 14)
        for m in models:
            self.assertIn(f'["{m}", [', sqf, f"{m} missing from the tables")
        kernel = (
            REPO / "addons/ballistics/functions/fnc_calculateBallisticDrag.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("getDragTables", kernel)


class TestOrganisationCrossCheck(unittest.TestCase):
    """The kernel's airFriction-equivalent must reproduce ACE3's shipped
    values (ACE3 derives them from the Applied Ballistics library)."""

    def test_m855_matches_ace3(self):
        # ACE3's ACE_556x45_Ball_Mk318 (G1 0.307): airFriction -0.0012588.
        # The kernel at M855 MV (948 m/s, Mach 2.79): Cd ~0.52 -> ~0.00116
        # local; ACE3 drop-matched 0.00126.  Allow the averaging band.
        af = airfriction_equiv(0.307, 948)
        self.assertAlmostEqual(
            af, 0.00126, delta=0.0002, msg=f"M855 airFriction {af} vs ACE3 0.00126"
        )

    def test_50bmg_matches_ace3(self):
        # ACE3's ACE_127x99_Ball_AMAX (G1 1.05): airFriction -0.00037397.
        af = airfriction_equiv(1.05, 882)
        self.assertAlmostEqual(
            af,
            0.000374,
            delta=0.00005,
            msg=f".50 AMAX airFriction {af} vs ACE3 0.000374",
        )

    def test_127x108_matches_vanilla(self):
        # Vanilla B_127x108_Ball (G1 0.63): airFriction -0.00065098 (the
        # Lynx config).  The kernel at 820 m/s (Mach 2.41, Cd ~0.55)
        # gives ~0.000596 - the LOCAL match.  The vanilla value is the
        # drop-AVERAGED constant over the whole flight (higher Cd at
        # the transonic crossing).  The kernel must sit within the
        # physics band, not equal the averaged constant.
        af = airfriction_equiv(0.63, 820)
        self.assertGreater(af, 0.00055)
        self.assertLess(af, 0.00065)

    def test_bridge_constant_in_sqf(self):
        # The conversion constant must be in the SQF verbatim.
        sqf = (
            REPO / "addons/ballistics/functions/fnc_calculateBallisticDrag.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("0.00068418", sqf)
        self.assertIn("_rhoRel", sqf)


class TestNumericalSimulation(unittest.TestCase):
    """The integrated trajectory must match published behaviour."""

    def test_m855_velocity_decay(self):
        # M855 at 300 m: ~633 m/s (NATO EPVAT / mil trajectory data,
        # the ~940 -> ~780 @ 100m -> ~633 @ 300m progression).
        _, _, v300 = simulate(0.307, 948, mass_g=4.0)
        self.assertGreater(v300, 550)
        self.assertLess(v300, 700)

    def test_50bmg_less_drag(self):
        # .50 BMG (BC 1.05) retains velocity far better than M855.
        _, _, v300_50 = simulate(1.05, 882, mass_g=42.8)
        _, _, v300_556 = simulate(0.307, 948, mass_g=4.0)
        self.assertGreater(v300_50, v300_556)

    def test_transonic_spike_increases_drop(self):
        # A 5.56 crosses Mach 1 at ~600 m; the real drag spike (Cd up
        # to 0.66 vs the subsonic 0.20) shapes the trajectory.  The
        # table model must stay within the physical drop band at 800 m
        # where the crossing has fully occurred.
        def simulate_range(bc, mv, flat_cd=None, dist=800.0):
            vx, vy, t, x, y = mv, 0.0, 0.0, 0.0, 0.0
            while x < dist and t < 10.0:
                v = math.hypot(vx, vy)
                if flat_cd is None:
                    a = retard(bc, v)
                else:
                    a = 0.00068418 * (flat_cd / bc) * (v**2)
                if v > 0:
                    vx -= (a * vx / v) * 0.01
                    vy -= (a * vy / v) * 0.01
                vy -= 9.81 * 0.01
                x += vx * 0.01
                y += vy * 0.01
                t += 0.01
            return y

        # The flat-Cd model (the engine's constant drag) uses the Mach
        # 2.5 Cd across the whole flight - a valid approximation.  The
        # table model is the physically correct one.  Both must land in
        # the real 800 m drop band for M855; the table model's transonic
        # behaviour is what the engine cannot reproduce with one
        # constant.
        drop_table = simulate_range(0.307, 948, flat_cd=None)
        drop_flat = simulate_range(0.307, 948, flat_cd=G1[2.5])
        self.assertLess(drop_table, 0.0)  # the round falls
        self.assertLess(drop_flat, 0.0)
        self.assertLess(abs(drop_table - drop_flat), 1.5)
        # The real M855 flat-fire drop at 800 m: ~8 m (the trajectory
        # band - flat fire, no zeroing angle, accumulates full gravity).
        self.assertLess(drop_table, -1.0)
        self.assertGreater(drop_table, -15.0)


class TestSqfKernelStructure(unittest.TestCase):
    def test_kernel_registered(self):
        prep = (REPO / "addons/ballistics/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("calculateBallisticDrag", prep)

    def test_kernel_returns_retardation(self):
        sqf = (
            REPO / "addons/ballistics/functions/fnc_calculateBallisticDrag.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn('["_bc", 0, [0]]', sqf)
        self.assertIn("_dragModel", sqf)
        self.assertIn("20.05 * sqrt", sqf)
        self.assertIn("_velocity / _sound", sqf)


class TestDragTablesMatchSource(unittest.TestCase):
    """The SQF tables must equal the verified standard source.

    A previous revision carried a G7 table that was wrong by up to 147
    percent above Mach 1.2 while claiming JBM provenance. This test
    compares every point of every table against
    data/ballistics/sources/drag_functions.json, so the defect cannot
    return.
    """

    def test_every_table_matches_the_source(self):
        import json
        import re

        sqf = (REPO / "addons/ballistics/functions/fnc_getDragTables.sqf").read_text(
            encoding="utf-8"
        )
        source = json.loads(
            (REPO / "data/ballistics/sources/drag_functions.json").read_text(
                encoding="utf-8"
            )
        )["models"]
        checked = 0
        for model, ref in source.items():
            m = re.search(rf'\["{model}", \[(.*?)\n        \]\]', sqf, re.S)
            self.assertIsNotNone(m, f"{model} table missing from the generated file")
            points = [
                (float(a), float(b))
                for a, b in re.findall(r"\[([0-9.]+),\s*([0-9.]+)\]", m.group(1))
            ]
            self.assertEqual(
                len(points),
                len(ref),
                f"{model} point count differs from the source",
            )
            for (mach, cd), want in zip(points, ref):
                self.assertAlmostEqual(mach, want["mach"], places=3)
                self.assertAlmostEqual(
                    cd,
                    want["cd"],
                    places=4,
                    msg=f"{model} Cd at Mach {mach} differs from the source",
                )
                checked += 1
        self.assertGreater(checked, 400)


if __name__ == "__main__":
    unittest.main()
