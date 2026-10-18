#!/usr/bin/env python3
"""Reference checks for AEE's radio models.

The radio addon no longer computes a link budget.  ACRE2 (Longley-Rice ITM)
and TFAR own the free-space and terrain loss of a real link, so
fnc_calculateRadioPropagation publishes ONLY the losses those models do not
hold: the HF D-layer absorption, a flare's sudden ionospheric disturbance, a
cold battery's transmit derating and an EMP front-end upset.

Two earlier models left the addon and their mirrors left this suite with them:

  - the Friis/terrain/evaporation-duct budget (issues #305, #308): its duct
    N-deficit carried a spurious 0.1 factor and its Deygout diffraction was
    subtracted twice, once through fnc_calculateTerrainMaskedLink and once
    through fnc_calculateEmPropagation.  Both terms are gone; the guards
    below fail if either returns.
  - the Hall duct cutoff (issue #312): the radar path keeps the one cutoff
    law, Kerr 1951 lambda_max = 8.32e-4 delta^1.5 m
    (addons/radio/functions/radar/fnc_radarDuctRange.sqf).

The EM kernels that survive (two-ray ground, knife-edge, Deygout, valley
waveguide) are executed as SQF by tools/tests/test_em_propagation.py, so this
suite does not mirror them.

Run: python3 -m unittest tools.tests.test_radio
"""

import math
from pathlib import Path
import unittest

LN10 = 2.302585

ROOT = Path(__file__).resolve().parents[2]
RADIO = ROOT / "addons" / "radio"
PROPAGATION = RADIO / "functions" / "fnc_calculateRadioPropagation.sqf"
DUCT_RANGE = RADIO / "functions" / "radar" / "fnc_radarDuctRange.sqf"


def log10(x):
    """SQF's log command is base-10 (verified in-game: log 100 = 1).

    Python's math.log is natural log, so log10(x) = ln(x) / ln(10).
    """
    return math.log(x) / LN10


def excess_loss_db(
    iono_numerator,
    freq_hz,
    gyro_mhz,
    flare_haf=0.0,
    derate=1.0,
    battery=True,
    emp_factor=1.0,
):
    """Mirror of fnc_calculateRadioPropagation.sqf, the excess-loss path.

    iono_numerator: aee_radio_dLayerNumerator, 677.2 * I(chi) from
        fnc_calculateIonosphericAbsorption; the D-layer is transparent at
        30 MHz and above, so the term applies only below that.
    gyro_mhz: aee_radio_gyroFreqMHz, the longitudinal gyrofrequency.
    flare_haf: the NOAA SWPC D-RAP highest affected frequency, MHz.
    derate: the physiology battery capacity factor, clamped to 0.01..1.
    emp_factor: aee_core_empRadioFactor, clamped to 0.001..1.
    """
    iono_db = 0.0
    if freq_hz < 30e6:
        iono_db = iono_numerator / ((((freq_hz / 1e6) + gyro_mhz) ** 1.98) + 10.2)

    batt_db = 0.0
    if battery:
        batt_db = -10 * log10(max(0.01, min(1.0, derate)))

    emp_db = -20 * log10(max(0.001, min(1.0, emp_factor)))

    flare_db = 0.0
    if flare_haf > 0:
        flare_db = (flare_haf / (freq_hz / 1e6)) ** 1.5

    return iono_db + flare_db + batt_db + emp_db


def range_factor(excess_db):
    """Mirror of the published index: 10^(-L/20), 1 when there is no excess."""
    return 10 ** (-excess_db / 20)


def gyro_longitudinal_mhz(lat_deg):
    """Mirror of the centred-dipole f_L at 100 km (IGRF-13 B0 29.8 uT)."""
    lat = math.radians(lat_deg)
    b_ut = 29.8 * (6371 / 6471) ** 3 * math.sqrt(1 + 3 * math.sin(lat) ** 2)
    dip = math.atan(2 * math.tan(lat))
    return 0.028 * b_ut * abs(math.sin(dip))


def ionospheric_absorption(
    freq_hz, sun_elev_deg, ssn, flare_active, flare_value, lat_deg=40.0
):
    """Mirror of fnc_calculateIonosphericAbsorption.sqf (ITU-R P.533,
    George & Bradley), vertical incidence.  flare_value is the D-RAP HAF
    (MHz); the flare adds (HAF / f)^1.5 dB."""
    chi = min(90 - sun_elev_deg, 102)
    index = (1 + 0.0037 * ssn) * max(math.cos(math.radians(0.881 * chi)), 0) ** 1.3
    f = freq_hz / 1e6
    absorption = 677.2 * index / ((f + gyro_longitudinal_mhz(lat_deg)) ** 1.98 + 10.2)
    if flare_active and flare_value > 0:
        absorption += (flare_value / f) ** 1.5
    return max(0.0, absorption)


# ─── Sea-surface temperature (issue #37) ────────────────────────────────────
# Mirror of fnc_calculateSeaSurfaceTemperature.sqf: latitude-seasonal
# climatology blended with air temperature by the coupling weight.
#   clim = annual(lat) + 6 * cos(phase/12 * 360)  where phase = months
#          since local summer (0 = peak), local summer = July north,
#          January south.
#   sst  = w * T_air + (1 - w) * clim


def sea_surface_temp(air_c, lat, month, w=0.5):
    """Mirror of the maritime SST model (degC)."""
    abs_lat = abs(lat)
    if abs_lat < 15:
        annual = 28
    elif abs_lat < 30:
        annual = 22
    elif abs_lat < 50:
        annual = 13
    elif abs_lat < 65:
        annual = 5
    else:
        annual = 0
    local_summer = 7 if lat >= 0 else 1
    phase = (month - local_summer + 12) % 12
    clim = annual + 6 * math.cos(phase / 12 * 360 * math.pi / 180)
    return w * air_c + (1 - w) * clim


class TestIonosphericAbsorption(unittest.TestCase):
    def test_gyrofrequency_is_physical(self):
        # f_L at mid-latitude, 100 km: ~0.8-1.4 MHz (ITU-R P.533 maps).
        self.assertGreater(gyro_longitudinal_mhz(40), 0.8)
        self.assertLess(gyro_longitudinal_mhz(40), 1.4)

    def test_daytime_80m_is_heavily_absorbed(self):
        # Midday D-layer absorption at 3.5 MHz, solar maximum: tens of dB
        # per vertical pass (why 80 m is a night band).
        self.assertGreater(ionospheric_absorption(3.5e6, 70, 150, False, 0), 20)

    def test_upper_hf_is_lightly_absorbed(self):
        self.assertLess(ionospheric_absorption(21e6, 70, 150, False, 0), 3)

    def test_night_is_near_zero(self):
        night = ionospheric_absorption(3e6, -30, 100, False, 0)
        day = ionospheric_absorption(3e6, 60, 100, False, 0)
        self.assertLess(night, 0.01 * day)

    def test_absorption_falls_with_zenith_angle(self):
        values = [
            ionospheric_absorption(5e6, e, 100, False, 0) for e in (90, 60, 30, 10, 0)
        ]
        for a, b in zip(values, values[1:]):
            self.assertGreater(a, b)

    def test_sunspots_raise_absorption(self):
        self.assertGreater(
            ionospheric_absorption(5e6, 60, 200, False, 0),
            ionospheric_absorption(5e6, 60, 0, False, 0),
        )

    def test_flare_drap(self):
        # NOAA SWPC D-RAP: HAF = 10 log10(F) + 65 MHz; 1 dB at the HAF;
        # (HAF/f)^1.5 elsewhere.  An X1 flare (1e-4 W/m2) overhead: HAF 25 MHz.
        haf = 10 * math.log10(1e-4) + 65
        self.assertAlmostEqual(haf, 25.0)
        base = ionospheric_absorption(25e6, 90, 100, False, 0)
        flared = ionospheric_absorption(25e6, 90, 100, True, haf)
        self.assertAlmostEqual(flared - base, 1.0, places=6)
        src = (
            RADIO / "functions" / "fnc_calculateIonosphericAbsorption.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("((_haf / _fMHz) ^ 1.5)", src)

    def test_sqf_carries_the_p533_constants(self):
        src = next(RADIO.rglob("fnc_calculateIonosphericAbsorption.sqf")).read_text(
            encoding="utf-8"
        )
        for token in ("677.2", "0.0037", "0.881", "1.98", "10.2", "29.8", "min 102"):
            self.assertIn(token, src)


class TestSeaSurfaceTemperature(unittest.TestCase):
    """Issue #37: the maritime SST feed for the evaporation duct."""

    def test_tropics_warm_all_year(self):
        # Tropical SST stays warm year-round; the seasonal swing is
        # modest (28 +- 6 C climatology, blended toward the air).
        for month in [1, 4, 7, 10]:
            sst = sea_surface_temp(28, 10, month, w=0.2)
            self.assertGreaterEqual(sst, 20)
            self.assertLessEqual(sst, 34)

    def test_north_sea_cold_in_winter(self):
        # Lat 55 N (subpolar): January coldest, July warmest.
        jan = sea_surface_temp(4, 55, 1, w=0.5)
        jul = sea_surface_temp(16, 55, 7, w=0.5)
        self.assertLess(jan, jul)

    def test_southern_hemisphere_phase_inverted(self):
        # Lat -33 (subtropical south): January is local summer (warm),
        # July local winter (cold).
        jan = sea_surface_temp(24, -33, 1, w=0.5)
        jul = sea_surface_temp(14, -33, 7, w=0.5)
        self.assertGreater(jan, jul)

    def test_air_coupling_blends(self):
        # w=1.0: SST follows air exactly; w=0: SST is pure climatology.
        self.assertAlmostEqual(sea_surface_temp(25, 45, 7, w=1.0), 25.0, places=6)
        pure_clim = sea_surface_temp(25, 45, 7, w=0.0)
        self.assertAlmostEqual(pure_clim, 13 + 6, places=6)  # July peak

    def test_air_sea_gradient_direction(self):
        # Warm air over a cold sea gives a positive (T - SST), the
        # classic duct condition direction.
        sst = sea_surface_temp(25, 60, 1, w=0.5)  # cold northern winter sea
        self.assertGreater(25.0 - sst, 0)

    def test_the_sqf_carries_the_same_bands(self):
        src = next(
            (ROOT / "addons" / "maritime").rglob(
                "fnc_calculateSeaSurfaceTemperature.sqf"
            )
        ).read_text(encoding="utf-8")
        self.assertIn("[28, 22, 13, 5, 0] select _bandIdx", src)
        self.assertIn("_localSummer = [1, 7] select", src)


class TestBatteryDerating(unittest.TestCase):
    """Issue #36: cold batteries derate radio effective transmit power."""

    def test_cold_battery_is_a_ten_log_loss(self):
        # A capacity factor of 0.7 is -10 log10(0.7) = 1.55 dB.
        self.assertAlmostEqual(excess_loss_db(0, 1e8, 1.0, derate=0.7), 1.549, places=3)

    def test_the_floor_is_the_sqf_clamp(self):
        # The SQF clamps the derating at 0.01, so the worst case is
        # -10 log10(0.01) = 20 dB.  A floor of 0.3 (an earlier mirror
        # value) would have hidden 14.8 dB of the loss.  The delta absorbs
        # the base-10 log round trip; the value under test is 20 dB.
        self.assertAlmostEqual(
            excess_loss_db(0, 1e8, 1.0, derate=0.0), 20.0, delta=1e-3
        )
        src = PROPAGATION.read_text(encoding="utf-8")
        self.assertIn("_derate = (_derate max 0.01) min 1;", src)

    def test_toggle_off_ignores_derating(self):
        # With the CBA toggle off, a cold battery changes nothing.
        cold_on = excess_loss_db(0, 1e8, 1.0, derate=0.7)
        cold_off = excess_loss_db(0, 1e8, 1.0, derate=0.7, battery=False)
        self.assertGreater(cold_on, 0)
        self.assertEqual(cold_off, 0.0)


class TestExcessLossModel(unittest.TestCase):
    """The radio layer publishes only the losses ACRE2/TFAR do not model."""

    SRC = PROPAGATION.read_text(encoding="utf-8")

    def test_no_double_counted_or_invented_terms(self):
        # FSPL and terrain belong to ACRE2's ITM / TFAR; the flat "hot & dry"
        # penalty and the biome foliage constant had no physical source.
        for token in (
            "147.55",
            "_absorptionPenalty = 2",
            "_terrainLoss = 3",
            "0.3 + 1.7",
        ):
            self.assertNotIn(token, self.SRC)

    def test_the_d_block_is_transparent_above_30_mhz(self):
        self.assertEqual(excess_loss_db(7800, 1e8, 1.0), 0.0)
        self.assertGreater(excess_loss_db(7800, 3e6, 1.0), 20)

    def test_loss_terms(self):
        for token in (
            "_battDB = -10 * log _derate",
            "private _empDB = -20 * log _empFactor",
            "private _index = 10 ^ (-_excessDB / 20)",
            "if (_freqHz < 30e6) then",
        ):
            self.assertIn(token, self.SRC)
        # A half-capacity cold battery is a 3.01 dB transmit loss; a 0.5 EMP
        # amplitude factor is 6.02 dB; together the free-space range falls
        # to 10^(-9.03/20) = 0.354.
        excess = -10 * math.log10(0.5) - 20 * math.log10(0.5)
        self.assertAlmostEqual(range_factor(excess), 0.3536, places=3)

    def test_acre_callback_evaluates_hf_at_the_link_frequency(self):
        acre = (
            ROOT / "addons" / "compat_acre2" / "functions" / "fnc_integrateACRE2.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn('"aee_radio_dLayerNumerator"', acre)
        self.assertIn("if (_freq < 30) then", acre)
        self.assertNotIn("QEGVAR(", acre.split("compile '")[1])


class TestSingleDuctCutoffLaw(unittest.TestCase):
    """Issue #312: one evaporation-duct cutoff law in the addon.

    The radar path keeps Kerr 1951, lambda_max = 8.32e-4 delta^1.5 m.  The
    Hall law that the SHF link budget carried (2.5e-3 * sqrt(dN/delta - 0.157)
    * delta^1.5 m) left the addon with that budget.
    """

    def test_the_kerr_cutoff_is_the_one_law(self):
        src = DUCT_RANGE.read_text(encoding="utf-8")
        self.assertIn("8.32e-4 * (_delta ^ 1.5)", src)
        # Verified vector from the header: delta = 15 m -> lambda 0.0483 m,
        # so the minimum trapped frequency is 6.2 GHz.
        lam = 8.32e-4 * 15.0**1.5
        self.assertAlmostEqual(lam, 0.0483, places=4)
        self.assertAlmostEqual(3e8 / lam / 1e9, 6.21, places=2)

    def test_the_retired_hall_law_is_absent(self):
        for path in RADIO.rglob("*.sqf"):
            text = path.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("2.5e-3", text, f"{path.name} carries the Hall law again")

    def test_the_metre_valued_kerr_constant_cannot_return(self):
        # 0.085 was Kerr's centimetre-valued constant read as metres, a unit
        # error of about 100x (issue #312).  fnc_radarSeaClutter's NRL term
        # legitimately carries 0.085 * _psi, so the guard is the delta form.
        for path in RADIO.rglob("*.sqf"):
            text = path.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn(
                "0.085 * (_delta", text, f"{path.name} carries the unit error"
            )

    def test_no_evaporation_duct_n_deficit_in_the_addon(self):
        # Issue #305: the duct N-deficit left with the SHF budget.  It is the
        # only N = 77.6 P/T + 3.73e5 e/T^2 form allowed, and it lives in
        # addons/atmos as the refractivity model, not here.
        for path in RADIO.rglob("*.sqf"):
            text = path.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("3.73e5", text, f"{path.name} computes a duct N-deficit")


class TestSingleDiffractionPath(unittest.TestCase):
    """Issue #308: the excess-loss path subtracts no diffraction term.

    fnc_calculateTerrainMaskedLink and fnc_calculateEmPropagation both return
    the ITU-R P.526 Deygout kernel.  Subtracting either from an ACRE2/TFAR
    link that already computes its own terrain loss doubled the loss.
    """

    def test_the_budget_names_no_diffraction_kernel(self):
        src = PROPAGATION.read_text(encoding="utf-8")
        for token in (
            "calculateTerrainMaskedLink",
            "calculateEmPropagation",
            "calculateDeygoutDiffraction",
            "calculateTerrainDiffraction",
            "_terrainLoss",
            "_linkBudget",
        ):
            self.assertNotIn(token, src)

    def test_the_terrain_kernel_still_exists_for_its_own_consumers(self):
        # The kernels are kept as the public per-link API; only the budget
        # term is gone.  Removing them would break a consumer; leaving the
        # term would double the loss.
        self.assertTrue(
            (RADIO / "functions" / "fnc_calculateTerrainMaskedLink.sqf").is_file()
        )
        self.assertTrue(
            (RADIO / "functions" / "fnc_calculateEmPropagation.sqf").is_file()
        )
        prep = (RADIO / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(calculateTerrainMaskedLink)", prep)


if __name__ == "__main__":
    unittest.main()
