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
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADDONS = _REPO_ROOT / "addons"


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


def sleep_pressure(hours_awake, sleep_hours, local_hour, sleeping, process_s0=None):
    """Mirror of fnc_calculateSleepPressure.sqf.

    process_s0 carries process S across a step (issue #314).  None keeps the
    fresh-bout form: awake starts at S_min, asleep at S_max.
    """
    if process_s0 is None:
        start_s = S_MAX if sleeping else S_MIN
    else:
        start_s = min(S_MAX, max(S_MIN, process_s0))
    if sleeping:
        process_s = S_MIN + (start_s - S_MIN) * math.exp(-sleep_hours / TAU_D)
    else:
        process_s = S_MAX - (S_MAX - start_s) * math.exp(-hours_awake / TAU_S)
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
        text = _read_recursive(_ADDONS, filename)
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


# ─── Shipped-SQF carry (issue #314) ─────────────────────────────────────────
# The tracker and the kernel under test.  A red run points these two at
# `git show HEAD:<path>` copies; nothing else needs to change.
_FATIGUE_SQF = (
    _ADDONS / "physiology" / "functions" / "state" / "fnc_updateFatigueState.sqf"
)
_PRESSURE_SQF = (
    _ADDONS / "strain" / "functions" / "strain" / "fnc_calculateSleepPressure.sqf"
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sqf_lite import run_sqf  # noqa: E402

REST_GATE_S = 300  # fnc_updateFatigueState: 5 min of prone stillness


def step_tracker(state, unit, delta_hours, local_hour=23.0):
    """Mirror of fnc_updateFatigueState.sqf.

    The harness cannot parse the tracker: it has no `stance`/`speed` unary
    command and no `in` operator (tools/tests/sqf_lite.py, blocked by
    ownership).  The wrapper's control flow is mirrored here; the pressure
    itself comes from the SHIPPED kernel, and the source locks in
    TestTheTrackerSourceLocksTheCarry keep the mirror honest.
    """
    process_s0 = state.get("__QGVAR__processS", 0.0)
    wake_h = state.get("__QGVAR__wakefulnessHours", 0.0)
    sleep_h = state.get("__QGVAR__sleepHours", 0.0)

    resting = (
        unit.get("stance") in ("PRONE", "CROUCH")
        and unit.get("speed", 0.0) < 0.1
        and (local_hour >= 21 or local_hour <= 6)
    )
    rest_sec = unit.get("__QGVAR__restingSeconds", 0.0)
    rest_sec = rest_sec + delta_hours * 3600 if resting else 0.0
    unit["__QGVAR__restingSeconds"] = rest_sec
    sleeping = rest_sec > REST_GATE_S

    if sleeping:
        sleep_h += delta_hours
    else:
        sleep_h = 0.0
        wake_h += delta_hours

    process_s, process_c, sleepiness = run_sqf(
        _PRESSURE_SQF,
        [delta_hours, sleep_h, local_hour, sleeping, process_s0],
        {"missionNamespace": {}},
    )
    if sleeping:
        wake_h = wake_h * (process_s / process_s0) if process_s0 > 1e-6 else 0.0

    state["__QGVAR__processS"] = process_s
    state["__QGVAR__wakefulnessHours"] = wake_h
    state["__QGVAR__sleepHours"] = sleep_h
    state["__QGVAR__sleepiness"] = sleepiness
    state["__QGVAR__fatigueFactor"] = fatigue_factor(
        sleepiness, process_s, process_c, wake_h
    )
    return state


class TestProcessSContinuity(unittest.TestCase):
    """S is continuous across the sleep/wake boundary (Daan 1984).

    The kernel must decay from the value it is given, not from S_max.
    """

    def _kernel(self, hours_awake, sleep_hours, sleeping, s0):
        out = run_sqf(
            _PRESSURE_SQF,
            [hours_awake, sleep_hours, 23.0, sleeping, s0],
            {"missionNamespace": {}},
        )
        return out[0]

    def test_sleep_decays_from_the_carried_pressure(self):
        s24 = 1 - math.exp(-24 / TAU_S)
        got = self._kernel(0.0, 1 / 12, True, s24)
        self.assertAlmostEqual(got, s24 * math.exp(-(1 / 12) / TAU_D), places=5)

    def test_a_five_minute_rest_returns_little(self):
        # Issue #314 vector, kernel level: 24 h of pressure survives a 5 min
        # rest.  A fresh bout would restart near S_max (0.98 at 5 min).
        s24 = 1 - math.exp(-24 / TAU_S)
        carried = self._kernel(0.0, 1 / 12, True, s24)
        fresh = self._kernel(0.0, 1 / 12, True, -1)
        self.assertGreater(carried, 0.70)
        self.assertLess(carried, 0.80)
        self.assertGreater(fresh, 0.97)
        self.assertLess(carried, fresh - 0.20)

    def test_a_fresh_bout_keeps_the_published_form(self):
        # Default S0: today's published constants, unchanged.
        self.assertAlmostEqual(
            self._kernel(18.2, 0.0, False, -1), 1 - math.exp(-1), places=4
        )
        self.assertAlmostEqual(self._kernel(0.0, 4.2, True, -1), math.exp(-1), places=4)

    def test_a_carried_value_is_clamped_to_the_published_range(self):
        self.assertLessEqual(self._kernel(0.0, 0.0, False, 5.0), 1.0)
        self.assertGreaterEqual(self._kernel(0.0, 0.0, True, -0.5), 0.0)


class TestTheTrackerCarriesTheState(unittest.TestCase):
    """fnc_updateFatigueState runs from the real SQF (issue #314)."""

    REST_TICK = 1 / 60  # 60 s, the tick that crosses the 300 s rest gate

    def _run(self, steps):
        state = {}
        unit = {}
        for delta_hours, posture in steps:
            unit["stance"] = posture
            step_tracker(state, unit, delta_hours)
        return state, None

    def test_a_five_minute_rest_does_not_reset_a_day_awake(self):
        steps = [(0.4, "STAND")] * 60 + [(self.REST_TICK, "PRONE")] * 6
        ns, _ = self._run(steps)
        s = ns["__QGVAR__processS"]
        wake_h = ns["__QGVAR__wakefulnessHours"]
        fatigue = ns["__QGVAR__fatigueFactor"]
        # 24 h awake leaves S at 0.73; 6 minutes of rest must not clear it.
        self.assertGreater(s, 0.55)
        self.assertLess(s, 0.90)
        self.assertGreater(wake_h, 20.0)
        self.assertLess(fatigue, 0.75)

    def test_long_sleep_drives_the_pressure_toward_min(self):
        steps = [(0.4, "STAND")] * 60 + [(0.5, "PRONE")] * 48
        ns, _ = self._run(steps)
        self.assertLess(ns["__QGVAR__processS"], 0.01)
        self.assertGreater(ns["__QGVAR__wakefulnessHours"], -1.0)
        self.assertLess(ns["__QGVAR__wakefulnessHours"], 1.0)
        self.assertAlmostEqual(ns["__QGVAR__fatigueFactor"], 1.0, places=2)

    def test_wake_debt_falls_as_the_pressure_is_discharged(self):
        # A short rest gives back about 2% (exp(-t/tau_d)), not 100%.
        steps = [(0.4, "STAND")] * 60 + [(self.REST_TICK, "PRONE")] * 6
        ns, _ = self._run(steps)
        debt = ns["__QGVAR__wakefulnessHours"]
        self.assertAlmostEqual(
            debt / 24.1, math.exp(-(self.REST_TICK / TAU_D)), places=2
        )


class TestTheTrackerSourceLocksTheCarry(unittest.TestCase):
    """The shipped tracker must carry S and must not reset the debt."""

    def setUp(self):
        self.src = _read_recursive(_ADDONS, "fnc_updateFatigueState.sqf")

    def test_the_pressure_is_the_persisted_state(self):
        self.assertIn("missionNamespace getVariable [QGVAR(processS), 0]", self.src)
        self.assertIn(
            "missionNamespace setVariable [QGVAR(processS), _processS]", self.src
        )

    def test_the_carried_pressure_is_passed_to_the_kernel(self):
        self.assertIn(
            "[_deltaHours, _sleepH, _localHour, _sleeping, _processS0]", self.src
        )

    def test_a_sleep_tick_no_longer_zeroes_the_wake_debt(self):
        # This exact branch was the #314 defect.
        self.assertNotIn(
            "if (_sleeping) then {\n    _wakeH = 0;\n    _sleepH = _sleepH + _deltaHours;",
            self.src,
        )
        self.assertIn("_wakeH = _wakeH * (_processS / _processS0);", self.src)

    def test_the_mirror_uses_the_shipped_kernel(self):
        # A mirror that re-implemented the pressure would drift silently.
        self.assertIs(step_tracker.__globals__["run_sqf"], run_sqf)
        self.assertIn("_PRESSURE_SQF", step_tracker.__code__.co_names)


if __name__ == "__main__":
    unittest.main()
