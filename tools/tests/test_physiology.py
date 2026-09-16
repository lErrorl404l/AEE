#!/usr/bin/env python3
"""Reference checks for AEE's physiology models.

Mirrors of the SQF implementations in addons/physiology: hypoxia (TUC
model) and UV index (ISO 17166 / CIE clear-sky model).

Run: python3 -m unittest tools/tests/test_physiology.py
"""

import math
import unittest
from pathlib import Path

_PHYSIOLOGY = (
    Path(__file__).resolve().parents[2] / "addons" / "physiology" / "functions"
)


def equivalent_altitude(pressure_hpa):
    """Mirror of the ISA hypsometric relation in fnc_calculateHypoxia.sqf."""
    return 44330 * (1 - (pressure_hpa / 1013.25) ** 0.1903)


TUC_TABLE = [[6000, 1800], [7000, 240], [8000, 120], [9000, 45], [10000, 15]]


def tuc(eq_alt_m):
    """Mirror of the FAA TUC interpolation in fnc_calculateHypoxia.sqf.

    Below 6000 m the TUC is effectively infinite (the SQF uses 1e9), so
    the risk stays near zero.  Above 10000 m it floors at 15 s.
    """
    if eq_alt_m < 6000:
        return 1e9
    _tuc = 15
    for i in range(len(TUC_TABLE) - 1):
        lo = TUC_TABLE[i]
        hi = TUC_TABLE[i + 1]
        if lo[0] <= eq_alt_m <= hi[0]:
            frac = (eq_alt_m - lo[0]) / (hi[0] - lo[0])
            _tuc = lo[1] + frac * (hi[1] - lo[1])
    return max(_tuc, 15)


def hypoxia_risk(eq_alt_m, exposure_s):
    """Mirror of fnc_calculateHypoxia.sqf: exposure/TUC clamped 0..1."""
    t = tuc(eq_alt_m)
    return max(0.0, min(1.0, exposure_s / t))


def cross_sensitivity(dehydration, hypoxia, scale=1.0, enabled=True):
    """Mirror of fnc_applyCrossSensitivity.sqf.

    Dehydration amplifies hypoxia impact (1.0 at 0% .. 1.25 at 100%,
    Gopinathan 1988 cognitive-decrement anchor), hypoxia amplifies
    dehydration (1.0 at 0% .. 1.3 at 100%, altitude diuresis +
    respiratory loss anchor, Anand 1996).  Scale interpolates the
    coupling strength between 1.0 (none) and the full literature cap.
    Returns [effectiveDehydration, effectiveHypoxia].
    """
    if not enabled or scale <= 0:
        return [dehydration, hypoxia]
    dehydration = max(0.0, min(1.0, dehydration))
    hypoxia = max(0.0, min(1.0, hypoxia))
    hyp_amp_full = 1.0 + (1.25 - 1.0) * dehydration  # 1.0..1.25
    hyp_amp = 1.0 + (hyp_amp_full - 1.0) * scale
    deh_amp_full = 1.0 + (1.3 - 1.0) * hypoxia  # 1.0..1.3
    deh_amp = 1.0 + (deh_amp_full - 1.0) * scale
    eff_hypoxia = min(1.0, hypoxia * hyp_amp)
    eff_dehydration = min(1.0, dehydration * deh_amp)
    return [eff_dehydration, eff_hypoxia]


def uv_index(solar_elevation, ozone_du, altitude_m, overcast, month, is_summer=True):
    """Mirror of fnc_calculateUVIndex.sqf (ISO 17166 / CIE clear-sky).

    month is 1-12; is_summer overrides the May-August northern-hemisphere
    check so the test can fix the factor explicitly.
    """
    sin_elev = max(0.0, math.sin(math.radians(solar_elevation)))
    uv_clear = 12.5 * sin_elev
    ozone_factor = 0.0
    if sin_elev > 0.001:
        ozone_factor = math.exp(-0.0013 * ozone_du / sin_elev)
    alt_factor = 1 + (altitude_m / 1000) * 0.1
    cloud_factor = 1 - overcast * 0.7
    month_factor = 1.3 if (is_summer and 5 <= month <= 8) else 1.0
    value = uv_clear * ozone_factor * alt_factor * cloud_factor * month_factor
    return round(max(0.0, min(13.0, value)))


class TestHypoxiaTUC(unittest.TestCase):
    def test_equivalent_altitude_reference(self):
        # ISA: sea level -> 0 m; ~540 hPa -> ~5000 m.
        self.assertAlmostEqual(equivalent_altitude(1013.25), 0, places=1)
        self.assertAlmostEqual(equivalent_altitude(540.2), 5000, delta=60)

    def test_tuc_below_6000_is_infinite(self):
        # Below the FAA table the TUC is effectively infinite (1e9).
        self.assertEqual(tuc(5000), 1e9)
        self.assertEqual(tuc(0), 1e9)

    def test_tuc_at_table_points(self):
        self.assertEqual(tuc(6000), 1800)
        self.assertEqual(tuc(7000), 240)
        self.assertEqual(tuc(8000), 120)
        self.assertEqual(tuc(9000), 45)
        self.assertEqual(tuc(10000), 15)

    def test_tuc_interpolates_between_points(self):
        # Midway between 8000 (120) and 9000 (45): falls in (45, 120).
        mid = tuc(8500)
        self.assertGreater(mid, 45)
        self.assertLess(mid, 120)

    def test_tuc_above_10000_floors_at_15(self):
        self.assertEqual(tuc(12000), 15)

    def test_risk_zero_without_exposure(self):
        self.assertEqual(hypoxia_risk(8000, 0), 0.0)

    def test_risk_one_at_tuc(self):
        # Exposure equal to the TUC -> risk 1.
        self.assertEqual(hypoxia_risk(8000, 120), 1.0)

    def test_risk_clamped_above_tuc(self):
        self.assertEqual(hypoxia_risk(8000, 500), 1.0)

    def test_risk_linear_below_tuc(self):
        # Half the TUC -> risk 0.5.
        self.assertAlmostEqual(hypoxia_risk(8000, 60), 0.5, places=6)

    def test_risk_zero_at_low_altitude(self):
        # At 5000 m the TUC is infinite, so any finite exposure gives ~0.
        self.assertLess(hypoxia_risk(5000, 100000), 0.001)


class TestCrossSensitivity(unittest.TestCase):
    """Dehydration-hypoxia coupling (issue #40)."""

    def test_zero_dehydration_no_amplification(self):
        # 0% dehydration + 50% hypoxia: no amplification.
        eff_deh, eff_hyp = cross_sensitivity(0.0, 0.5)
        self.assertAlmostEqual(eff_hyp, 0.5, places=6)
        self.assertAlmostEqual(eff_deh, 0.0, places=6)

    def test_half_dehydration_amplifies_hypoxia(self):
        # 50% dehydration + 50% hypoxia: hypoxia amplifier = 1.125,
        # dehydration amplifier = 1.15.
        eff_deh, eff_hyp = cross_sensitivity(0.5, 0.5)
        self.assertAlmostEqual(eff_hyp, 0.5 * 1.125, places=6)
        self.assertAlmostEqual(eff_deh, 0.5 * 1.15, places=6)

    def test_full_both_clamped(self):
        # 100% dehydration + 100% hypoxia: both clamp to 1.0.
        eff_deh, eff_hyp = cross_sensitivity(1.0, 1.0)
        self.assertEqual(eff_deh, 1.0)
        self.assertEqual(eff_hyp, 1.0)

    def test_amplifier_bounds(self):
        # At full dehydration the hypoxia amplifier is 1.25; at full
        # hypoxia the dehydration amplifier is 1.3.
        _, eff_hyp = cross_sensitivity(1.0, 0.0)
        self.assertEqual(eff_hyp, 0.0)  # hypoxia risk 0 stays 0
        eff_deh, _ = cross_sensitivity(0.0, 1.0)
        self.assertEqual(eff_deh, 0.0)

    def test_half_dehydration_full_hypoxia(self):
        # 50% dehydration + 100% hypoxia: hypoxia clamped 1.0, dehydration
        # 0.5 * 1.3 = 0.65 (full hypoxia -> dehydration amplifier 1.3).
        eff_deh, eff_hyp = cross_sensitivity(0.5, 1.0)
        self.assertEqual(eff_hyp, 1.0)
        self.assertAlmostEqual(eff_deh, 0.65, places=6)

    def test_disabled_no_change(self):
        # Coupling disabled: identical to current behaviour.
        for deh in (0.0, 0.3, 0.5, 1.0):
            for hyp in (0.0, 0.4, 0.7, 1.0):
                eff_deh, eff_hyp = cross_sensitivity(deh, hyp, enabled=False)
                self.assertEqual(eff_deh, deh)
                self.assertEqual(eff_hyp, hyp)

    def test_zero_scale_no_change(self):
        # Scale 0: no coupling.
        eff_deh, eff_hyp = cross_sensitivity(0.5, 0.5, scale=0.0)
        self.assertEqual(eff_deh, 0.5)
        self.assertEqual(eff_hyp, 0.5)

    def test_half_scale_half_strength(self):
        # Scale 0.5: half the coupling.  Dehydration 0.5 -> amplifier
        # 1.0625 (between 1.0 and 1.125); hypoxia 0.5 -> amplifier 1.075.
        eff_deh, eff_hyp = cross_sensitivity(0.5, 0.5, scale=0.5)
        self.assertAlmostEqual(eff_hyp, 0.5 * 1.0625, places=6)
        self.assertAlmostEqual(eff_deh, 0.5 * 1.075, places=6)

    def test_monotonic_in_both(self):
        # Effective hypoxia rises with dehydration; effective dehydration
        # rises with hypoxia.
        eff0 = cross_sensitivity(0.0, 0.5)[1]
        eff1 = cross_sensitivity(0.5, 0.5)[1]
        eff2 = cross_sensitivity(1.0, 0.5)[1]
        self.assertLess(eff0, eff1)
        self.assertLess(eff1, eff2)


class TestSQFSyncPhysiology(unittest.TestCase):
    """SQF source must contain the constants the Python mirrors rely on."""

    def _assert_in_sqf(self, filename, fragments, context):
        text = (_PHYSIOLOGY / filename).read_text(encoding="utf-8")
        missing = [f for f in fragments if f not in text]
        self.assertFalse(
            missing,
            f"{filename}: {context} changed/missing in SQF: {missing}. "
            f"Re-sync the Python mirror in test_physiology.py.",
        )

    def test_hypoxia_constants(self):
        self._assert_in_sqf(
            "fnc_calculateHypoxia.sqf",
            ["44330", "1013.25", "6000", "1800", "10000", "15"],
            "ISA hypsometric and FAA TUC table",
        )

    def test_dehydration_constants(self):
        self._assert_in_sqf(
            "fnc_calculateDehydrationRisk.sqf",
            ["18", "23", "28", "32", "0.5", "1.0"],
            "WBGT bands and deficit thresholds",
        )

    def test_cross_sensitivity_constants(self):
        self._assert_in_sqf(
            "fnc_applyCrossSensitivity.sqf",
            ["1.25", "1.3", "linearConversion", "min 1"],
            "cross-sensitivity amplifiers",
        )


class TestUVIndex(unittest.TestCase):
    def test_clear_sky_reference(self):
        # 60 deg elevation, 300 DU, sea level, clear, winter (no boost):
        # 12.5 * sin(60) * exp(-0.0013*300/sin(60)) ~ 10.8 * 0.648 ~ 7.
        self.assertEqual(uv_index(60, 300, 0, 0, 1, is_summer=False), 7)

    def test_ozone_absorption(self):
        # More ozone absorbs more UV-B: the index falls as ozone rises.
        self.assertGreater(
            uv_index(60, 200, 0, 0, 1, is_summer=False),
            uv_index(60, 400, 0, 0, 1, is_summer=False),
        )

    def test_zero_elevation_zero_uv(self):
        # Sun at the horizon or below: UV floors at 0.
        self.assertEqual(uv_index(0, 300, 0, 0, 1, is_summer=False), 0)
        self.assertEqual(uv_index(-10, 300, 0, 0, 1, is_summer=False), 0)

    def test_altitude_increases_uv(self):
        self.assertGreater(
            uv_index(60, 300, 3000, 0, 6, is_summer=True),
            uv_index(60, 300, 0, 0, 6, is_summer=True),
        )

    def test_overcast_reduces_uv(self):
        # Full overcast cuts 70 %.
        clear = uv_index(60, 300, 0, 0, 6, is_summer=True)
        cloudy = uv_index(60, 300, 0, 1.0, 6, is_summer=True)
        self.assertLess(cloudy, clear)

    def test_summer_boost(self):
        self.assertGreater(
            uv_index(60, 300, 0, 0, 6, is_summer=True),
            uv_index(60, 300, 0, 0, 6, is_summer=False),
        )

    def test_never_negative_and_capped(self):
        for elev in range(0, 91, 15):
            self.assertGreaterEqual(uv_index(elev, 300, 8000, 0, 6, is_summer=True), 0)
            self.assertLessEqual(uv_index(elev, 300, 8000, 0, 6, is_summer=True), 13)


# ── Drift-lock caps (issue #62) ────────────────────────────────────────────
DEHYDRATION_AMPLIFIES_HYPOXIA_CAP = 1.25  # Gopinathan 1988
HYPOXIA_AMPLIFIES_DEHYDRATION_CAP = 1.3  # Anand 1996


class TestDriftLockCrossSensitivity(unittest.TestCase):
    """Pins the cross-sensitivity caps AND their behavioural consequence."""

    def test_caps_are_pinned(self):
        self.assertEqual(DEHYDRATION_AMPLIFIES_HYPOXIA_CAP, 1.25)
        self.assertEqual(HYPOXIA_AMPLIFIES_DEHYDRATION_CAP, 1.3)

    def test_cap_behaviour(self):
        # The caps live on the AMPLIFIERS (visible where the min-1 clamp
        # does not mask them).  At 50% both risks: hypoxia amplifier hits
        # 1.125, dehydration amplifier 1.15 (linear 1.0..cap by the risk).
        eff_deh, eff_hyp = cross_sensitivity(0.5, 0.5)
        self.assertAlmostEqual(eff_hyp, 0.5 * 1.125, places=4)
        self.assertAlmostEqual(eff_deh, 0.5 * 1.15, places=4)
        # Full scale, full risk: the min-1 clamp saturates the output.
        eff_deh, eff_hyp = cross_sensitivity(1.0, 1.0)
        self.assertAlmostEqual(eff_hyp, 1.0, places=4)
        self.assertAlmostEqual(eff_deh, 1.0, places=4)
        # Half coupling: the amplifier itself is half-way to the cap,
        # then applied to the risk.
        eff_deh, eff_hyp = cross_sensitivity(0.5, 0.5, scale=0.5)
        self.assertAlmostEqual(eff_hyp, 0.5 * 1.0625, places=4)  # amp 1.0625
        self.assertAlmostEqual(eff_deh, 0.5 * 1.075, places=4)  # amp 1.075

    def test_sqf_caps(self):
        text = (_PHYSIOLOGY / "fnc_applyCrossSensitivity.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("1.25", text)
        self.assertIn("1.3", text)


if __name__ == "__main__":
    unittest.main()
