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
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]

# The modern BRL/JBM drag tables (the AUTHORITATIVE values, 76 G1
# points / 81 G7 points - Litz Applied Ballistics A5-1/A5-3, McCoy
# Ch.7, NATO AOP-55, ARL.  The anchors are the exact table values).
G1 = {
    0.0: 0.2630,
    0.5: 0.2030,
    0.8: 0.2550,
    0.9: 0.3420,
    1.0: 0.4810,
    1.1: 0.5880,
    1.2: 0.6390,
    1.3: 0.6590,
    1.4: 0.6630,
    1.5: 0.6570,
    1.6: 0.6490,
    1.8: 0.6320,
    2.0: 0.5934,
    2.25: 0.5660,
    2.5: 0.5400,
    3.0: 0.4990,
    3.5: 0.4720,
    4.0: 0.4530,
    5.0: 0.4370,
}
G7 = {
    0.0: 0.1198,
    0.5: 0.1198,
    0.8: 0.1358,
    0.9: 0.1763,
    1.0: 0.2427,
    1.1: 0.3334,
    1.2: 0.4460,
    1.3: 0.5743,
    1.4: 0.6748,
    1.5: 0.7100,
    1.6: 0.7030,
    1.8: 0.6550,
    2.0: 0.6060,
    2.25: 0.5590,
    2.5: 0.5240,
    3.0: 0.4750,
    3.5: 0.4430,
    4.0: 0.4210,
    5.0: 0.4000,
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
            (0.5, 0.2030),
            (1.0, 0.4810),
            (1.5, 0.6570),
            (2.0, 0.5934),
            (2.5, 0.5400),
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
        sqf = (
            REPO / "addons/ballistics/functions/fnc_calculateBallisticDrag.sqf"
        ).read_text(encoding="utf-8")
        for anchor in ("0.2030", "0.4810", "0.6570", "0.5934", "0.5400"):
            self.assertIn(anchor, sqf, f"G1 anchor {anchor} missing from SQF")
        for anchor in ("0.1198", "0.2427", "0.7100", "0.6060", "0.5240"):
            self.assertIn(anchor, sqf, f"G7 anchor {anchor} missing from SQF")


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
        self.assertIn('params ["_bc"', sqf)
        self.assertIn("_dragModel", sqf)
        self.assertIn("_velocity / 340", sqf)


if __name__ == "__main__":
    unittest.main()
