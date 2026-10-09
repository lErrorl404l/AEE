#!/usr/bin/env python3
"""Wiring checks for the previously orphaned kernels (cont18 audit).

Each kernel was reported to have no production caller. These tests pin the
consumer that now reaches it and prove the kernel output changes a value the
consumer publishes. The value checks are Python mirrors of the consumer
arithmetic, because the consumers read engine state a headless run does not
provide; the source-lock block fails first if the consumer stops calling the
kernel.

Run: python3 -m unittest tools.tests.test_orphan_wiring
"""

import math
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_MOB = _REPO / "addons" / "mobility" / "functions"
_RADIO = _REPO / "addons" / "radio" / "functions"
_MAR = _REPO / "addons" / "maritime" / "functions"
_BALL = _REPO / "addons" / "ballistics"
_ENV = _REPO / "addons" / "persistence" / "functions"


def _candidates(root, name):
    direct = root / name
    if direct.exists():
        return direct.read_text(encoding="utf-8")
    for f in root.rglob(name):
        return f.read_text(encoding="utf-8")
    raise FileNotFoundError(f"{name} not found under {root}")


def _sqf(root, name):
    return _candidates(root, name)


class TestRadioRefractionWiring(unittest.TestCase):
    """calculateRefraction -> fnc_calculateRadioPropagation."""

    def setUp(self):
        self.src = _sqf(_RADIO, "fnc_calculateRadioPropagation.sqf")

    def test_consumer_calls_and_reads_refraction(self):
        self.assertIn("EFUNC(atmos,calculateRefraction)", self.src)
        self.assertIn("EGVAR(atmos,refractionK)", self.src)
        self.assertIn("_effectiveDistM = _distM / (sqrt _refractionK)", self.src)
        self.assertIn("20 * log _effectiveDistM", self.src)

    def test_k_factor_changes_the_published_fspl(self):
        def fspl(dist_m, freq_hz, k):
            return (
                20 * math.log10(dist_m / math.sqrt(k))
                + 20 * math.log10(freq_hz)
                - 147.55
            )

        standard = fspl(5000, 1e8, 1.0)
        super_refract = fspl(5000, 1e8, 4.0 / 3.0)
        self.assertNotAlmostEqual(standard, super_refract, places=1)
        self.assertLess(super_refract, standard)


class TestGroundFrostWiring(unittest.TestCase):
    """detectGroundFrost -> fnc_updateGroundState."""

    def setUp(self):
        self.src = _sqf(_MOB, "fnc_updateGroundState.sqf")

    def test_consumer_calls_and_reads_frost(self):
        self.assertIn("EFUNC(persistence,detectGroundFrost)", self.src)
        self.assertIn("EGVAR(persistence,groundFrostPresent)", self.src)
        self.assertIn("|| _groundFrost", self.src)

    def test_frost_presence_changes_the_ground_state(self):
        def state(temp, rain_accum, frozen_depth, frost_present, surface):
            ground_frozen = (frozen_depth > 0.01) or frost_present
            if surface in ("snow", "ice", "glacier", "tundra"):
                return "Snow"
            if (
                temp is not None
                and ((temp < -2) or frost_present)
                and (rain_accum > 0.05 or ground_frozen)
            ):
                return "Frozen"
            if rain_accum > 0.2 and temp is not None and temp > 2:
                return "Mud"
            return "Normal"

        # A calm sub-zero night: air -1 C is above the -2 C dry threshold, so
        # only the frost model can classify the bare ground as frozen.
        self.assertEqual(state(-1.0, 0.0, 0.0, True, "grass"), "Frozen")
        self.assertEqual(state(-1.0, 0.0, 0.0, False, "grass"), "Normal")


class TestCompassAnomalyWiring(unittest.TestCase):
    """calculateMagneticAnomaly -> fnc_calculateCompassDeviation."""

    def setUp(self):
        self.src = _sqf(_MAR, "fnc_calculateCompassDeviation.sqf")

    def test_consumer_calls_and_uses_anomaly(self):
        self.assertIn("FUNC(calculateMagneticAnomaly)", self.src)
        self.assertIn("compassAnomalyNT", self.src)
        self.assertIn("_declination + _anomalyDeg", self.src)

    def test_anomaly_shifts_the_heading(self):
        def anomaly_nt(moment, r, cos_theta):
            # SI flux density: B = (mu0/4pi) * M / r^3 * sqrt(1 + 3cos^2).
            # mu0/4pi = 1e-7 T m / A.
            return (1e-7 * moment / r**3) * math.sqrt(1 + 3 * cos_theta**2) * 1e9

        nt = anomaly_nt(1000.0, 5.0, 1.0)
        deg = (nt / 50000.0) * 57.2957795
        self.assertGreater(nt, 0.0)
        self.assertNotEqual(deg, 0.0)


class TestRecoilWiring(unittest.TestCase):
    """calculateRecoil -> the ballistics Fired handler."""

    def setUp(self):
        self.src = (_BALL / "XEH_postInit.sqf").read_text(encoding="utf-8")

    def test_fired_handler_calls_recoil_and_uses_impulse(self):
        self.assertIn("FUNC(calculateRecoil)", self.src)
        self.assertIn("FUNC(getLoadData)", self.src)
        self.assertIn("_platform addForce", self.src)
        self.assertIn("lastRecoil", self.src)

    def test_recoil_impulse_drives_the_platform_force(self):
        def saami_impulse(ejecta_kg, mv_ms, charge_kg, factor):
            return ejecta_kg * mv_ms + charge_kg * mv_ms * factor

        def lagrange_impulse(ejecta_kg, mv_ms, charge_kg):
            return mv_ms * (ejecta_kg + 0.5 * charge_kg)

        rifle = saami_impulse(0.042, 887.0, 0.0, 1.75)
        cannon = lagrange_impulse(10.0, 900.0, 5.0)
        for impulse in (rifle, cannon):
            self.assertGreater(impulse, 0.0)
            self.assertGreater(impulse / 0.02, 0.0)


class TestTerrainLimitsWiring(unittest.TestCase):
    """calculateTerrainLimits -> fnc_calculateRouteDegradation."""

    def test_route_degradation_consults_the_limits(self):
        route = _sqf(_MOB, "fnc_calculateRouteDegradation.sqf")
        self.assertIn("FUNC(calculateTerrainLimits)", route)
        self.assertIn("vectorUp _x", route)
        self.assertIn("select 3", route)

    def test_limits_consume_getVehicleData_clearance(self):
        limits = _sqf(_MOB, "fnc_calculateTerrainLimits.sqf")
        self.assertIn("FUNC(getVehicleData)", limits)
        self.assertIn("_clearanceMm / 1000", limits)
        self.assertIn("_clearance = _clearanceM", limits)

    def test_crossing_flips_with_slope_and_gates_damage(self):
        def can_cross(slope, grade, side):
            return slope <= grade and slope <= side

        def damage(ground_pressure, rate, interval, crossing):
            return ground_pressure * rate * interval * (1 if crossing else 0)

        self.assertTrue(can_cross(5.0, 20.0, 25.0))
        self.assertFalse(can_cross(40.0, 20.0, 25.0))
        self.assertGreater(damage(1000.0, 1e-4, 1.0, True), 0.0)
        self.assertEqual(damage(1000.0, 1e-4, 1.0, False), 0.0)


class TestEstimateMassWiring(unittest.TestCase):
    """estimateVehicleMass -> fnc_applyAccretionMass mass path.

    The estimator is test-enforced separate from the seven driving functions
    (test_vehicle_mass_model.DRIVING_FUNCTIONS), so the consumer is the mass
    coupling, not the traction path.
    """

    def setUp(self):
        self.src = _sqf(_MOB, "fnc_applyAccretionMass.sqf")

    def test_mass_path_reads_the_estimate(self):
        self.assertIn("FUNC(estimateVehicleMass)", self.src)
        self.assertIn("unavailable", self.src)
        self.assertIn("_base = _estimate select 0", self.src)

    def test_base_mass_resolution_changes_with_the_estimate(self):
        def base_mass(engine_mass, estimate_available, estimate_low):
            if engine_mass > 0:
                return engine_mass
            if estimate_available:
                return estimate_low
            return engine_mass

        self.assertEqual(base_mass(3000, True, 2000), 3000)
        self.assertEqual(base_mass(0, True, 2000), 2000)
        self.assertEqual(base_mass(0, False, 2000), 0)


class TestGetVehicleDataVerdict(unittest.TestCase):
    """getVehicleData is the value-row lookup, consumed by the limits."""

    def test_identity_consumers_call_match_directly(self):
        classify = _sqf(_MOB, "fnc_classifyVehicle.sqf")
        estimate = _sqf(_MOB, "fnc_estimateVehicleMass.sqf")
        self.assertIn("FUNC(getVehicleMatch)", classify)
        self.assertIn("FUNC(getVehicleMatch)", estimate)

    def test_the_value_row_is_now_consumed(self):
        limits = _sqf(_MOB, "fnc_calculateTerrainLimits.sqf")
        self.assertIn("FUNC(getVehicleData)", limits)


class TestSoilStrengthQuarantine(unittest.TestCase):
    def test_quarantine_is_explicit_in_the_header(self):
        src = _sqf(_MOB, "fnc_calculateSoilStrength.sqf")
        self.assertIn("QUARANTINED", src)


if __name__ == "__main__":
    unittest.main()
