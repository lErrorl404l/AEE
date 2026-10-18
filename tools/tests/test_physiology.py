#!/usr/bin/env python3
"""Reference checks for AEE's physiology models.

Mirrors of the SQF implementations in the physiology family addons: hypoxia (TUC
model) and UV index (ISO 17166 / CIE clear-sky model).

Run: python3 -m unittest tools/tests/test_physiology.py
"""

import math
import re
import sys
import unittest
from pathlib import Path

_ADDONS = Path(__file__).resolve().parents[2] / "addons"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sqf_lite import SqfParser, SqfRuntime, tokenize  # noqa: E402


def _read_physiology(name):
    """Read an SQF function file from the physiology family addons
    (physiology, strain, altitude, dive, clothing), resolving categorised
    subfolders (issue #203).  The function NAME is flat."""
    for f in _ADDONS.rglob(name):
        return f.read_text(encoding="utf-8")
    raise FileNotFoundError(f"{name} not found under {_ADDONS}")


def equivalent_altitude(pressure_hpa):
    """Mirror of the ISA inverse in fnc_calculateHypoxia.sqf (troposphere
    power law to 226.321 hPa, isothermal stratosphere above)."""
    if pressure_hpa >= 226.321:
        return 44330.8 * (1 - (pressure_hpa / 1013.25) ** 0.190263)
    return 11000 + (287.05287 * 216.65 / 9.80665) * math.log(226.321 / pressure_hpa)


def isa_pressure_hpa(alt_m):
    """ISA pressure, mirror of fnc_calculateBarometricPressure (in hPa)."""
    alt = max(alt_m, 0.0)
    if alt <= 11000:
        return 1013.25 * (1 - 0.0065 * alt / 288.15) ** 5.25588
    return 226.321 * math.exp(-9.80665 * (alt - 11000) / (287.05287 * 216.65))


def _sqf_tuc_table():
    """The TUC table, read from the SQF so the mirror cannot drift."""
    src = _read_physiology("fnc_calculateHypoxia.sqf")
    block = src[
        src.index("private _tucTable = [") : src.index(
            "];", src.index("private _tucTable")
        )
    ]
    return [
        [float(a), float(b)]
        for a, b in re.findall(r"\[([0-9.]+),\s*([0-9.]+)\]", block)
    ]


TUC_TABLE = _sqf_tuc_table()
TUC_ONSET_M = TUC_TABLE[0][0]


def tuc(eq_alt_m):
    """Mirror of the TUC interpolation in fnc_calculateHypoxia.sqf: ln(TUC)
    is interpolated between the FAA AC 61-107B rows; below the 18,000 ft
    onset it is unlimited (1e9); above the last row it holds the last."""
    if eq_alt_m < TUC_ONSET_M:
        return 1e9
    out = TUC_TABLE[-1][1]
    for lo, hi in zip(TUC_TABLE, TUC_TABLE[1:]):
        if lo[0] <= eq_alt_m <= hi[0]:
            frac = (eq_alt_m - lo[0]) / (hi[0] - lo[0])
            out = math.exp(math.log(lo[1]) + frac * (math.log(hi[1]) - math.log(lo[1])))
    return out


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


def uv_index(solar_elevation, ozone_du, altitude_m, overcast, doy=172):
    """Mirror of fnc_calculateUVIndex.sqf (Madronich 2007 clear sky, the
    Earth-Sun distance term, WHO altitude term, overcast CMF 0.35)."""
    mu0 = max(0.0, math.sin(math.radians(solar_elevation)))
    uv_clear = (
        12.50 * mu0**2.42 * (max(ozone_du, 100) / 300) ** -1.23 if mu0 > 0 else 0.0
    )
    dist = 1 + 0.033 * math.cos(math.radians(360 * (doy - 3) / 365))
    alt_factor = 1 + (altitude_m / 1000) * 0.1
    cloud_factor = 1 - overcast * 0.65
    return round(max(0.0, uv_clear * dist * alt_factor * cloud_factor))


FT = 0.3048


class TestHypoxiaTUC(unittest.TestCase):
    def test_equivalent_altitude_reference(self):
        # ISA: sea level -> 0 m; 540.2 hPa -> 5000 m; 226.3 hPa -> 11 km;
        # 54.75 hPa -> 20 km (ICAO Doc 7488).
        self.assertAlmostEqual(equivalent_altitude(1013.25), 0, places=1)
        self.assertAlmostEqual(equivalent_altitude(540.2), 5000, delta=10)
        self.assertAlmostEqual(equivalent_altitude(226.32), 11000, delta=5)
        self.assertAlmostEqual(equivalent_altitude(54.75), 20000, delta=20)

    def test_tuc_matches_faa_ac_61_107b(self):
        # Each published altitude falls inside its published TUC range.
        for alt_ft, lo_s, hi_s in (
            (18000, 1200, 1800),
            (22000, 600, 600),
            (25000, 180, 300),
            (28000, 150, 180),
            (30000, 60, 120),
            (35000, 30, 60),
            (40000, 15, 20),
            (45000, 9, 15),
            (50000, 9, 12),
        ):
            value = tuc(alt_ft * FT + 0.5)
            self.assertGreaterEqual(value, lo_s * 0.97, f"{alt_ft} ft: {value:.0f} s")
            self.assertLessEqual(value, hi_s * 1.03, f"{alt_ft} ft: {value:.0f} s")

    def test_tuc_falls_monotonically(self):
        values = [tuc(a) for a in range(int(TUC_ONSET_M), 16000, 50)]
        for a, b in zip(values, values[1:]):
            self.assertLessEqual(b, a)

    def test_tuc_below_18000_ft_is_unlimited(self):
        self.assertEqual(tuc(5000), 1e9)
        self.assertEqual(tuc(0), 1e9)

    def test_risk_zero_without_exposure(self):
        self.assertEqual(hypoxia_risk(8000, 0), 0.0)

    def test_risk_one_at_tuc(self):
        self.assertEqual(hypoxia_risk(8000, tuc(8000)), 1.0)

    def test_risk_linear_below_tuc(self):
        self.assertAlmostEqual(hypoxia_risk(8000, tuc(8000) / 2), 0.5, places=6)

    def test_breathing_altitude_not_terrain(self):
        # The bug this pins: a helicopter crew at 7,620 m (25,000 ft) over
        # sea-level terrain breathes ISA 376 hPa, not the 1013 hPa station
        # pressure of the ground below.  The SQF carries the station pressure
        # up the ISA ratio; that must reproduce the flight level.
        station = 1013.25
        breathing = station * isa_pressure_hpa(7620) / isa_pressure_hpa(0)
        self.assertAlmostEqual(equivalent_altitude(breathing), 7620, delta=5)
        src = _read_physiology("fnc_calculateHypoxia.sqf")
        self.assertIn("_pIsaBreath / _pIsaGround", src)
        self.assertIn('isKindOf "Plane"', src)
        self.assertIn("min 2438", src)


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
        text = _read_physiology(filename)
        missing = [f for f in fragments if f not in text]
        self.assertFalse(
            missing,
            f"{filename}: {context} changed/missing in SQF: {missing}. "
            f"Re-sync the Python mirror in test_physiology.py.",
        )

    def test_hypoxia_constants(self):
        self._assert_in_sqf(
            "fnc_calculateHypoxia.sqf",
            [
                "44330.8",
                "ISA_SEA_LEVEL_PRESSURE_HPA",
                "226.321",
                "5486",
                "1500",
                "15240",
                "10.5",
            ],
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
    def test_madronich_reference_points(self):
        # Madronich 2007 Table: 300 DU, sea level, clear.  SZA 0 -> 12.5,
        # SZA 30 -> 8.8, SZA 60 -> 2.3 (12.5 * mu0^2.42), +/-3.3 % distance.
        self.assertIn(uv_index(90, 300, 0, 0, doy=80), (12, 13))
        self.assertIn(uv_index(60, 300, 0, 0, doy=80), (8, 9))
        self.assertIn(uv_index(30, 300, 0, 0, doy=80), (2, 3))

    def test_mid_latitude_summer_noon(self):
        # Athens (38 N) late June noon, SZA ~15 deg, ~300 DU: observed
        # clear-sky UVI 9-11 (WHO/Greek network climatology).
        self.assertIn(uv_index(75, 300, 0, 0, doy=172), (9, 10, 11))

    def test_ozone_absorption(self):
        self.assertGreater(uv_index(60, 200, 0, 0), uv_index(60, 400, 0, 0))

    def test_zero_elevation_zero_uv(self):
        self.assertEqual(uv_index(0, 300, 0, 0), 0)
        self.assertEqual(uv_index(-10, 300, 0, 0), 0)

    def test_altitude_increases_uv(self):
        self.assertGreater(uv_index(60, 300, 3000, 0), uv_index(60, 300, 0, 0))

    def test_overcast_reduces_uv(self):
        self.assertLess(uv_index(60, 300, 0, 1.0), uv_index(60, 300, 0, 0))

    def test_no_month_fudge_in_sqf(self):
        src = _read_physiology("fnc_calculateUVIndex.sqf")
        self.assertNotIn("_monthFactor", src)
        self.assertIn("currentSunElevation", src)
        self.assertIn("12.50 * (_mu0 ^ 2.42)", src)

    def test_never_negative(self):
        for elev in range(0, 91, 15):
            self.assertGreaterEqual(uv_index(elev, 300, 8000, 0), 0)


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
        text = _read_physiology("fnc_applyCrossSensitivity.sqf")
        self.assertIn("1.25", text)
        self.assertIn("1.3", text)


# ─── CBA player-event registration (issue #302) ─────────────────────────────
PHYSIOLOGY_POST_INIT = _ADDONS / "physiology" / "XEH_postInit.sqf"

# The CBA functions this component may call.  Checked against CBA A3 3.19.0
# build 260808: cba_events.pbo and cba_common.pbo, extracted with Mikero
# extractpbo on 2026-10-18.  CBA defines no CBA_fnc_addPlayerKilledHandler,
# which is the #302 defect: the call aborted and the reset never registered.
CBA_3_19_0_FUNCS = {
    "CBA_fnc_addBISPlayerEventHandler",
    "CBA_fnc_addEventHandler",
    "CBA_fnc_addPerFrameHandler",
    "CBA_fnc_addPlayerEventHandler",
    "CBA_fnc_currentUnit",
}

# The exact shipped registration.  "Killed" is an engine unit event; the CBA
# BIS player route installs it on the controlled unit and re-attaches after
# respawn.  The handler reads neither argument, so no params line is needed.
KILLED_REGISTRATION = re.compile(
    r'\["AEE_OnPlayerKilled",\s*"Killed",\s*(\{.*?\})\s*\]'
    r"\s*call\s+CBA_fnc_addBISPlayerEventHandler;",
    re.S,
)


def _code(text):
    """Source with comments removed.  AEE comments name the very functions
    these tests scan for, so a raw-text scan matches prose first."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "\n".join(re.sub(r"//.*$", "", line) for line in text.splitlines())


class TestKilledHandlerRegistration(unittest.TestCase):
    """The acclimatisation reset must register through a CBA function that
    exists, on an event the engine raises (issue #302)."""

    def setUp(self):
        self.src = PHYSIOLOGY_POST_INIT.read_text(encoding="utf-8")
        self.code = _code(self.src)

    def test_every_cba_function_used_is_one_cba_defines(self):
        used = set(re.findall(r"\bCBA_fnc_\w+", self.code))
        self.assertTrue(used, "the postInit registers no CBA handler")
        unknown = sorted(used - CBA_3_19_0_FUNCS)
        self.assertFalse(unknown, f"not defined by CBA 3.19.0: {unknown}")

    def test_the_reset_registers_on_the_killed_event(self):
        self.assertNotIn("CBA_fnc_addPlayerKilledHandler", self.code)
        self.assertIsNotNone(
            KILLED_REGISTRATION.search(self.code),
            "the killed-handler registration moved or changed event",
        )

    def test_the_registered_handler_resets_acclimatisation(self):
        """Run the shipped registration and the shipped handler body."""
        match = KILLED_REGISTRATION.search(self.code)
        self.assertIsNotNone(match, "the killed-handler registration moved")
        ns = {}
        captured = {}
        rt = SqfRuntime({"missionNamespace": ns})

        def add_bis(key, event_type, code, ignore_virtual=True):
            captured.update(key=key, event_type=event_type)
            # The engine raises Killed with [_unit, _killer].
            rt.push()
            rt.set("_this", [{}, {}])
            try:
                rt.run(code.body)
            finally:
                rt.pop()
            return True

        rt.globals["CBA_fnc_addBISPlayerEventHandler"] = add_bis
        rt.run(SqfParser(tokenize(match.group(0))).parse_program())

        self.assertEqual(captured["key"], "AEE_OnPlayerKilled")
        self.assertEqual(captured["event_type"], "Killed")
        self.assertEqual(
            ns.get("__QEGVAR__altitude_acclimatizationPercent"),
            0,
            "the handler did not reset the acclimatisation state",
        )


if __name__ == "__main__":
    unittest.main()
