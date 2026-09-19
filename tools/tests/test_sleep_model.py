#!/usr/bin/env python3
"""Reference checks for the Borbely two-process sleep/fatigue model.

Validates the SQF implementation in addons/physiology:
- fnc_calculateSleepPressure.sqf   (Process S + Process C)
- fnc_calculateFatigueFactor.sqf   (Van Dongen + Dawson & Reid anchored)

Ground truth (research-verified):
- Process S: tau_s = 18.2 h (rise), tau_d = 4.2 h (decay, S_min=0
  convention), S_max=1, S_min=0 (Daan, Beersma & Borbely 1984,
  Am J Physiol 246:R161-R178, PMID 6696142)
- Process C: sinusoid, amplitude 0.1-0.15 (Skeldon 2014), peak wake
  drive ~18:00-21:00 (Dijk & Czeisler 1995) — NOT 6:00 (that is the
  sleep-propensity peak, the opposite convention)
- Performance: near-linear PVT lapse accumulation beyond 15.84 h
  cumulative wakefulness (Van Dongen 2003, PMID 12683469)
- BAC equivalence: 17-19 h awake -> 0.05%, 24 h -> 0.10%
  (Dawson & Reid 1997, PMID 9230429)

Run: python3 -m unittest tools/tests/test_sleep_model.py
"""

import math
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PHYSIOLOGY = _REPO_ROOT / "addons" / "physiology" / "functions"

def _read_recursive(base, name):
    """Read an SQF function file, resolving categorised subfolders (issue
    #203).  The function NAME is flat (aee_<mod>_fnc_<name>)."""
    if (base / name).exists():
        return (base / name).read_text(encoding="utf-8")
    for f in base.rglob(name):
        return f.read_text(encoding="utf-8")
    raise FileNotFoundError(f"{name} not found under {base}")


TAU_S = 18.2
TAU_D = 4.2
S_MAX = 1.0
S_MIN = 0.0
AMP = 0.12
PHI = 12.0  # wake-drive peak at ~18:00 (sinusoid peaks at phi + 6)

WAKEFULNESS_THRESHOLD = 15.84
K = 0.05
FLOOR = 0.30
CIRCADIAN_SWING = 0.15


def sleep_pressure(hours_awake, sleep_hours, local_hour, sleeping):
    """Mirror of fnc_calculateSleepPressure.sqf."""
    if sleeping:
        process_s = S_MIN + (S_MAX - S_MIN) * math.exp(-sleep_hours / TAU_D)
    else:
        process_s = S_MAX - (S_MAX - S_MIN) * math.exp(-hours_awake / TAU_S)
    # SQF sin() takes degrees; the mirror converts to radians.
    process_c = AMP * math.sin(math.radians(360 * (local_hour - PHI) / 24))
    return process_s, process_c, process_s - process_c


def fatigue_factor(sleepiness, process_s, process_c, hours_awake):
    """Mirror of fnc_calculateFatigueFactor.sqf."""
    impairment = (hours_awake - WAKEFULNESS_THRESHOLD) * K
    factor = max(FLOOR, min(1.0, 1.0 - impairment))
    circ_mod = (process_c / AMP) * CIRCADIAN_SWING
    return max(FLOOR, min(1.0, factor + circ_mod))


class TestProcessS(unittest.TestCase):
    """Homeostatic sleep pressure (Daan 1984)."""

    def test_zero_wake_zero_pressure(self):
        s, _, _ = sleep_pressure(0, 0, 12, False)
        self.assertAlmostEqual(s, 0.0, places=4)

    def test_wake_pressure_rises(self):
        # After 18.2 h awake, S reaches 63.2% of S_max.
        s, _, _ = sleep_pressure(18.2, 0, 12, False)
        self.assertAlmostEqual(s, 1 - math.exp(-1), places=3)

    def test_wake_saturates(self):
        # Long wakefulness -> S approaches S_max = 1.
        s, _, _ = sleep_pressure(100, 0, 12, False)
        self.assertGreater(s, 0.99)

    def test_sleep_pressure_decays(self):
        # Sleep decays with tau_d: after 4.2 h asleep, S falls to 36.8%.
        s, _, _ = sleep_pressure(24, 4.2, 12, True)
        self.assertAlmostEqual(s, math.exp(-1), places=3)

    def test_sleep_reaches_min(self):
        s, _, _ = sleep_pressure(0, 100, 12, True)
        self.assertLess(s, 0.01)


class TestProcessC(unittest.TestCase):
    """Circadian wake drive (Dijk & Czeisler 1995)."""

    def test_peak_wake_drive_evening(self):
        # Peak wake drive at ~18:00 (the wake maintenance zone), NOT 6:00.
        s, c18, _ = sleep_pressure(24, 0, 18, False)
        s, c06, _ = sleep_pressure(24, 0, 6, False)
        self.assertGreater(c18, c06)

    def test_wake_drive_peaks_at_1800(self):
        # The sinusoid peaks at phi + 6 = 18:00.  C(18) must be the
        # maximum over the day (catches a wrong phi constant).
        c_peak = max(sleep_pressure(24, 0, h, False)[1] for h in range(0, 24))
        s, c18, _ = sleep_pressure(24, 0, 18, False)
        self.assertAlmostEqual(c18, c_peak, places=6)

    def test_full_cycle_value(self):
        # Sanity: C must be a real oscillation in [-A, +A], not a tiny
        # near-zero slope.  Catches the radians-vs-degrees SQF bug.
        s, c06, _ = sleep_pressure(24, 0, 6, False)  # trough: -90 deg
        s, c18, _ = sleep_pressure(24, 0, 18, False)  # peak: +90 deg
        # The oscillation spans the full [-A, A] range.
        self.assertAlmostEqual(c06, -AMP, places=6)
        self.assertAlmostEqual(c18, AMP, places=6)
        self.assertGreater(abs(c18 - c06), 0.2)

    def test_amplitude_within_published_range(self):
        # Published amplitude 0.1-0.15; the mod uses 0.12.
        self.assertGreaterEqual(AMP, 0.1)
        self.assertLessEqual(AMP, 0.15)

    def test_circadian_low_at_early_morning(self):
        # Circadian wake drive is lowest around 04:00-06:00.
        s, c04, _ = sleep_pressure(24, 0, 4, False)
        s, c18, _ = sleep_pressure(24, 0, 18, False)
        self.assertLess(c04, c18)


class TestFatigueFactor(unittest.TestCase):
    """Performance degradation (Van Dongen 2003 + Dawson & Reid 1997)."""

    def test_full_performance_below_threshold(self):
        # <= 15.84 h awake: no impairment (plus a small circadian term).
        f = fatigue_factor(0.5, 0.5, 0.0, 10.0)
        self.assertAlmostEqual(f, 1.0, places=4)

    def test_24h_awake_severe_impairment(self):
        # 24 h awake: 8.16 h past threshold * 0.05 = 0.41 impairment,
        # factor ~0.59.  Matches the 0.10% BAC-equivalent severity.
        f = fatigue_factor(0.9, 0.9, 0.0, 24.0)
        expected = max(FLOOR, min(1.0, 1.0 - (24 - 15.84) * K))
        self.assertAlmostEqual(f, expected, places=4)
        self.assertGreater(f, 0.5)
        self.assertLess(f, 0.65)

    def test_48h_awake_floors(self):
        # 48 h awake: (48-15.84)*0.05 = 1.6 -> floor at 0.30.
        f = fatigue_factor(1.0, 1.0, 0.0, 48.0)
        self.assertAlmostEqual(f, FLOOR, places=4)

    def test_monotonic_degradation(self):
        # Factor falls as wakefulness increases (same circadian phase).
        f0 = fatigue_factor(0.5, 0.5, 0.0, 16.0)
        f1 = fatigue_factor(0.5, 0.5, 0.0, 24.0)
        f2 = fatigue_factor(0.5, 0.5, 0.0, 36.0)
        self.assertGreater(f0, f1)
        self.assertGreater(f1, f2)

    def test_circadian_modulation(self):
        # Same wakefulness, different phases: evening (wake drive) boosts,
        # early morning (circadian low) penalises.
        _, c18, _ = sleep_pressure(24, 0, 18, False)
        _, c04, _ = sleep_pressure(24, 0, 4, False)
        f18 = fatigue_factor(0.9, 0.9, c18, 24.0)
        f04 = fatigue_factor(0.9, 0.9, c04, 24.0)
        self.assertGreater(f18, f04)

    def test_modulation_bounded(self):
        # The circadian swing stays within +/-0.15 of baseline.
        s, c_max, _ = sleep_pressure(24, 0, 18, False)
        baseline = fatigue_factor(0.9, 0.9, 0.0, 24.0)
        boosted = fatigue_factor(0.9, 0.9, c_max, 24.0)
        self.assertLess(abs(boosted - baseline), 0.16)


class TestSQFSyncSleep(unittest.TestCase):
    """SQF source must contain the constants the Python mirrors rely on."""

    def _assert_in_sqf(self, filename, fragments, context):
        text = _read_recursive(_PHYSIOLOGY, filename)
        missing = [f for f in fragments if f not in text]
        self.assertFalse(
            missing,
            f"{filename}: {context} changed/missing in SQF: {missing}. "
            f"Re-sync the Python mirror in test_sleep_model.py.",
        )

    def test_sleep_pressure_constants(self):
        self._assert_in_sqf(
            "fnc_calculateSleepPressure.sqf",
            ["18.2", "4.2", "0.12", "12.0", "360 *", "sin"],
            "Borbely process S/C constants, degrees sin, 18:00 peak",
        )

    def test_fatigue_factor_constants(self):
        self._assert_in_sqf(
            "fnc_calculateFatigueFactor.sqf",
            ["15.84", "0.05", "0.30", "0.15"],
            "Van Dongen threshold, slope, floor, circadian swing",
        )

    def test_fatigue_state_accumulates(self):
        self._assert_in_sqf(
            "fnc_updateFatigueState.sqf",
            ["wakefulnessHours", "sleepHours", "ACE_isUnconscious", "restingSeconds"],
            "sleep state accumulation and detection",
        )


if __name__ == "__main__":
    unittest.main()
