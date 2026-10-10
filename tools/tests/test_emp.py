#!/usr/bin/env python3
"""Nuclear EMP model (issue #9).

The EMP field, coupling, degradation and recovery kernels are pure, so this
suite EXECUTES the shipped SQF through the shared sqf_lite interpreter
(issue #204) and checks the issue's own test vectors.  The engine-bound glue
(the tick and the two consumers) is held by source assertions: the consumers
must read the state aee_core publishes, so the wiring cannot silently break.

Sources for every value:
  E1/E2 double-exponential waveform: IEC 61000-2-9, adopted by MIL-STD-464C
    A.5.9.1 (the HEMP waveform standard); DOE Waveform Application Guide 2023.
  HEMP coverage r = sqrt(2 R h): Glasstone & Dolan, The Effects of Nuclear
    Weapons, Ch XI (geometric horizon).  R = 6371 km.
  Ground-burst 1/R: the issue's model (E0 = 100 kV/m, R0 = 5 km).
  Coupling E_coupled = E_free * 10^(-dB/20): the issue's model.
  Recovery tau = 1 + 29 * (E_coupled / E_damage): the issue's model.
  Degradation factor 1/(1+r): a labelled MODEL MAPPING (no published curve).

Run: python3 -m unittest tools.tests.test_emp -v
"""

from __future__ import annotations

import math
import unittest
from pathlib import Path

from tools.tests.sqf_lite import run_sqf

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / "addons" / "core" / "functions"
RADIO = REPO / "addons" / "radio" / "functions"
OPTICS = REPO / "addons" / "optics" / "functions"

WAVEFORM = CORE / "fnc_calculateEmpWaveform.sqf"
FIELD = CORE / "fnc_calculateEmpField.sqf"
COUPLING = CORE / "fnc_calculateEmpCoupling.sqf"
DEGRADATION = CORE / "fnc_calculateEmpDegradation.sqf"
RECOVERY = CORE / "fnc_calculateEmpRecovery.sqf"
RECOVERED = CORE / "fnc_calculateEmpRecoveredFactor.sqf"


def _src(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestEmpWaveform(unittest.TestCase):
    """E1 double exponential (IEC 61000-2-9)."""

    def test_zero_at_onset(self):
        # E(0) = E0*k*(exp(0) - exp(0)) = 0.
        self.assertAlmostEqual(run_sqf(WAVEFORM, [0]), 0.0, delta=1e-9)

    def test_negative_time_is_zero(self):
        self.assertEqual(run_sqf(WAVEFORM, [-1e-9]), 0.0)

    def test_rises_to_the_peak_band(self):
        # The E1 pulse peaks near 50 kV/m (the E0 the standard sets).
        peak = max(run_sqf(WAVEFORM, [t * 1e-9]) for t in range(1, 12))
        self.assertGreater(peak, 40000.0)
        self.assertLess(peak, 65000.0)

    def test_e0_scales_the_peak(self):
        # E2 is the same form with E0 = 100 V/m.  The source gives E2's peak
        # but NOT its rate constants, so the kernel takes them as arguments and
        # does not invent them.  This proves the E0 parameter scales the peak.
        e1 = max(run_sqf(WAVEFORM, [t * 1e-9]) for t in range(1, 12))
        e2 = max(run_sqf(WAVEFORM, [t * 1e-9, 100]) for t in range(1, 12))
        self.assertAlmostEqual(e2 / e1, 100 / 50000, delta=1e-6)


class TestEmpField(unittest.TestCase):
    """Free field: HEMP footprint and ground-burst 1/R (issue #9)."""

    def test_hemp_400km_radius_is_2257km(self):
        # r = sqrt(2 * 6371000 * 400000) = 2257 km (the issue's vector).
        inside = run_sqf(FIELD, ["hemp", 2_000_000, 400000, 50000])
        outside = run_sqf(FIELD, ["hemp", 3_000_000, 400000, 50000])
        self.assertEqual(inside, 50000)
        self.assertEqual(outside, 0)

    def test_hemp_100km_radius_is_1129km(self):
        self.assertEqual(run_sqf(FIELD, ["hemp", 1_000_000, 100000, 50000]), 50000)
        self.assertEqual(run_sqf(FIELD, ["hemp", 1_200_000, 100000, 50000]), 0)

    def test_ground_burst_falls_as_one_over_r(self):
        # E = E0 * R0 / R, E0 = 100 kV/m, R0 = 5 km.
        self.assertEqual(run_sqf(FIELD, ["ground", 5000, 0, 100000]), 100000)
        self.assertAlmostEqual(
            run_sqf(FIELD, ["ground", 50000, 0, 100000]), 10000, delta=1
        )
        self.assertAlmostEqual(
            run_sqf(FIELD, ["ground", 250000, 0, 100000]), 2000, delta=1
        )

    def test_ground_burst_is_floored_at_the_reference_range(self):
        # Inside R0 the field does not exceed the peak.
        self.assertEqual(run_sqf(FIELD, ["ground", 0, 0, 100000]), 100000)


class TestEmpCoupling(unittest.TestCase):
    """E_coupled = E_free * 10^(-dB/20) (issue #9)."""

    def test_soft_skin_vehicle_20db(self):
        # 50 kV/m into a 20 dB soft-skin vehicle -> 5 kV/m (the issue's vector).
        self.assertAlmostEqual(run_sqf(COUPLING, [50000, 20]), 5000, delta=1)

    def test_no_hardening_is_the_free_field(self):
        self.assertAlmostEqual(run_sqf(COUPLING, [50000, 0]), 50000, delta=1)

    def test_facility_80db(self):
        # MIL-STD-188-125 / CISA level 4: 80 dB -> 10^(-4) -> 5 V/m.
        self.assertAlmostEqual(run_sqf(COUPLING, [50000, 80]), 5.0, delta=0.01)

    def test_armoured_40db(self):
        self.assertAlmostEqual(run_sqf(COUPLING, [50000, 40]), 500, delta=1)


class TestEmpDegradation(unittest.TestCase):
    """Degradation factor 1/(1+r), r = coupled/damage (a labelled model)."""

    def test_zero_field_is_intact(self):
        self.assertEqual(run_sqf(DEGRADATION, [0, 5000]), 1.0)

    def test_damage_threshold_halves_the_factor(self):
        self.assertAlmostEqual(run_sqf(DEGRADATION, [5000, 5000]), 0.5, delta=1e-9)

    def test_factor_decreases_with_field(self):
        low = run_sqf(DEGRADATION, [1000, 5000])
        high = run_sqf(DEGRADATION, [50000, 5000])
        self.assertGreater(low, high)
        self.assertLess(high, 0.1)


class TestEmpRecovery(unittest.TestCase):
    """tau = 1 + 29*(coupled/damage) (issue #9)."""

    def test_no_field_recovers_in_one_second(self):
        self.assertEqual(run_sqf(RECOVERY, [0, 5000]), 1.0)

    def test_damage_threshold_is_thirty_seconds(self):
        self.assertAlmostEqual(run_sqf(RECOVERY, [5000, 5000]), 30.0, delta=1e-9)

    def test_recovered_factor_starts_at_f0_and_approaches_one(self):
        self.assertAlmostEqual(run_sqf(RECOVERED, [0.5, 0, 30]), 0.5, delta=1e-9)
        self.assertAlmostEqual(run_sqf(RECOVERED, [0.5, 3000, 30]), 1.0, delta=1e-6)

    def test_recovered_factor_is_one_when_intact(self):
        self.assertEqual(run_sqf(RECOVERED, [1.0, 0, 30]), 1.0)


class TestEmpWiring(unittest.TestCase):
    """The consumers read the state aee_core publishes."""

    def test_update_emp_calls_the_kernels(self):
        src = _src(CORE / "fnc_updateEmp.sqf")
        for call in (
            "FUNC(calculateEmpField)",
            "FUNC(calculateEmpCoupling)",
            "FUNC(calculateEmpDegradation)",
            "FUNC(calculateEmpRecovery)",
            "FUNC(calculateEmpRecoveredFactor)",
        ):
            self.assertIn(call, src)

    def test_trigger_emp_sets_the_event(self):
        src = _src(CORE / "fnc_triggerEmp.sqf")
        self.assertIn("QGVAR(empActive), true", src)
        self.assertIn("QGVAR(empStartTime)", src)

    def test_radio_applies_the_factor(self):
        src = _src(RADIO / "fnc_calculateRadioPropagation.sqf")
        self.assertIn("EGVAR(core,empRadioFactor)", src)

    def test_optics_applies_the_factor(self):
        src = _src(OPTICS / "fnc_applyEmpSensorDamage.sqf")
        self.assertIn("EGVAR(core,empOpticsFactor)", src)
        self.assertIn("EGVAR(nightvision,nvgFlashUntil)", src)

    def test_update_environment_runs_the_emp_tick(self):
        src = _src(CORE / "fnc_updateEnvironment.sqf")
        self.assertIn("FUNC(updateEmp)", src)
        self.assertIn("EFUNC(optics,applyEmpSensorDamage)", src)


class TestEmpConstantsMatchSources(unittest.TestCase):
    """Read the constants out of the SQF text; do not trust the comment."""

    def test_earth_radius(self):
        self.assertIn("_earthRadiusM = 6371000", _src(FIELD))

    def test_ground_reference_range(self):
        self.assertIn("_refRangeM = 5000", _src(FIELD))

    def test_coupling_is_field_decibels(self):
        self.assertIn("10 ^ ((0 - _hardeningDB) / 20)", _src(COUPLING))

    def test_recovery_coefficient_is_29(self):
        self.assertIn("1 + 29 * _r", _src(RECOVERY))


if __name__ == "__main__":
    unittest.main()
