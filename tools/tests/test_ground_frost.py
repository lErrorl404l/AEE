#!/usr/bin/env python3
"""Reference checks for the ground frost detection model.

Validates the SQF implementation in addons/environmental:
- fnc_detectGroundFrost.sqf (Magnus dew point -> terrain frost)

The model mirrors the SQF exactly: same Magnus constants (Alduchov &
Eskridge 1996), same requirement for a solved node-stack surface
temperature (there is no T_air - 2 fallback), same four frost gates,
same intensity clamp.  The drift-lock tests at the bottom fail if the
SQF source drifts from the Python mirror.

Run: python3 -m unittest tools/tests/test_ground_frost.py
"""

import math
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENVIRONMENTAL = _REPO_ROOT / "addons" / "persistence" / "functions"


def _read_env(name):
    """Read an SQF function file, resolving categorised subfolders (issue
    #203).  The function NAME is flat (aee_environmental_fnc_<name>)."""
    if (_ENVIRONMENTAL / name).exists():
        return (_ENVIRONMENTAL / name).read_text(encoding="utf-8")
    for f in _ENVIRONMENTAL.rglob(name):
        return f.read_text(encoding="utf-8")
    raise FileNotFoundError(f"{name} not found under {_ENVIRONMENTAL}")


def dew_point_magnus(temp_c, rh_pct):
    """Mirror of the Magnus dew-point formula (Alduchov & Eskridge 1996).

    gamma = ln(RH/100) + (17.62 * T) / (243.12 + T)
    Td    = (243.12 * gamma) / (17.62 - gamma)
    """
    gamma = math.log(rh_pct / 100) + (17.62 * temp_c) / (243.12 + temp_c)
    return (243.12 * gamma) / (17.62 - gamma)


def dew_point_depression(temp_c, rh_pct):
    """Mirror of the dew-point depression (T - Td)."""
    return temp_c - dew_point_magnus(temp_c, rh_pct)


def ground_frost_intensity(temp_c, rh_pct, wind_speed, overcast, surface_temp):
    """Mirror of fnc_detectGroundFrost.sqf.

    surface_temp is the node-stack surface temperature for the 5 m cell,
    or None when the stack has not solved that cell.  The SQF gives no
    frost verdict for an unsolved cell: the old T_air - 2 C night offset
    is removed (issue #11), because a fixed offset is a cooling law in
    neither direction.

    Frost requires surface <= 0 degC, dew-point depression < 2 degC,
    overcast < 0.3 and wind < 5 m/s.  Intensity is
    (0 - surface) * (1 - depression/5), clamped to 0-1.
    """
    if surface_temp is None:
        return 0.0
    depression = dew_point_depression(temp_c, rh_pct)
    if surface_temp > 0 or depression >= 2 or overcast >= 0.3 or wind_speed >= 5:
        return 0.0
    return max(0.0, min(1.0, (0 - surface_temp) * (1 - depression / 5)))


class TestDewPoint(unittest.TestCase):
    def test_reference_value(self):
        # 20 degC at 50 % RH: dew point ~9.3 degC (standard psychrometric
        # anchor).  The Magnus formula reproduces it to 0.1 degC.
        self.assertAlmostEqual(dew_point_magnus(20, 50), 9.26, places=1)

    def test_saturated_air(self):
        # 100 % RH: dew point equals air temperature.
        self.assertAlmostEqual(dew_point_magnus(10, 100), 10.0, places=4)

    def test_dry_air_lower_dew_point(self):
        # Lower RH at the same temperature gives a lower dew point.
        self.assertLess(dew_point_magnus(20, 30), dew_point_magnus(20, 80))

    def test_depression_positive_when_unsaturated(self):
        self.assertGreater(dew_point_depression(20, 50), 0.0)

    def test_depression_zero_when_saturated(self):
        self.assertAlmostEqual(dew_point_depression(10, 100), 0.0, places=4)


class TestSolvedSurfaceRequired(unittest.TestCase):
    """Frost reads the solved node-stack surface, and refuses without one."""

    def test_no_solved_surface_gives_no_frost(self):
        # The stack has not reached the cell: no verdict.  The removed
        # T_air - 2 offset would have reported frost here.
        self.assertEqual(ground_frost_intensity(-5, 90, 1, 0, None), 0.0)

    def test_solved_cold_surface_gives_frost(self):
        self.assertGreater(ground_frost_intensity(-5, 90, 1, 0, -7.0), 0.0)

    def test_solved_warm_surface_gives_no_frost(self):
        # The surface governs, not the air: air -5 C over a solved 1 C
        # surface is not frost.  The flat offset could not tell them apart.
        self.assertEqual(ground_frost_intensity(-5, 90, 1, 0, 1.0), 0.0)

    def test_cold_solved_surface_under_warm_air_gives_frost(self):
        # The reverse case: air +2 C, solved surface -1 C.
        self.assertGreater(ground_frost_intensity(2, 90, 1, 0, -1.0), 0.0)


class TestGroundFrost(unittest.TestCase):
    def test_frost_present(self):
        # -5 degC, 90 % RH, clear, calm, solved surface -7 degC, depression
        # ~1.4 degC -> intensity saturates at 1.0.
        i = ground_frost_intensity(-5, 90, 1, 0, -7.0)
        self.assertGreater(i, 0.5)
        self.assertLessEqual(i, 1.0)

    def test_no_frost_too_warm(self):
        # +5 degC air, surface +3 degC: above freezing, no frost.
        self.assertEqual(ground_frost_intensity(5, 90, 1, 0, 3.0), 0.0)

    def test_no_frost_cloudy(self):
        # Cloud cover blocks the frost gate even with a cold surface.
        self.assertEqual(ground_frost_intensity(-5, 90, 1, 0.8, -7.0), 0.0)

    def test_no_frost_windy(self):
        # Strong wind mixes the air, no frost.
        self.assertEqual(ground_frost_intensity(-5, 90, 10, 0, -7.0), 0.0)

    def test_edge_case_zero_air_temp(self):
        # 0 degC air, clear and calm, solved surface -2 degC -> frost forms.
        self.assertGreater(ground_frost_intensity(0, 90, 1, 0, -2.0), 0.0)

    def test_edge_case_zero_surface(self):
        # +2 degC air, solved surface exactly 0 degC -> the intensity term
        # (0 - surface) is zero, so no frost.
        self.assertEqual(ground_frost_intensity(2, 90, 1, 0, 0.0), 0.0)

    def test_intensity_clamped(self):
        # Very cold, saturated, clear, calm: raw intensity far above 1.
        self.assertEqual(ground_frost_intensity(-15, 100, 1, 0, -17.0), 1.0)

    def test_dry_air_blocks_frost(self):
        # -5 degC at 80 % RH: dew-point depression ~2.9 degC, above the
        # 2 degC gate, so no frost even though the surface is cold.
        self.assertEqual(ground_frost_intensity(-5, 80, 1, 0, -7.0), 0.0)


class TestSQFSyncGroundFrost(unittest.TestCase):
    """SQF source must contain the constants the Python mirror relies on."""

    def _assert_in_sqf(self, filename, fragments, context):
        text = _read_env(filename)
        missing = [f for f in fragments if f not in text]
        self.assertFalse(
            missing,
            f"{filename}: {context} changed/missing in SQF: {missing}. "
            f"Re-sync the Python mirror in test_ground_frost.py.",
        )

    def test_magnus_constants(self):
        self._assert_in_sqf(
            "fnc_detectGroundFrost.sqf",
            [
                "17.62",
                "243.12",
                "ln (_humidity / 100)",
                "groundFrostIntensity",
                "groundFrostPresent",
            ],
            "Magnus dew-point constants and output variables",
        )

    def test_frost_gates(self):
        self._assert_in_sqf(
            "fnc_detectGroundFrost.sqf",
            [
                "_surfaceTemp <= 0",
                "_depression < 2",
                "_overcast < 0.3",
                "_wind < 5",
                "_stackKey in _surfState",
                "groundSurfaceTemp",
            ],
            "frost gates and the solved-surface route",
        )

    def test_the_flat_offset_is_gone(self):
        # The T_air - 2 C night offset (issue #11) is removed, not kept as a
        # fallback: an unsolved cell now yields no verdict instead.
        text = _read_env("fnc_detectGroundFrost.sqf")
        self.assertNotIn("_temp - 2", text)
        self.assertNotIn("Brunt", text)

    def test_the_caller_passes_the_position(self):
        # A dedicated server has no local unit, so the cell key must come
        # from the caller, which already holds the position.
        text = (
            _REPO_ROOT / "addons/mobility/functions/fnc_updateGroundState.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("[_pos2D] call EFUNC(persistence,detectGroundFrost)", text)
        self.assertIn(
            'params [["_pos2D", [], [[]]]]', _read_env("fnc_detectGroundFrost.sqf")
        )

    def test_intensity_formula(self):
        self._assert_in_sqf(
            "fnc_detectGroundFrost.sqf",
            [
                "(0 - _surfaceTemp) * (1 - _depression / 5)",
                "max 0 min 1",
            ],
            "intensity formula and clamp",
        )


if __name__ == "__main__":
    unittest.main()
