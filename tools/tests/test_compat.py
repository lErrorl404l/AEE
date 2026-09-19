#!/usr/bin/env python3
"""Compat addon contract tests (issue #93).

The six compat addons are the integration surface where AEE physics leaves
the mod: ACRE2/TFAR radio, ACE3 medical, KAT circulation, ACM hypoxia, Real
Weather.  They had ZERO test coverage.  Each test mirrors the compat
function's pure logic - the parts that take AEE state and produce a value
(signal %, range multiplier, medical mapping, fluid drain) - and locks the
contract, so a wrong index or unit conversion fails CI instead of
degrading silently in-game.

The mirrors are written from the SQF source in addons/compat_*/functions/.
Host mods only matter at integration time (the docker --hosts mode); the
pure functions here need no host.

Run: python3 -m unittest tools.tests.test_compat
"""

import math
import unittest


# ─── compat_acre2: signal callback contract ─────────────────────────────────
# fnc_integrateACRE2.sqf:
#   dB_shift = (propIdx - 1) * 8
#   signalDBm = maxSignal + dB_shift
#   signalPct = ((signalDBm - min) / (max - min)) clamped 0..1
#   returns [signalPct, signalDBm]


def _read_env_biome():
    """Read fnc_getBiome.sqf from its categorised subfolder (issue #203)."""
    from pathlib import Path

    base = Path("addons/environmental/functions")
    for f in base.rglob("fnc_getBiome.sqf"):
        return f.read_text(encoding="utf-8")
    raise FileNotFoundError("fnc_getBiome.sqf not found")


def acre2_signal(prop_idx, max_signal_dbm, db_shift=8.0, sens_min=-110.0, sens_max=0.0):
    """Mirror of the ACRE2 custom signal callback."""
    prop_idx = 1.0 if prop_idx <= 0 else prop_idx
    shift = (prop_idx - 1.0) * db_shift
    signal_dbm = max_signal_dbm + shift
    pct = (signal_dbm - sens_min) / (sens_max - sens_min)
    return max(0.0, min(1.0, pct)), signal_dbm


class TestCompatACRE2(unittest.TestCase):
    def test_neutral_index_no_shift(self):
        pct, dbm = acre2_signal(1.0, -80.0)
        self.assertEqual(dbm, -80.0)
        self.assertAlmostEqual(pct, (-80 + 110) / 110, places=6)

    def test_propagation_boost_extends_range(self):
        _, dbm_boost = acre2_signal(2.0, -80.0)  # +8 dB
        _, dbm_neutral = acre2_signal(1.0, -80.0)
        self.assertAlmostEqual(dbm_boost - dbm_neutral, 8.0, places=6)

    def test_propagation_fade_reduces_range(self):
        _, dbm_fade = acre2_signal(0.3, -80.0)  # -5.6 dB
        _, dbm_neutral = acre2_signal(1.0, -80.0)
        self.assertAlmostEqual(dbm_fade - dbm_neutral, -5.6, places=4)

    def test_percent_bounded_0_1(self):
        for idx in [0.3, 0.5, 1.0, 1.5, 2.0]:
            pct, _ = acre2_signal(idx, -80.0)
            self.assertGreaterEqual(pct, 0.0)
            self.assertLessEqual(pct, 1.0)

    def test_zero_guard_uses_neutral(self):
        # propIdx <= 0 is treated as neutral 1.0 in the SQF.
        pct, dbm = acre2_signal(0.0, -80.0)
        self.assertEqual(dbm, -80.0)

    def test_sensitivity_window_recomputes_pct(self):
        # A weak signal outside the window clamps at 0%.
        pct, _ = acre2_signal(0.3, -120.0)  # below -110 floor
        self.assertEqual(pct, 0.0)


# ─── compat_tfar: range multiplier contract ─────────────────────────────────
# fnc_integrateTFAR.sqf:
#   mult = (propIdx - 1) * 0.6 + 1, clamped [0.3, 1.5]
#   sending only (receiving stays 1.0 so the scale is not cancelled)


def tfar_mult(prop_idx, scale=0.6, lo=0.3, hi=1.5):
    """Mirror of the TFAR sending-distance multiplier."""
    prop_idx = 1.0 if prop_idx <= 0 else prop_idx
    mult = (prop_idx - 1.0) * scale + 1.0
    return max(lo, min(hi, mult))


class TestCompatTFAR(unittest.TestCase):
    def test_neutral_index_unit_mult(self):
        self.assertEqual(tfar_mult(1.0), 1.0)

    def test_boost_scales_sending(self):
        # propIdx 2.0 -> (1.0*0.6)+1 = 1.6, but clamped at 1.5 (max).
        self.assertEqual(tfar_mult(2.0), 1.5)
        self.assertAlmostEqual(tfar_mult(1.5), 1.3, places=4)  # +0.3

    def test_fade_reduces_sending(self):
        self.assertAlmostEqual(tfar_mult(0.3), 0.58, places=4)  # -0.42

    def test_clamped_range(self):
        # propIdx 2.5 -> (1.5*0.6)+1 = 1.9 clamped to 1.5 (max).
        self.assertEqual(tfar_mult(2.5), 1.5)
        # propIdx 0.1 -> (0.1-1)*0.6+1 = 0.46, already above the 0.3 floor.
        self.assertAlmostEqual(tfar_mult(0.1), 0.46, places=4)
        # The 0.3 floor is unreachable: propIdx must be > 0 (the <= 0
        # guard returns neutral 1.0) and the clamp needs idx < 0.17, so
        # the reachable floor is 0.4 (at idx -> 0+).  The clamp range
        # still holds for the whole domain.
        self.assertGreaterEqual(tfar_mult(1e-9), 0.3)
        self.assertLessEqual(tfar_mult(1e-9), 1.5)
        self.assertGreaterEqual(tfar_mult(2.5), 0.3)

    def test_zero_guard(self):
        # propIdx <= 0 is neutral 1.0 -> mult 1.0.
        self.assertEqual(tfar_mult(0.0, lo=0.3), tfar_mult(1.0))

    def test_monotonic(self):
        prev = -1.0
        for idx in [x / 10 for x in range(3, 21)]:
            m = tfar_mult(idx)
            self.assertGreaterEqual(m, prev)
            prev = m


# ─── compat_ace3: medical mapping contract ──────────────────────────────────
# fnc_integrateMedical.sqf:
#   WBGT > 32 -> hr +30, flow -20, pain 0.3
#   WBGT > 28 -> hr +20, flow -15
#   WBGT > threshold (0) -> hr +10, flow -10
#   risk > 0.7 -> flow -15 extra, pain max 0.2
#   risk > threshold (0) -> flow -8 extra
#   heat stroke: WBGT > 32 AND risk > 0.8 -> cardiac arrest
#   burn: damage = (temp - burnTemp) * 0.0005, type "burn"


def ace3_medical_map(
    wbgt,
    risk,
    temp,
    wbgt_threshold=23.0,
    risk_threshold=0.3,
    heatstroke_wbgt=32.0,
    burn_temp=25.0,
    burn_scale=0.0005,
):
    """Mirror of the ACE3 vitals mapping.  Returns (hr, flow, pain,
    cardiac_arrest, burn_damage).

    Exclusive band cascade: >32 very dangerous, >28 danger, >threshold
    extreme caution.  The sequential-if version let the caution band
    overwrite the danger band (a real bug the mirror caught; the SQF now
    fixes it).
    """
    hr = flow = pain = 0
    if wbgt > wbgt_threshold or risk > risk_threshold:
        if wbgt > 32:
            hr, flow, pain = 30, -20, 0.3
        elif wbgt > 28:
            hr, flow = 20, -15
        elif wbgt > wbgt_threshold:
            hr, flow = 10, -10
        if risk > 0.7:
            flow -= 15
            pain = max(pain, 0.2)
        if risk > risk_threshold:
            flow -= 8
    cardiac = wbgt > heatstroke_wbgt and risk > 0.8
    burn = (temp - burn_temp) * burn_scale if temp > burn_temp else 0.0
    return hr, flow, pain, cardiac, burn


class TestCompatACE3(unittest.TestCase):
    def test_neutral_no_vitals(self):
        # WBGT below the 23 threshold and risk below 0.3: no vitals.
        hr, flow, pain, cardiac, burn = ace3_medical_map(20, 0.1, 20)
        self.assertEqual((hr, flow, pain), (0, 0, 0))
        self.assertFalse(cardiac)
        self.assertEqual(burn, 0.0)

    def test_extreme_wbgt_strongest(self):
        hr, flow, pain, _, _ = ace3_medical_map(33, 0.1, 25)
        self.assertEqual(hr, 30)
        self.assertLessEqual(flow, -20)

    def test_danger_band(self):
        # WBGT 28-32 (danger): hr 20.  The sequential-if bug made this
        # return 10 (extreme caution overwrote); the cascade fixes it.
        hr, flow, _, _, _ = ace3_medical_map(30, 0.1, 25)
        self.assertEqual(hr, 20)
        self.assertEqual(flow, -15)

    def test_dehydration_compounds_flow(self):
        _, flow_low, _, _, _ = ace3_medical_map(25, 0.1, 25)
        _, flow_high, pain, _, _ = ace3_medical_map(25, 0.8, 25)
        self.assertLess(flow_high, flow_low)
        self.assertGreaterEqual(pain, 0.2)

    def test_heat_stroke_cardiac(self):
        # WBGT 33 > 32 and risk 0.85 > 0.8 -> cardiac arrest.
        _, _, _, cardiac, _ = ace3_medical_map(33, 0.85, 25)
        self.assertTrue(cardiac)
        _, _, _, cardiac_no, _ = ace3_medical_map(33, 0.5, 25)
        self.assertFalse(cardiac_no)

    def test_burn_damage_scales(self):
        # Burn threshold default 25 C: damage = (temp-25)*0.0005.
        _, _, _, _, burn = ace3_medical_map(20, 0.1, 50)
        self.assertAlmostEqual(burn, (50 - 25) * 0.0005, places=6)
        _, _, _, _, burn_none = ace3_medical_map(20, 0.1, 20)
        self.assertEqual(burn_none, 0.0)


# ─── compat_kat: fluid drain + SpO2 contract ────────────────────────────────
# fnc_integrateKAT.sqf:
#   dehyd = 0.05 + (T-15)max0*0.002 + (bodyTemp-37.5)max0*0.01 + risk*0.03
#   ECP drains fully, ISP drains half, clamped >= 100 mL; total recomputed
#   SpO2 = 97 - risk*32, clamped [60, 97]; PaO2 = 33 + (SpO2-60)/15*7


def kat_fluid_drain(temp, body_temp, risk, base=0.05):
    """Mirror of the KAT body-fluid drain amount (litres)."""
    dehyd = base
    dehyd += max(0.0, temp - 15.0) * 0.002
    dehyd += max(0.0, body_temp - 37.5) * 0.01
    dehyd += risk * 0.03
    return dehyd


def kat_fluid_compartments(dehyd, ecb=2700.0, ecp=3300.0, srbc=500.0, isp=10000.0):
    """Mirror of the ECP/ISP drain with the 100 mL floor and total."""
    ecp_new = max(100.0, ecp - dehyd)
    isp_new = max(100.0, isp - dehyd * 0.5)
    total = ecb + ecp_new + srbc + isp_new
    return [ecb, ecp_new, srbc, isp_new, total]


def kat_spo2(risk, scale=32.0, floor=60.0):
    """Mirror of the KAT SpO2 mapping (percent)."""
    return max(floor, 97.0 - risk * scale)


def kat_pao2(spo2):
    """Mirror of the KAT PaO2 mapping (33..40 mmHg over the 60..97 span)."""
    return 33.0 + ((spo2 - 60.0) / 37.0) * 7.0


class TestCompatKAT(unittest.TestCase):
    def test_no_drain_when_neutral(self):
        # T 15, body 37, no risk: only the base 0.05 L applies.
        self.assertAlmostEqual(kat_fluid_drain(15, 37, 0), 0.05, places=6)

    def test_heat_and_dehydration_add_drain(self):
        drain_hot = kat_fluid_drain(30, 38.5, 0.5)
        self.assertGreater(drain_hot, 0.05)
        # (30-15)*0.002 + (38.5-37.5)*0.01 + 0.5*0.03 = 0.03+0.01+0.015
        self.assertAlmostEqual(drain_hot, 0.05 + 0.03 + 0.01 + 0.015, places=4)

    def test_compartments_floor_at_100ml(self):
        # A drain of 20000 mL floors BOTH compartments (ECP full drain,
        # ISP half drain) at the 100 mL SQF clamp.
        [ecb, ecp, srbc, isp, total] = kat_fluid_compartments(20000.0)
        self.assertEqual(ecp, 100.0)
        self.assertEqual(isp, 100.0)
        self.assertEqual(total, ecb + 100 + srbc + 100)

    def test_total_recomputed(self):
        [ecb, ecp, srbc, isp, total] = kat_fluid_compartments(0.5)
        self.assertAlmostEqual(total, ecb + ecp + srbc + isp, places=6)

    def test_spo2_mapping(self):
        self.assertEqual(kat_spo2(0.0), 97.0)
        self.assertAlmostEqual(kat_spo2(0.5), 81.0, places=4)  # 97-16
        self.assertEqual(kat_spo2(1.0), 65.0)  # 97-32 = 65
        self.assertEqual(kat_spo2(2.0), 60.0)  # floor

    def test_pao2_consistent(self):
        self.assertAlmostEqual(kat_pao2(97.0), 40.0, places=4)  # upper
        self.assertAlmostEqual(kat_pao2(60.0), 33.0, places=4)  # lower


# ─── compat_acm: hypoxia duty factor contract ───────────────────────────────
# fnc_registerHypoxiaDutyFactor.sqf:
#   risk <= 0.8 -> 1.0 (no double-count with ACM's own altitude model)
#   risk > 0.8  -> 1 - ((risk - 0.8)/0.2) * 0.35, floor 0.65 at risk 1.0


def acm_duty_factor(risk):
    """Mirror of the ACM SpO2 duty factor."""
    if risk <= 0.8:
        return 1.0
    return 1.0 - ((risk - 0.8) / 0.2) * 0.35


class TestCompatACM(unittest.TestCase):
    def test_below_band_neutral(self):
        for r in [0.0, 0.4, 0.8]:
            self.assertEqual(acm_duty_factor(r), 1.0)

    def test_full_risk_floor(self):
        self.assertAlmostEqual(acm_duty_factor(1.0), 0.65, places=4)

    def test_linear_engagement(self):
        self.assertAlmostEqual(acm_duty_factor(0.9), 1.0 - 0.175, places=4)

    def test_no_double_count_design(self):
        # Below 0.8 the factor is exactly 1.0: ACM's altitude model owns
        # the band, AEE only adds near-unconsciousness.
        self.assertEqual(acm_duty_factor(0.79), 1.0)


# ─── compat_realweather: weather.json validation contract ───────────────────
# fnc_integrateRealWeather.sqf: every value is range-checked at the trust
# boundary; ANY out-of-range value rejects the WHOLE file (no partial
# publish).  Ranges: T -60..60 C, RH 0..100, P 850..1085 hPa, overcast 0..1.


def realweather_validate(temp, humidity, pressure, overcast):
    """Mirror of the weather.json trust-boundary check.

    Returns True if the whole record is valid, False if ANY field fails.
    """
    if temp is None or humidity is None or pressure is None or overcast is None:
        return False
    if not isinstance(temp, (int, float)) or not -60 <= temp <= 60:
        return False
    if not isinstance(humidity, (int, float)) or not 0 <= humidity <= 100:
        return False
    if not isinstance(pressure, (int, float)) or not 850 <= pressure <= 1085:
        return False
    if not isinstance(overcast, (int, float)) or not 0 <= overcast <= 1:
        return False
    return True


class TestCompatRealWeather(unittest.TestCase):
    def test_valid_record_accepted(self):
        self.assertTrue(realweather_validate(15.0, 50.0, 1013.0, 0.4))

    def test_out_of_range_humidity_rejects_whole_file(self):
        self.assertFalse(realweather_validate(15.0, 150.0, 1013.0, 0.4))

    def test_out_of_range_overcast_rejects(self):
        self.assertFalse(realweather_validate(15.0, 50.0, 1013.0, 1.5))

    def test_out_of_range_pressure_rejects(self):
        self.assertFalse(realweather_validate(15.0, 50.0, 800.0, 0.4))

    def test_missing_field_rejects(self):
        self.assertFalse(realweather_validate(None, 50.0, 1013.0, 0.4))
        self.assertFalse(realweather_validate(15.0, None, 1013.0, 0.4))

    def test_boundary_values_accepted(self):
        self.assertTrue(realweather_validate(-60, 0, 850, 0))
        self.assertTrue(realweather_validate(60, 100, 1085, 1))


class TestThresholdGatePattern(unittest.TestCase):
    """Issue #154 pattern 1: no getVariable-fallback-0 in medical gates.

    The #123 burn defect was one gate with a `0` fallback.  The audit
    found the SAME pattern in all four compat_ace3 gates (heart rate,
    cardiac arrest) — uninitialised settings made "any value fires".
    These drift-locks pin the fix: thresholds are resolved once with
    real defaults, never read inline with a 0 fallback.
    """

    def test_no_fallback_zero_gates(self):
        from pathlib import Path

        text = Path("addons/compat_ace3/functions/fnc_integrateMedical.sqf").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("medicalWBGTThreshold), 0]", text)
        self.assertNotIn("medicalRiskThreshold), 0]", text)
        self.assertNotIn("medicalHeatStrokeWBGT), 0]", text)
        self.assertNotIn("medicalBurnTemp), 0]", text)

    def test_resolved_thresholds_present(self):
        from pathlib import Path

        text = Path("addons/compat_ace3/functions/fnc_integrateMedical.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("medicalWBGTThreshold), 23]", text)
        self.assertIn("medicalRiskThreshold), 0.3]", text)
        self.assertIn("medicalHeatStrokeWBGT), 32]", text)
        self.assertIn("medicalBurnTemp), 25]", text)
        # The gates must use the resolved locals.
        self.assertIn("_wbgt > _wbgtThreshold", text)
        self.assertIn("_risk > _riskThreshold", text)
        self.assertIn("_wbgt > _heatStrokeWBGT", text)

    def test_uninitialised_settings_do_not_fire(self):
        # The mirror default 23/0.3/32: WBGT 10, risk 0.1 (below all
        # thresholds) must produce zero vitals even though the values are
        # above a hypothetical 0 fallback.
        hr, flow, pain, cardiac, burn = ace3_medical_map(10, 0.1, 20)
        self.assertEqual((hr, flow, pain), (0, 0, 0))
        self.assertFalse(cardiac)
        self.assertEqual(burn, 0.0)


class TestWorldLatitudePattern(unittest.TestCase):
    """Issue #179: one geolocation source, true geographic sign.

    The mod had 3-4 inconsistent latitude reads (solar used abs, space
    weather raw, Coriolis a map-Y guess) and no longitude or mapZone
    source at all.  These drift-locks pin the shared getWorldLocation
    source and its consumers.  getWorldLatitude is REMOVED (issue #179):
    every consumer calls getWorldLocation and selects the element it
    needs, and the BIS inverted latitude sign is corrected at the source
    (positive = north).
    """

    def test_shared_source_exists(self):
        from pathlib import Path

        text = Path("addons/core/functions/fnc_getWorldLocation.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("CfgWorlds", text)
        self.assertIn("[_signed, abs _signed, _lon, _zone]", text)
        # The BIS inverted convention must be corrected here (negate).
        self.assertIn("-getNumber", text)

    def test_old_latitude_function_removed(self):
        from pathlib import Path

        # #179 deletes getWorldLatitude - there is ONE source.
        self.assertFalse(
            Path("addons/core/functions/fnc_getWorldLatitude.sqf").exists(),
            "getWorldLatitude must be removed - use getWorldLocation",
        )
        prep = Path("addons/core/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertNotIn("getWorldLatitude", prep)

    def test_coriolis_uses_shared_source(self):
        from pathlib import Path

        text = Path(
            "addons/ballistics/functions/fnc_calculateCoriolisDeflection.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("getWorldLocation", text)
        self.assertIn("select 0", text)  # signed = true geographic sign
        # The map-Y equirectangular guess must be gone.
        self.assertNotIn("/ 100000 * 90", text)

    def test_magnitude_consumers_use_shared_source(self):
        from pathlib import Path

        solar = Path("addons/core/functions/fnc_calculateSolarRadiation.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("getWorldLocation", solar)
        self.assertIn("select 1", solar)  # magnitude

        biome = _read_env_biome()
        self.assertIn("getWorldLocation", biome)

        space = Path(
            "addons/environmental/functions/climatology/fnc_calculateSpaceWeather.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("getWorldLocation", space)

        compass = Path(
            "addons/maritime/functions/fnc_calculateCompassDeviation.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("getWorldLocation", compass)

        star = Path("addons/optics/functions/sensor/fnc_getStarCatalog.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("getWorldLocation", star)
        # No direct CfgWorlds latitude read may remain outside the source.
        self.assertNotIn('>> "latitude"', star)

    def test_only_one_direct_latitude_read(self):
        # #179: the ONLY direct CfgWorlds latitude read is the shared
        # source itself.  Count across all addons.
        from pathlib import Path

        count = 0
        for fn in Path("addons").rglob("*.sqf"):
            text = fn.read_text(encoding="utf-8", errors="replace")
            if '>> "latitude"' in text:
                count += 1
        self.assertEqual(
            count, 1, "exactly one direct CfgWorlds latitude read (getWorldLocation)"
        )


if __name__ == "__main__":
    unittest.main()
