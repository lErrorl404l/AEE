#!/usr/bin/env python3
"""Reference checks for the ship-motion model (issue #33).

Executes the real kernel addons/maritime/functions/fnc_shipMotionKernel.sqf
through sqf_lite, so the checks cannot drift from the shipped code, and
checks the driver's engine contract.

Run: python3 -m unittest tools/tests/test_ship_motion.py
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

KERNEL = (
    Path(__file__).resolve().parents[2]
    / "addons"
    / "maritime"
    / "functions"
    / "fnc_shipMotionKernel.sqf"
)
DRIVER = KERNEL.parent / "fnc_calculateShipMotion.sqf"
PREP = KERNEL.parent.parent / "XEH_PREP.hpp"

# Realistic vessels: (beam m, length m, mass kg).
PATROL = (4.0, 15.0, 40000.0)
FRIGATE = (15.3, 60.0, 1000000.0)


def peak_period(hs):
    """Pierson-Moskowitz peak period from the significant wave height."""
    return 0.730 * math.sqrt(hs / 0.0246)


def motion(hs, rel_deg, vessel, u=3.0, gm=1.5, zeta=0.10):
    return run_sqf(
        KERNEL,
        [hs, peak_period(hs), u, rel_deg, vessel[0], vessel[1], vessel[2], gm, zeta],
    )


class TestKernelBehaviour(unittest.TestCase):
    def test_zero_wave_height_is_still(self):
        self.assertEqual(motion(0.0, 90.0, PATROL), [0, 0, 0])

    def test_calm_sea_is_small(self):
        # SS1 (Hs ~ 0.05 m): pitch and roll under 2 degrees (issue #33).
        for vessel in (PATROL, FRIGATE):
            pitch, roll, _ = motion(0.05, 90.0, vessel)
            self.assertLess(roll, 2.0)
            self.assertLess(abs(pitch), 2.0)

    def test_beam_sea_rolls_more_than_it_pitches(self):
        pitch, roll, _ = motion(1.2, 90.0, PATROL)
        self.assertGreater(roll, pitch)

    def test_head_sea_pitches_more_than_it_rolls(self):
        pitch, roll, _ = motion(1.2, 180.0, PATROL)
        self.assertGreater(pitch, roll)
        self.assertAlmostEqual(roll, 0.0, places=6)

    def test_roll_grows_with_sea_state(self):
        _, calm, _ = motion(0.05, 90.0, FRIGATE)
        _, heavy, _ = motion(3.54, 90.0, FRIGATE)
        self.assertGreater(heavy, calm)

    def test_heave_grows_with_wave_height(self):
        _, _, calm = motion(0.05, 90.0, FRIGATE)
        _, _, heavy = motion(3.54, 90.0, FRIGATE)
        self.assertGreater(heavy, calm)
        self.assertGreater(heavy, 0.0)

    def test_roll_is_non_negative(self):
        for hs in (0.05, 1.2, 3.54):
            _, roll, _ = motion(hs, 90.0, FRIGATE)
            self.assertGreaterEqual(roll, 0.0)


class TestSourceContract(unittest.TestCase):
    def test_kernel_has_no_engine_write(self):
        text = KERNEL.read_text(encoding="utf-8")
        for token in ("setVariable", "setVelocity", "setPos", "diag_log"):
            self.assertNotIn(token, text)

    def test_driver_is_client_only(self):
        text = DRIVER.read_text(encoding="utf-8")
        self.assertIn("if (!hasInterface) exitWith", text)

    def test_kernel_is_prepped(self):
        text = PREP.read_text(encoding="utf-8")
        self.assertIn("PREP(shipMotionKernel)", text)
        self.assertIn("PREP(calculateShipMotion)", text)


if __name__ == "__main__":
    unittest.main()
