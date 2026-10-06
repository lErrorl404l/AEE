#!/usr/bin/env python3
"""GNSS tracker kernel tests (MGRS wave 3, tasks 10 to 12).

Runs the REAL pure kernels through tools/tests/sqf_lite.py:
  addons/core/functions/geo/fnc_gnssErrorEllipse.sqf   (task 10)
  addons/core/functions/geo/fnc_gnssFixState.sqf       (task 11)
  addons/core/functions/geo/fnc_datalinkState.sqf      (task 12)

The kernels read no world, no config, no player and no engine state.  The
sourced constants come from the GPS Standard Positioning Service Performance
Standard, 5th edition, April 2020 (gps.gov): UERE 3.6 m RMS, 8 m horizontal
and 13 m vertical at 95 percent, and the R95 factor 2.0.  Every other shape
is marked UNSOURCED in the kernel header and listed for the per-constant
register (task 18).
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GEO = ROOT / "addons" / "core" / "functions" / "geo"
ELLIPSE = GEO / "fnc_gnssErrorEllipse.sqf"
FIXSTATE = GEO / "fnc_gnssFixState.sqf"
DATALINK = GEO / "fnc_datalinkState.sqf"
PREP = ROOT / "addons" / "core" / "XEH_PREP.hpp"


def ellipse(dop, uere, atmos=0.0, canopy=0.0, urban=0.0, jamming=0.0, rx=1.0):
    return run_sqf(ELLIPSE, [dop, uere, atmos, canopy, urban, jamming, rx])


def fix_state(dt, signal, jamming, prev):
    return run_sqf(FIXSTATE, [dt, signal, jamming, prev])


def datalink(distance, terrain=0.0, urban=0.0, jammer=0.0, bandwidth=100.0):
    return run_sqf(DATALINK, [distance, terrain, urban, jammer, bandwidth])


class TestGnssErrorEllipse(unittest.TestCase):
    def test_clean_sky_no_jammer_is_a_small_ellipse(self):
        # Given a clean sky and no jammer, the 1-sigma horizontal error is
        # the DOP times the sourced 3.6 m UERE.
        east, north, _up, major, minor, _orient, cep, r95 = ellipse(1.0, 3.6)
        self.assertAlmostEqual(east, 3.6, places=6)
        self.assertAlmostEqual(north, 3.6, places=6)
        self.assertLess(major, 5.0)
        self.assertLess(minor, 5.0)
        self.assertLess(cep, 5.0)
        self.assertLess(r95, 11.0)

    def test_high_dop_and_jammer_is_a_large_ellipse(self):
        # A high DOP and full jamming inflate the ellipse by an order of
        # magnitude against the clean case.
        _e, _n, _u, clean_major, _m, _o, _c, clean_r95 = ellipse(1.0, 3.6)
        _e, _n, _u, jam_major, _m, _o, _c, jam_r95 = ellipse(8.0, 3.6, jamming=1.0)
        self.assertGreater(jam_major, 100.0)
        self.assertGreater(jam_r95, clean_r95 * 10.0)

    def test_urban_stretches_the_east_axis_and_swings_orientation(self):
        clean = ellipse(1.0, 3.6)
        urban = ellipse(1.0, 3.6, urban=1.0)
        self.assertEqual(clean[5], 0)
        self.assertEqual(urban[5], 90)
        self.assertGreater(urban[0], urban[1])

    def test_vertical_is_the_sourced_13_over_8_ratio(self):
        east, _n, up, _a, _b, _o, _c, _r = ellipse(1.0, 3.6)
        self.assertAlmostEqual(up / east, 13 / 8, places=6)

    def test_r95_is_the_sourced_2drms_factor(self):
        east, north, _u, _a, _b, _o, _c, r95 = ellipse(1.0, 3.6)
        drms = math.hypot(east, north)
        self.assertAlmostEqual(r95, 2.0 * drms, places=6)

    def test_receiver_quality_and_canopy_raise_the_error(self):
        clean = ellipse(1.0, 3.6)
        poor_rx = ellipse(1.0, 3.6, rx=0.5)
        canopy = ellipse(1.0, 3.6, canopy=1.0)
        self.assertGreater(poor_rx[0], clean[0])
        self.assertGreater(canopy[0], clean[0])


class TestGnssErrorEllipseSourceContract(unittest.TestCase):
    def test_preps_registration(self):
        prep = PREP.read_text(encoding="utf-8")
        self.assertIn("PREPS(geo,gnssErrorEllipse)", prep)

    def test_header_carries_the_sourced_constants(self):
        src = ELLIPSE.read_text(encoding="utf-8")
        self.assertIn("3.6", src)
        self.assertIn("2.0", src)
        self.assertIn("13 / 8", src)
        self.assertIn("Standard Positioning Service", src)

    def test_unsourced_shapes_are_marked(self):
        src = ELLIPSE.read_text(encoding="utf-8")
        self.assertIn("UNSOURCED", src)
        self.assertIn("per-constant register", src)


class TestGnssFixState(unittest.TestCase):
    def test_fresh_start_reports_a_good_fix(self):
        quality, time_since, reacq, lag, stutter = fix_state(1.0, 1.0, 0.0, [])
        self.assertEqual(quality, "ok")
        self.assertEqual(time_since, 0)
        self.assertEqual(reacq, 1)
        self.assertEqual(lag, 0)
        self.assertEqual(stutter, 0)

    def test_signal_loss_clears_the_fix_and_ages_it(self):
        quality, time_since, reacq, lag, _s = fix_state(1.0, 0.0, 0.0, [0, 1])
        self.assertEqual(quality, "none")
        self.assertEqual(reacq, 0)
        self.assertEqual(time_since, 1.0)
        self.assertGreater(lag, 0)

    def test_return_proves_a_reacquisition_ramp_and_a_lagged_offset(self):
        # Given a signal loss, when the signal returns, then the
        # re-acquisition progress climbs over several steps and the lagged
        # offset falls back to zero.  A lost fix leaves reacq at 0.
        lost = fix_state(1.0, 0.0, 0.0, [0, 1])
        self.assertEqual(lost[2], 0)

        prev = [lost[1], lost[2]]
        progress = []
        lags = []
        qualities = []
        for _ in range(4):
            out = fix_state(1.0, 1.0, 0.0, prev)
            qualities.append(out[0])
            progress.append(out[2])
            lags.append(out[3])
            prev = [out[1], out[2]]

        # The first return step is degraded, not instantly re-acquired.
        self.assertEqual(qualities[0], "degraded")
        self.assertLess(progress[0], 1)
        self.assertEqual(qualities[-1], "ok")
        self.assertEqual(progress[-1], 1)

        for a, b in zip(progress, progress[1:]):
            self.assertLess(a, b)
        for a, b in zip(lags, lags[1:]):
            self.assertGreater(a, b)
        self.assertGreater(lags[0], 0)
        self.assertEqual(lags[-1], 0)

    def test_jamming_removes_a_fix(self):
        quality, _t, reacq, _lag, _s = fix_state(1.0, 1.0, 1.0, [0, 1])
        self.assertEqual(quality, "none")
        self.assertEqual(reacq, 0)


class TestGnssFixStateSourceContract(unittest.TestCase):
    def test_preps_registration(self):
        prep = PREP.read_text(encoding="utf-8")
        self.assertIn("PREPS(geo,gnssFixState)", prep)

    def test_header_records_the_continuity_source_and_unsourced_shapes(self):
        src = FIXSTATE.read_text(encoding="utf-8")
        self.assertIn("Standard Positioning Service", src)
        self.assertIn("Continuity", src)
        self.assertIn("UNSOURCED", src)
        self.assertIn("per-constant register", src)


class TestDatalinkState(unittest.TestCase):
    def test_near_clear_link_is_received(self):
        state, interval, track_age, error = datalink(1000.0)
        self.assertEqual(state, "received")
        self.assertGreater(interval, 0)
        self.assertLess(track_age, 1.0)
        self.assertLess(error, 5.0)
        self.assertIn(state, ("received", "lost"))

    def test_far_blocked_link_is_lost_and_ages(self):
        near = datalink(1000.0)
        far = datalink(12000.0, terrain=0.8, urban=0.5, jammer=0.0)
        self.assertEqual(near[0], "received")
        self.assertEqual(far[0], "lost")
        self.assertEqual(far[1], 0)
        self.assertGreater(far[2], near[2])
        self.assertGreater(far[3], near[3])

    def test_track_age_rises_with_distance(self):
        ages = [datalink(d)[2] for d in (1000.0, 4000.0, 8000.0, 16000.0)]
        for a, b in zip(ages, ages[1:]):
            self.assertLessEqual(a, b)
        self.assertLess(ages[0], ages[-1])

    def test_bandwidth_shortens_the_update_interval(self):
        slow = datalink(2000.0, bandwidth=50.0)
        fast = datalink(2000.0, bandwidth=400.0)
        self.assertEqual(slow[0], "received")
        self.assertEqual(fast[0], "received")
        self.assertGreater(slow[1], fast[1])


class TestDatalinkStateSourceContract(unittest.TestCase):
    def test_preps_registration(self):
        prep = PREP.read_text(encoding="utf-8")
        self.assertIn("PREPS(geo,datalinkState)", prep)

    def test_header_records_the_friis_shape_and_the_unsourced_shapes(self):
        src = DATALINK.read_text(encoding="utf-8")
        self.assertIn("Friis", src)
        self.assertIn("fnc_calculateRadioPropagation", src)
        self.assertIn("UNSOURCED", src)
        self.assertIn("per-constant register", src)

    def test_kernel_has_no_runtime_radio_dependency(self):
        # A pure kernel must not call the radio module or read mission state.
        src = DATALINK.read_text(encoding="utf-8")
        self.assertNotIn("call FUNC(", src)
        self.assertNotIn("call EFUNC(", src)
        self.assertNotIn("missionNamespace", src)


if __name__ == "__main__":
    unittest.main()
