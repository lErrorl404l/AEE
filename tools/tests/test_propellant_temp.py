#!/usr/bin/env python3
"""Reference checks for the propellant-temperature muzzle-velocity model.

Validates the SQF implementation in addons/ballistics:
- fnc_calculatePropellantSensitivity.sqf  (fps/degF coefficient cascade)
- fnc_calculateMuzzleVelocityCorrection.sqf (%/degC normalised to the
  ammo's own initSpeed, 21 degC NATO EPVAT reference)

Ground truth (research-verified):
- Smokeless powders span 0.14-2.0 fps/degF; military ball (WC844-type)
  is ~1.5 fps/degF; central rule of thumb is 1.0 fps/degF
  (reloading literature; Sniper's Hide compilation; PrecisionRifleBlog
  field test; Boulkadid et al. 2016, DOI 10.22211/cejem/67229)
- 1 fps/degF = 0.5486 m/s per degC (0.3048 * 1.8)
- 21 degC reference: NATO AEP-97 / STANAG 4823 EPVAT conditioning

Run: python3 -m unittest tools/tests/test_propellant_temp.py
"""

import math
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BALLISTICS = _REPO_ROOT / "addons" / "ballistics" / "functions"

# fps/degF -> m/s per degC (1 degC = 1.8 degF; 1 fps = 0.3048 m/s)
MPS_PER_DEGC_PER_FPS_DEGF = 0.3048 * 1.8  # 0.5486

# Literature-anchored coefficients (fps/degF)
TEMP_STABLE = 0.3  # Hodgdon Extreme / RL16-class, match powders
SINGLE_BASE = 0.7  # extruded nitrocellulose
CENTRAL = 1.0  # rule of thumb, most smokeless powders
DOUBLE_BASE = 1.2  # NC + NG
MILITARY_BALL = 1.5  # WC844-type ball (5.56/7.62 NATO)

REF_TEMP_C = 21.0


def propellant_sensitivity(ammo):
    """Mirror of fnc_calculatePropellantSensitivity.sqf cascade."""
    table = {
        "B_556x45_Ball": MILITARY_BALL,
        "B_556x45_Ball_Tracer_Red": MILITARY_BALL,
        "B_762x51_Ball": MILITARY_BALL,
        "B_762x51_Ball_Tracer_Green": MILITARY_BALL,
        "B_9x21_Ball": DOUBLE_BASE,
        "B_545x39_Ball": MILITARY_BALL,
        "B_65x39_Caseless": TEMP_STABLE,
        "B_338_NM_Ball": TEMP_STABLE,
        "B_127x108_Ball": MILITARY_BALL,
        "B_127x99_Ball": MILITARY_BALL,
    }
    if ammo in table:
        return table[ammo]
    # Caliber-family fallback
    for frag, coeff in [
        ("556x45", MILITARY_BALL),
        ("762x51", MILITARY_BALL),
        ("545x39", MILITARY_BALL),
        ("127x", MILITARY_BALL),
        ("9x21", DOUBLE_BASE),
        ("9x19", DOUBLE_BASE),
        ("338", TEMP_STABLE),
        ("6.5", TEMP_STABLE),
    ]:
        if frag in ammo:
            return coeff
    return CENTRAL


def muzzle_velocity_correction(ammo, init_speed, temp_c, ace_advbal=False):
    """Mirror of fnc_calculateMuzzleVelocityCorrection.sqf.

    Returns (correction, coeff).  ace_advbal True -> no-op (ACE3 double
    count guard returns 1.0 without setting anything).
    """
    if ace_advbal:
        return 1.0, None
    if init_speed <= 0:
        return 1.0, None
    coeff = propellant_sensitivity(ammo)
    mps_per_degc = coeff * MPS_PER_DEGC_PER_FPS_DEGF
    pct_per_degc = mps_per_degc / init_speed * 100
    correction = 1 + (pct_per_degc * (temp_c - REF_TEMP_C)) / 100
    return max(0.85, min(1.15, correction)), coeff


class TestSensitivityCascade(unittest.TestCase):
    """fps/degF coefficient resolution (fnc_calculatePropellantSensitivity)."""

    def test_military_556(self):
        # M855-family: WC844 double-base ball ~1.5 fps/degF.
        self.assertAlmostEqual(propellant_sensitivity("B_556x45_Ball"), 1.5, places=4)

    def test_military_762(self):
        # M80-family: same ball-powder anchor.
        self.assertAlmostEqual(propellant_sensitivity("B_762x51_Ball"), 1.5, places=4)

    def test_9mm_double_base(self):
        # 9mm Parabellum: double-base, ~1.2 fps/degF.
        self.assertAlmostEqual(propellant_sensitivity("B_9x21_Ball"), 1.2, places=4)

    def test_temperature_stable_match(self):
        # .338 Norma match: temperature-stable powder ~0.3 fps/degF.
        self.assertAlmostEqual(propellant_sensitivity("B_338_NM_Ball"), 0.3, places=4)

    def test_unknown_ammo_central_default(self):
        # Unknown ammo: conservative central 1.0 fps/degF.
        self.assertAlmostEqual(propellant_sensitivity("B_999x999_Ball"), 1.0, places=4)

    def test_caliber_fallback(self):
        # Known caliber family, unknown exact class: family coefficient.
        self.assertAlmostEqual(
            propellant_sensitivity("B_556x45_Ball_Green"), 1.5, places=4
        )

    def test_sensitivity_span_within_literature(self):
        # All coefficients must sit in the published 0.14-2.0 fps/degF range.
        for ammo in [
            "B_556x45_Ball",
            "B_762x51_Ball",
            "B_9x21_Ball",
            "B_338_NM_Ball",
            "B_65x39_Caseless",
            "B_127x99_Ball",
        ]:
            c = propellant_sensitivity(ammo)
            self.assertGreaterEqual(c, 0.14)
            self.assertLessEqual(c, 2.0)


class TestMuzzleVelocityCorrection(unittest.TestCase):
    """%/degC normalised to the ammo's own initSpeed."""

    def test_556_reference_temp_no_change(self):
        # 5.56 at 21 degC: correction exactly 1.0.
        corr, _ = muzzle_velocity_correction("B_556x45_Ball", 905, 21.0)
        self.assertAlmostEqual(corr, 1.0, places=6)

    def test_556_cold_reduces_mv(self):
        # -30 degC: ~0.091%/degC * -51 = -4.6% -> correction ~0.954.
        corr, _ = muzzle_velocity_correction("B_556x45_Ball", 905, -30.0)
        mps_per_c = 1.5 * MPS_PER_DEGC_PER_FPS_DEGF
        pct = mps_per_c / 905 * 100
        expected = 1 + (pct * (-30 - 21)) / 100
        self.assertAlmostEqual(corr, expected, places=6)
        self.assertGreater(corr, 0.90)
        self.assertLess(corr, 0.98)

    def test_556_hot_increases_mv(self):
        # +50 degC: +2.7% -> correction ~1.027.
        corr, _ = muzzle_velocity_correction("B_556x45_Ball", 905, 50.0)
        self.assertGreater(corr, 1.01)
        self.assertLess(corr, 1.05)

    def test_9mm_larger_relative_shift(self):
        # Same 1.2 fps/degF powder, but 400 m/s pistol: the RELATIVE shift
        # is larger than a 905 m/s rifle with the same coefficient.
        pistol = muzzle_velocity_correction("B_9x21_Ball", 400, 50.0)[0]
        rifle_at_12 = muzzle_velocity_correction("B_9x21_Ball", 905, 50.0)[0]
        self.assertGreater(abs(pistol - 1.0), abs(rifle_at_12 - 1.0))

    def test_military_ball_vs_match_at_heat(self):
        # At +50 degC the temperature-stable .338 shifts less than the
        # military ball 5.56: this is the "no bias" requirement.
        match = muzzle_velocity_correction("B_338_NM_Ball", 900, 50.0)[0]
        military = muzzle_velocity_correction("B_556x45_Ball", 905, 50.0)[0]
        self.assertLess(abs(match - 1.0), abs(military - 1.0))

    def test_clamp_upper(self):
        # Extreme heat, slow round, sensitive powder: clamp at 1.15.
        corr, _ = muzzle_velocity_correction("B_9x21_Ball", 300, 95.0)
        self.assertAlmostEqual(corr, 1.15, places=6)

    def test_clamp_lower(self):
        # Extreme cold, slow round: clamp at 0.85.
        corr, _ = muzzle_velocity_correction("B_9x21_Ball", 300, -60.0)
        self.assertAlmostEqual(corr, 0.85, places=6)

    def test_no_mv_data_no_correction(self):
        # initSpeed <= 0: no correction possible, factor 1.0.
        corr, _ = muzzle_velocity_correction("B_556x45_Ball", 0, 50.0)
        self.assertEqual(corr, 1.0)

    def test_ace_advbal_double_count_guard(self):
        # ACE3 advanced ballistics active: no-op (ACE3 applies its own
        # per-ammo table).  This prevents compounding the correction.
        corr, _ = muzzle_velocity_correction(
            "B_556x45_Ball", 905, 50.0, ace_advbal=True
        )
        self.assertEqual(corr, 1.0)

    def test_reference_is_nato_epvat(self):
        # The zero-crossing is at 21 degC (AEP-97 / STANAG 4823).
        self.assertEqual(REF_TEMP_C, 21.0)


class TestSQFSyncPropellant(unittest.TestCase):
    """SQF source must contain the constants the Python mirrors rely on."""

    def _assert_in_sqf(self, filename, fragments, context):
        text = (_BALLISTICS / filename).read_text(encoding="utf-8")
        missing = [f for f in fragments if f not in text]
        self.assertFalse(
            missing,
            f"{filename}: {context} changed/missing in SQF: {missing}. "
            f"Re-sync the Python mirror in test_propellant_temp.py.",
        )

    def test_sensitivity_constants(self):
        self._assert_in_sqf(
            "fnc_calculatePropellantSensitivity.sqf",
            [
                "1.5",
                "1.2",
                "0.3",
                "AEE_Propellant",
            ],
            "propellant coefficient table and cascade",
        )

    def test_correction_constants(self):
        self._assert_in_sqf(
            "fnc_calculateMuzzleVelocityCorrection.sqf",
            [
                "0.3048",
                "1.8",
                "21",
                "0.85",
                "1.15",
                "ace_advanced_ballistics_ammoTemperatureEnabled",
            ],
            "unit conversion, reference temp, clamps, ACE3 guard",
        )


if __name__ == "__main__":
    unittest.main()
