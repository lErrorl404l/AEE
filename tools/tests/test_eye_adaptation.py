#!/usr/bin/env python3
"""Eye adaptation kernels (issue #141).

AEE owns the camera aperture and therefore owns the eye adaptation rate.
The model runs in base-10 log-luminance space.  A fast pupil branch lags a
slow cone and rod pair.  The CIE 191:2010 mesopic photopic fraction blends
the cone pool against the rod pool.

The pure kernels are executed here from their real SQF through
tools/tests/sqf_lite.py.  The engine-touching sampler, driver and wiring are
source-contracted (the wiring classes live in this file and in
test_engine_bridges.py).

Constants are traced to a published source or marked UNSOURCED beside the
value in the SQF header.  The per-constant register is in
.omo/plans/aee-eye-adaptation.md.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EYE = ROOT / "addons" / "optics" / "functions" / "eye"

MESOPIC = EYE / "fnc_eyeMesopicWeight.sqf"
PUPIL_STEADY = EYE / "fnc_eyePupilSteady.sqf"
PUPIL_STEP = EYE / "fnc_eyePupilStep.sqf"


def mesopic_weight(lum):
    """Mirror of fnc_eyeMesopicWeight: CIE 191:2010 photopic fraction."""
    lo, hi = 0.005, 5.0
    if lum <= lo:
        return 0.0
    if lum >= hi:
        return 1.0
    t = (math.log10(lum) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
    return t * t * (3 - 2 * t)


def pupil_steady(lum):
    """Mirror of fnc_eyePupilSteady: de Groot and Gebhard 1952 diameter."""
    b = lum / 3.183
    x = 0.4 * (math.log10(b) + 0.5)
    d = 4.9 - 3.0 * math.tanh(x)
    return max(1.9, min(8.0, d))


def pupil_step(d, d_target, dt, tau_constrict=0.25, tau_dilate=0.475):
    """Mirror of fnc_eyePupilStep: asymmetric first-order lag."""
    tau = tau_constrict if d_target < d else tau_dilate
    return d + (d_target - d) * (1 - math.exp(-dt / tau))


class TestEyeMesopicWeight(unittest.TestCase):
    """fnc_eyeMesopicWeight runs from the real SQF and matches the mirror."""

    def test_scotopic_endpoint_is_zero(self):
        self.assertEqual(run_sqf(MESOPIC, [0.005]), 0)

    def test_photopic_endpoint_is_one(self):
        self.assertEqual(run_sqf(MESOPIC, [5]), 1)

    def test_below_band_is_scotopic(self):
        self.assertEqual(run_sqf(MESOPIC, [0.001]), 0)

    def test_above_band_is_photopic(self):
        self.assertEqual(run_sqf(MESOPIC, [100]), 1)

    def test_monotonic_on_the_band(self):
        sweep = [0.005 * (5 / 0.005) ** (i / 20) for i in range(21)]
        prev = -1.0
        for lum in sweep:
            got = run_sqf(MESOPIC, [lum])
            self.assertGreaterEqual(got, prev)
            self.assertLessEqual(got, 1.0)
            prev = got

    def test_matches_the_mirror_in_the_band(self):
        for lum in [0.01, 0.05, 0.2, 1.0, 2.5]:
            self.assertAlmostEqual(
                run_sqf(MESOPIC, [lum]), mesopic_weight(lum), places=6
            )


class TestEyePupilSteady(unittest.TestCase):
    """fnc_eyePupilSteady runs from the real SQF and matches the mirror."""

    def test_bright_scene_constricts(self):
        self.assertLess(run_sqf(PUPIL_STEADY, [10000]), 2.5)

    def test_dark_scene_dilates(self):
        self.assertGreater(run_sqf(PUPIL_STEADY, [0.001]), 7.0)

    def test_monotonic_decreasing_in_lum(self):
        prev = None
        for lum in [1e-4, 1e-2, 1e-1, 1, 10, 1000, 1e5]:
            got = run_sqf(PUPIL_STEADY, [lum])
            if prev is not None:
                self.assertLessEqual(got, prev)
            prev = got

    def test_stays_inside_the_clamps(self):
        for lum in [1e-9, 1e-3, 1, 1e3, 1e9]:
            got = run_sqf(PUPIL_STEADY, [lum])
            self.assertGreaterEqual(got, 1.9)
            self.assertLessEqual(got, 8.0)

    def test_matches_the_mirror(self):
        for lum in [0.001, 0.1, 3.183, 100, 10000]:
            self.assertAlmostEqual(
                run_sqf(PUPIL_STEADY, [lum]), pupil_steady(lum), places=6
            )


class TestEyePupilStep(unittest.TestCase):
    """fnc_eyePupilStep runs from the real SQF and matches the mirror."""

    def test_zero_step_does_not_move(self):
        self.assertAlmostEqual(
            run_sqf(PUPIL_STEP, [4.0, 6.0, 0.0, 0.25, 0.475]), 4.0, places=9
        )

    def test_large_step_reaches_target(self):
        got = run_sqf(PUPIL_STEP, [4.0, 6.0, 100.0, 0.25, 0.475])
        self.assertAlmostEqual(got, 6.0, places=6)

    def test_constriction_is_faster_than_redilation(self):
        # Equal 3 mm steps over the same dt: the constriction moves further.
        constricted = run_sqf(PUPIL_STEP, [6.0, 3.0, 0.2, 0.25, 0.475])
        dilated = run_sqf(PUPIL_STEP, [3.0, 6.0, 0.2, 0.25, 0.475])
        moved_constrict = 6.0 - constricted
        moved_dilate = dilated - 3.0
        self.assertGreater(moved_constrict, moved_dilate)

    def test_matches_the_mirror(self):
        for d, target, dt in [(5.0, 2.0, 0.1), (2.0, 7.0, 0.4), (4.0, 4.5, 0.2)]:
            self.assertAlmostEqual(
                run_sqf(PUPIL_STEP, [d, target, dt, 0.25, 0.475]),
                pupil_step(d, target, dt),
                places=6,
            )


if __name__ == "__main__":
    unittest.main()
