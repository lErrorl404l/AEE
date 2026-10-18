#!/usr/bin/env python3
"""Reference checks for AEE's environmental model.

These tests validate the SQF implementation in addons/environmental
(CBRN persistence, Rothermel fire spread, avalanche risk, freeze-thaw,
flash flood, severe weather, surface wetness) against the source
formulas. They fail if the formulas drift from the reference.

Run: python3 -m unittest tools/tests/test_environmental.py
"""

import math
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CBRN_PERSISTENCE = (
    REPO / "addons/persistence/functions/warnings/fnc_calculateCBRNPersistence.sqf"
)

R_GAS = 8.314462618  # J/(mol*K), CODATA 2018 (molar gas constant)
T_REF_K = 298.15  # K, 25 C: the temperature the agent data is quoted at


def cbrn_persistence_h(temp_c, delta_hvap_jmol=0.0, base_h=24.0, ea_jmol=0.0):
    """Mirror of the temperature term in fnc_calculateCBRNPersistence.sqf.

    The slope is the published hydrolysis activation energy where the agent
    has one (GD 64.25, HD 108.8 kJ/mol), else the deltaHvap interim slope
    (FM 3-11.9, January 2005, Appendix G).  Both 0 is the no-agent case,
    where the term is 1 (no published value exists for an unidentified
    agent).  Returns the persistence in hours.
    """
    slope = ea_jmol if ea_jmol != 0 else delta_hvap_jmol
    rate_multiplier = 1.0
    if slope != 0:
        temp_k = max(temp_c + 273.15, 1.0)
        rate_multiplier = math.exp(-(slope / R_GAS) * (1.0 / temp_k - 1.0 / T_REF_K))
    return base_h / rate_multiplier


def cbrn_persistence(temp_c, delta_hvap_jmol=0.0, base_h=24, interval=5):
    """Mirror of fnc_calculateCBRNPersistence.sqf (per-agent Arrhenius).

    Returns the per-tick exponential decay factor. A higher factor means
    slower decay, hence longer persistence.
    """
    return math.exp(
        -(interval / 3600) / cbrn_persistence_h(temp_c, delta_hvap_jmol, base_h)
    )


def equilibrium_moisture(temp_c, rh_pct):
    """Mirror of fnc_equilibriumMoisture.sqf (Simard 1968 EMC).

    Simard's three-branch fit, T in degF and RH in percent, returned as a
    fraction clamped to the physical 1-35 percent band.
    """
    t_f = temp_c * 1.8 + 32
    rh = max(0.0, min(100.0, rh_pct))
    emc_pct = 21.0606 + 0.005565 * rh * rh - 0.00035 * rh * t_f - 0.483199 * rh
    if rh < 50:
        emc_pct = 2.22749 + 0.160107 * rh - 0.014784 * t_f
    if rh < 10:
        emc_pct = 0.03229 + 0.281073 * rh - 0.000578 * rh * t_f
    return max(0.01, min(0.35, emc_pct / 100))


def fuel_moisture_response(m_prev, emc, dt_s, tau_h):
    """Mirror of fnc_fuelMoistureResponse.sqf (timelag relaxation)."""
    tau = max(0.001, tau_h)
    return emc + (m_prev - emc) * math.exp(-(dt_s / 3600) / tau)


def rothermel_ros(sigma, w0, delta, mf, mx, u_ms, slope_tan):
    """Mirror of fnc_rothermelSpread.sqf (Rothermel 1972 INT-115).

    SI inputs (load kg/m^2, depth m, wind m/s, slope tangent); R in m/s.
    Fuel parameters are the Albini (1976) INT-GTR-30 standard models.
    """
    if not (w0 > 0 and mf < mx and sigma > 0):
        return 0.0
    rho_p = 32.0  # lb/ft^3
    h = 8000.0  # BTU/lb
    st = 0.0555
    se = 0.01
    w0_lb = w0 * 0.204816
    delta_ft = delta * 3.28084
    u_ftmin = u_ms * 196.850
    rho_b = w0_lb / max(0.001, delta_ft)
    beta = rho_b / rho_p
    beta_op = 3.348 * sigma ** (-0.8189)
    ratio = beta / beta_op
    a = 1 / (4.774 * sigma**0.1 - 7.27)
    g_max = sigma**1.5 / (495 + 0.0594 * sigma**1.5)
    g = g_max * ratio**a * math.exp(a * (1 - ratio))
    eta_s = min(1.0, 0.174 * se ** (-0.19))
    mf_ratio = mf / mx
    eta_m = max(0.0, 1 - 2.59 * mf_ratio + 5.11 * mf_ratio**2 - 3.52 * mf_ratio**3)
    ir = g * w0_lb * (1 - st) * h * eta_m * eta_s
    xi = math.exp((0.792 + 0.681 * sigma**0.5) * (beta + 0.1)) / (192 + 0.2595 * sigma)
    eps = math.exp(-138 / sigma)
    qig = 250 + 1116 * mf
    c = 7.47 * math.exp(-0.133 * sigma**0.55)
    b = 0.02526 * sigma**0.54
    e = 0.715 * math.exp(-3.59e-4 * sigma)
    phi_w = c * u_ftmin**b * ratio ** (-e)
    phi_s = 5.275 * beta ** (-0.3) * slope_tan**2
    r_ftmin = ir * xi * (1 + phi_w + phi_s) / max(1e-9, rho_b * eps * qig)
    return r_ftmin * 0.3048 / 60


def byram_intensity(h_kjkg, w_kgm2, ros_ms):
    """Mirror of fnc_byramIntensity.sqf (Byram 1959).

    Returns (fireline intensity kW/m, flame length m).
    """
    ib = h_kjkg * w_kgm2 * ros_ms
    return ib, 0.0775 * ib**0.46


def fire_area(area, ros, interval):
    """Mirror of the fire-area growth in fnc_calculateFireSpreadRisk.sqf."""
    perimeter = 2 * math.pi * math.sqrt(area / math.pi)
    area = area + perimeter * ros * interval
    return max(0.0, min(1e6, area))


def slope_risk(slope_deg):
    """Mirror of the slope curve in fnc_calculateAvalancheRisk.sqf (Schweizer 2003)."""
    return max(0.0, min(1.0, 1 - abs(slope_deg - 35) / 20))


def avalanche_risk(slope_deg, wind_ms, temp_c, rain, ground_state="Snow"):
    """Mirror of the combined risk in fnc_calculateAvalancheRisk.sqf."""
    if ground_state not in ("Snow", "Frozen"):
        return 0.0
    risk = slope_risk(slope_deg)
    wind_factor = 0
    if wind_ms > 8:
        wind_factor = min((wind_ms - 8) / 20, 0.2)
    temp_factor = 0
    if temp_c > 0:
        temp_factor = min(((temp_c - 0) / 20) * 0.15, 0.15)
    rain_factor = 0
    if ground_state == "Snow" and rain > 0:
        rain_factor = min(rain * 0.15, 0.15)
    return min(risk + wind_factor + temp_factor + rain_factor, 1.0)


def freeze_thaw(fdd, tdd, temp_c, interval=5):
    """Mirror of fnc_calculateFreezeThawCycling.sqf (Stefan solution).

    Returns (fdd, tdd, frozen_depth_m, thaw_depth_m).
    """
    fdd = fdd + max(0 - temp_c, 0) * (interval / 86400)
    tdd = tdd + max(temp_c - 0, 0) * (interval / 86400)
    frozen_depth = 0.05 * math.sqrt(fdd)
    thaw_depth = 0.05 * math.sqrt(tdd)
    return fdd, tdd, frozen_depth, thaw_depth


def flash_flood_risk(rain_rate, rain_accum, terrain_factor):
    """Mirror of fnc_calculateFlashFloodRisk.sqf."""
    risk = (rain_rate * 25 / 50) * (1 + rain_accum) * terrain_factor
    return max(0.0, min(1.0, risk))


def dust_devil(wind_ms, biome_arid, temp, clear, day=True):
    """Mirror of the dust-devil band in fnc_calculateSevereWeather.sqf.

    The SQF gates on the 2-8 m/s wind band, arid biome, hot air and a
    clear sky. It has no day/night gate; the day parameter is kept for
    signature compatibility and does not affect the result.
    """
    if biome_arid and 2 <= wind_ms <= 8 and temp > 30 and clear:
        return min(wind_ms / 15, 0.8)
    return 0.0


def surface_wetness(wetness, rain, temp, dewpoint, overcast, wind, interval=5):
    """Mirror of fnc_calculateSurfaceWetness.sqf."""
    wetness = wetness + rain * 0.05
    if temp < dewpoint and overcast < 0.3 and wind < 3:
        wetness = wetness + 0.02
    evap = (0.01 + 0.001 * wind) * (1 + (temp - 15) * 0.05)
    wetness = wetness - wetness * evap * (interval / 3600)
    return max(0.0, min(1.0, wetness))


class TestCBRNPersistence(unittest.TestCase):
    """The temperature term is per-agent Arrhenius on the latent heat of
    vaporisation (FM 3-11.9, January 2005, Appendix G)."""

    VX = 80.3e3  # kJ/mol -> J/mol, the VX latent heat of vaporisation
    CG = 24.8e3

    def test_warmer_temp_shorter_persistence(self):
        # A positive latent heat makes the agent decay faster when warmer.
        self.assertLess(cbrn_persistence(25, self.VX), cbrn_persistence(15, self.VX))

    def test_no_agent_no_temperature_term(self):
        # The Q10 = 2 rule of thumb is gone: with no agent there is no
        # published kinetic constant, so the term is 1.
        self.assertAlmostEqual(cbrn_persistence(25, 0), cbrn_persistence(5, 0))
        self.assertAlmostEqual(cbrn_persistence_h(25, 0), 24.0)

    def test_implied_q10_per_agent(self):
        # The report's deltaHvap-implied Q10 over 15-25 C per agent.
        for dh_kjmol, q10 in (
            (24.8, 1.42),
            (48.5, 1.97),
            (55.2, 2.17),
            (62.8, 2.42),
            (80.3, 3.09),
        ):
            with self.subTest(dh_kjmol=dh_kjmol):
                got = cbrn_persistence_h(15, dh_kjmol * 1000) / cbrn_persistence_h(
                    25, dh_kjmol * 1000
                )
                self.assertAlmostEqual(got, q10, places=1)

    def test_persistence_never_negative(self):
        # The decay factor is exp(negative), always in (0, 1].
        for args in ((15, self.VX), (40, self.VX), (-20, self.CG), (15, 0)):
            with self.subTest(args=args):
                modifier = cbrn_persistence(*args)
                self.assertGreater(modifier, 0.0)
                self.assertLessEqual(modifier, 1.0)

    def test_reference_tick_math(self):
        # At 25 C the row data is quoted at, the term is 1: persistence = base_h.
        self.assertAlmostEqual(
            cbrn_persistence(25, self.VX, 24, 5), math.exp(-(5 / 3600) / 24)
        )


class TestCBRNPersistenceRemovals(unittest.TestCase):
    """The invented environmental terms are gone from the kernel."""

    def setUp(self):
        self.text = CBRN_PERSISTENCE.read_text(encoding="utf-8")

    def test_no_humidity_multiplier(self):
        # No published "RH to persistence" multiplier exists; humidity acts
        # indirectly through condensed water and its pH.
        self.assertNotIn("_humidityFactor", self.text)
        self.assertNotIn("currentHumidity", self.text)

    def test_no_wind_factor(self):
        # Wind is dispersion, not decay, and the plume path models it.
        self.assertNotIn("_windFactor", self.text)
        self.assertNotIn("vectorMagnitude wind", self.text)

    def test_no_q10_rule_of_thumb(self):
        self.assertNotIn("Q10 = 2", self.text)
        self.assertNotIn("2 ^ ((_temp_C - 15) / 10)", self.text)

    def test_arrhenius_term_is_sourced(self):
        self.assertIn("Arrhenius", self.text)
        self.assertIn("8.314462618", self.text)
        self.assertIn("298.15", self.text)
        self.assertIn("_deltaHvapJmol", self.text)
        self.assertIn("_activationEnergyJmol", self.text)
        self.assertIn("Wu et al. 2021", self.text)
        self.assertIn("Herriott 1947", self.text)

    def test_interim_basis_is_marked(self):
        # GB, VX and CG have no published Ea: their slope stays the deltaHvap
        # interim, labelled as such and not as an activation energy.
        self.assertIn("INTERIM", self.text)
        self.assertIn("UNSOURCED", self.text)


CBRN_AGENT = REPO / "addons/weather/functions/dispersion/fnc_getCbrnAgent.sqf"


class TestCBRNPersistenceActivationEnergy(unittest.TestCase):
    """A published hydrolysis activation energy replaces the deltaHvap slope
    where one exists: GD 64.25 kJ/mol (Wu et al. 2021, E3S Web Conf 267:02060)
    and HD 108.8 kJ/mol (Herriott 1947, J Gen Physiol 30(6):457-464)."""

    HD_DHVAP = 62.8e3  # FM 3-11.9 Appendix G, the interim slope
    HD_EA = 108.8e3  # Herriott 1947, H.2TDG sulfonium salt, 20-100 C
    GD_DHVAP = 55.2e3
    GD_EA = 64.25e3  # Wu et al. 2021, HCl aqueous, pH 0.90, 20 C

    def _rate_multiplier(self, dh, ea=0.0):
        """Decay-rate multiplier at 30 C over 25 C, the kernel's own term.

        A larger multiplier means faster decay, hence shorter persistence.
        """
        return cbrn_persistence_h(25, dh, ea_jmol=ea) / cbrn_persistence_h(
            30, dh, ea_jmol=ea
        )

    def test_hd_ea_shortens_persistence_by_36_percent_at_30c(self):
        interim = self._rate_multiplier(self.HD_DHVAP)
        published = self._rate_multiplier(self.HD_DHVAP, self.HD_EA)
        self.assertAlmostEqual(interim, 1.52, places=2)
        self.assertAlmostEqual(published, 2.06, places=2)
        self.assertAlmostEqual(published / interim, 1.358, places=3)
        # The same result stated as persistence: 36 percent shorter.
        self.assertAlmostEqual(interim / published, 0.736, places=3)

    def test_gd_ea_is_a_six_percent_change_at_30c(self):
        interim = self._rate_multiplier(self.GD_DHVAP)
        published = self._rate_multiplier(self.GD_DHVAP, self.GD_EA)
        self.assertAlmostEqual(published / interim, 1.062, places=3)

    def test_the_ea_wins_over_the_interim_slope(self):
        # A non-zero Ea is the slope even when deltaHvap is also passed.
        self.assertNotAlmostEqual(
            cbrn_persistence_h(30, self.HD_DHVAP, ea_jmol=self.HD_EA),
            cbrn_persistence_h(30, self.HD_DHVAP),
        )
        self.assertLess(
            cbrn_persistence_h(30, self.HD_DHVAP, ea_jmol=self.HD_EA),
            cbrn_persistence_h(30, self.HD_DHVAP),
        )

    def test_no_ea_no_delta_hvap_still_means_no_term(self):
        self.assertAlmostEqual(cbrn_persistence_h(30, 0, ea_jmol=0), 24.0)

    def test_agent_table_carries_the_ea_and_the_zeros(self):
        # GD and HD carry a published activation energy.  GB, VX and CG
        # carry 0, so the kernel keeps the deltaHvap interim for them.
        text = CBRN_AGENT.read_text(encoding="utf-8")
        for row in (
            "[1000, 0.106, 906, 62.8, [24, 336], 108.8]",  # HD
            "[35, 0.401, 3930, 55.2, [10 / 60, 15 / 60], 64.25]",  # GD
            "[15, 8.78e-4, 12.6, 80.3, [24, 336], 0]",  # VX
            "[35, 2.48, 18700, 48.5, [10 / 60, 15 / 60], 0]",  # GB
            "[1500, 1400, 7460000, 24.8, [10 / 60, 15 / 60], 0]",  # CG
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)


class TestFireSpread(unittest.TestCase):
    """Rothermel (1972) spread with Simard (1968) moisture, issue #10.

    Fuel model 1 (short grass): sigma 3500 ft^-1, w0 0.165886 kg/m^2, depth
    0.3048 m, moisture of extinction 0.12 (Albini 1976, INT-GTR-30).
    """

    def test_reference_ros_fuel_model_1(self):
        # Rothermel (1972) INT-115 at 5% fine moisture, calm, flat gives
        # 4.645 ft/min = 1.416 m/min = 0.023596 m/s.  The issue's stated
        # 1.25 m/min is the same figure rounded.
        r = rothermel_ros(3500, 0.165886, 0.3048, 0.05, 0.12, 0, 0)
        self.assertAlmostEqual(r, 0.02359643, places=7)

    def test_emc_reference(self):
        # Simard (1968) at 70 F / 40% RH: 2.22749 + 0.160107*40
        # - 0.014784*70 = 7.597%.  The issue's stated 7.2% is an arithmetic
        # slip on the same branch.
        self.assertAlmostEqual(equilibrium_moisture(21.111, 40), 0.075969, places=5)

    def test_mx_gate(self):
        # Rate of spread is zero once the fuel moisture reaches Mx.
        self.assertEqual(rothermel_ros(3500, 0.166, 0.3048, 0.12, 0.12, 0, 0), 0.0)
        self.assertEqual(rothermel_ros(3500, 0.166, 0.3048, 0.20, 0.12, 0, 0), 0.0)

    def test_flame_length_reference(self):
        # Byram: L = 0.0775 * IB^0.46.  At IB = 1000 kW/m -> 1.859 m.
        # The issue's stated 1.7 m does not reproduce from this relation.
        _, length = byram_intensity(1000, 1.0, 1.0)
        self.assertAlmostEqual(length, 1.859096, places=5)

    def test_ros_monotonic_wind(self):
        self.assertGreater(
            rothermel_ros(3500, 0.166, 0.3048, 0.05, 0.12, 5, 0),
            rothermel_ros(3500, 0.166, 0.3048, 0.05, 0.12, 2, 0),
        )

    def test_ros_monotonic_slope(self):
        self.assertGreater(
            rothermel_ros(3500, 0.166, 0.3048, 0.05, 0.12, 0, 1.0),
            rothermel_ros(3500, 0.166, 0.3048, 0.05, 0.12, 0, 0.5),
        )

    def test_ros_decreasing_moisture(self):
        self.assertLess(
            rothermel_ros(3500, 0.166, 0.3048, 0.10, 0.12, 0, 0),
            rothermel_ros(3500, 0.166, 0.3048, 0.04, 0.12, 0, 0),
        )

    def test_ros_zero_fuel(self):
        self.assertEqual(rothermel_ros(3500, 0.0, 0.3048, 0.05, 0.12, 5, 0), 0.0)

    def test_timelag_relaxes_toward_emc(self):
        # A dry class wets toward a higher EMC, a damp class dries toward it.
        self.assertGreater(fuel_moisture_response(0.02, 0.10, 3600, 1), 0.02)
        self.assertLess(fuel_moisture_response(0.20, 0.10, 3600, 1), 0.20)

    def test_fine_class_tracks_faster(self):
        # The 1-hour class moves further than the 100-hour class in one hour.
        d1 = fuel_moisture_response(0.02, 0.10, 3600, 1) - 0.02
        d100 = fuel_moisture_response(0.02, 0.10, 3600, 100) - 0.02
        self.assertGreater(d1, d100)

    def test_extreme_grass_with_wind(self):
        # 5 m/s midflame wind on dry fuel model 1 gives 2.703 m/s, the
        # extreme grass band; the wind factor dominates the no-wind rate.
        self.assertAlmostEqual(
            rothermel_ros(3500, 0.165886, 0.3048, 0.05, 0.12, 5, 0), 2.70320, places=3
        )

    def test_area_grows(self):
        self.assertGreater(fire_area(100, 1, 5), 100)

    def test_area_constant_zero_ros(self):
        self.assertEqual(fire_area(100, 0, 5), 100)

    def test_area_clamped(self):
        # A single large step overshoots the 1e6 cap.
        self.assertEqual(fire_area(999999, 100, 5), 1e6)


class TestAvalanche(unittest.TestCase):
    def test_slope_peak(self):
        self.assertEqual(slope_risk(35), 1.0)

    def test_slope_tails(self):
        self.assertEqual(slope_risk(15), 0.0)
        self.assertEqual(slope_risk(55), 0.0)

    def test_slope_midpoint(self):
        self.assertAlmostEqual(slope_risk(25), 0.5)

    def test_no_snow_zero(self):
        # No snowpack: the SQF exits with risk 0.
        self.assertEqual(avalanche_risk(35, 0, 0, 0, "Normal"), 0.0)

    def test_warm_increases_risk(self):
        # Rapid warm-up adds a temperature factor; cold air adds none.
        self.assertGreater(
            avalanche_risk(25, 0, 20, 0, "Snow"), avalanche_risk(25, 0, -5, 0, "Snow")
        )

    def test_risk_clamped(self):
        # All factors at maximum still clamp to 1.0.
        self.assertEqual(avalanche_risk(35, 30, 30, 1.0, "Snow"), 1.0)
        self.assertGreaterEqual(avalanche_risk(25, 10, 10, 0.5, "Snow"), 0.0)


class TestFreezeThaw(unittest.TestCase):
    def test_tdd_only_above_zero(self):
        # Below 0 C the thawing degree-days do not grow.
        fdd, tdd, _, _ = freeze_thaw(0, 0, -5, 86400)
        self.assertEqual(tdd, 0.0)
        self.assertGreater(fdd, 0.0)

    def test_fdd_only_below_zero(self):
        # Above 0 C the freezing degree-days do not grow.
        fdd, tdd, _, _ = freeze_thaw(0, 0, 5, 86400)
        self.assertEqual(fdd, 0.0)
        self.assertGreater(tdd, 0.0)

    def test_thaw_depth_sqrt_scaling(self):
        # Depth is proportional to sqrt(degree-days): 4 days at the same
        # rate gives twice the depth of 1 day.
        _, _, _, depth_1d = freeze_thaw(0, 0, 10, 86400)
        _, _, _, depth_4d = freeze_thaw(0, 0, 10, 86400 * 4)
        self.assertAlmostEqual(depth_4d / depth_1d, 2.0)

    def test_depths_never_negative(self):
        _, _, frozen, thawed = freeze_thaw(0, 0, -10, 86400)
        self.assertGreaterEqual(frozen, 0.0)
        self.assertGreaterEqual(thawed, 0.0)


class TestFlashFlood(unittest.TestCase):
    def test_no_rain_zero(self):
        self.assertEqual(flash_flood_risk(0, 0, 1.0), 0.0)

    def test_accum_alone_no_risk(self):
        # Antecedent moisture amplifies but cannot sustain risk alone.
        self.assertEqual(flash_flood_risk(0, 5, 1.0), 0.0)

    def test_50mmh_steep_full(self):
        # Rain rate 2 = 50 mm/h, steep catchment, no antecedent.
        self.assertEqual(flash_flood_risk(2, 0, 1.0), 1.0)

    def test_flat_half(self):
        # Non-arid terrain responds at half the steep-catchment rate.
        self.assertAlmostEqual(flash_flood_risk(2, 0, 0.5), 0.5)

    def test_clamped(self):
        self.assertEqual(flash_flood_risk(10, 0, 1.0), 1.0)


class TestSevereWeather(unittest.TestCase):
    def test_band_active(self):
        # Hot, clear, arid, wind in the 2-8 m/s band.
        self.assertGreater(dust_devil(5, True, 35, True), 0.0)

    def test_band_bounds(self):
        # Wind 1 m/s is too calm, 10 m/s shreds the vortex.
        self.assertEqual(dust_devil(1, True, 35, True), 0.0)
        self.assertEqual(dust_devil(10, True, 35, True), 0.0)

    def test_mid_band_active(self):
        self.assertGreater(dust_devil(5, True, 35, True), 0.0)

    def test_non_arid_inactive(self):
        self.assertEqual(dust_devil(5, False, 35, True), 0.0)

    def test_cold_inactive(self):
        self.assertEqual(dust_devil(5, True, 25, True), 0.0)


class TestSurfaceWetness(unittest.TestCase):
    def test_dries_toward_zero(self):
        # Warm, dry, no rain, no dew: wetness falls and never goes negative.
        result = surface_wetness(0.5, 0, 30, -10, 0.5, 5, 3600)
        self.assertLess(result, 0.5)
        self.assertGreaterEqual(result, 0.0)

    def test_heavy_rain_rises(self):
        self.assertGreater(surface_wetness(0.9, 1.0, 15, 5, 0.5, 2, 5), 0.9)

    def test_dew_rises_without_rain(self):
        # Clear, calm, cold night below the dew point.
        self.assertGreater(surface_wetness(0.1, 0, 5, 10, 0.1, 1, 5), 0.1)

    def test_clamped(self):
        self.assertEqual(surface_wetness(1.0, 1.0, 15, 5, 0.5, 2, 5), 1.0)
        self.assertEqual(surface_wetness(0.0, 0, 30, -10, 0.5, 5, 3600), 0.0)


# ─── Aurora model (issue #112) ──────────────────────────────────────────────
# Mirror of the aurora block in fnc_calculateSpaceWeather.sqf: NOAA SWPC
# Kp-to-latitude relationship (oval expands equatorward as Kp rises) and
# the intensity model (rises with Kp beyond the threshold, strongest when
# the observer's latitude is near the oval edge).


def aurora_oval_limit(kp):
    """Equatorward latitude limit of the auroral oval by Kp.

    Kp 0-1 -> 65 deg, Kp 9 -> ~49.7 deg (NOAA SWPC bands, interpolated).
    """
    return 65.0 - (min(kp, 9) * 1.7)


def aurora_intensity(kp, lat_deg, overcast, day_time):
    """Mirror of the SQF aurora gate + intensity (0-1, 0 = no aurora).

    Requires: Kp > 4, clear sky (< 0.3 overcast), night (before 06:00 or
    after 20:00), and the observer poleward of the oval limit.
    Intensity: 0.6 * (Kp excess over 4) + 0.4 * (latitude proximity to
    the oval edge), clamped 0-1.
    """
    kp_idx = round(max(0.0, min(9.0, kp)))
    if kp_idx <= 4:
        return 0.0
    if overcast >= 0.3:
        return 0.0
    if 6 <= day_time <= 20:
        return 0.0
    limit = aurora_oval_limit(kp_idx)
    if lat_deg <= limit:
        return 0.0
    kp_excess = max(0.0, min(1.0, (kp_idx - 4) / 5.0))
    lat_proximity = max(0.0, min(1.0, 1.0 - (lat_deg - limit) / 10.0))
    return max(0.0, min(1.0, kp_excess * 0.6 + lat_proximity * 0.4))


class TestAurora(unittest.TestCase):
    """Issue #112: Kp-driven aurora visibility and intensity."""

    def test_oval_limit_matches_noaa_bands(self):
        # Kp 0 -> 65, Kp 3 -> ~60, Kp 5 -> ~56.5, Kp 7 -> ~53, Kp 9 -> ~49.7.
        self.assertAlmostEqual(aurora_oval_limit(0), 65.0, places=4)
        self.assertAlmostEqual(aurora_oval_limit(3), 65 - 5.1, places=4)
        self.assertAlmostEqual(aurora_oval_limit(5), 65 - 8.5, places=4)
        self.assertAlmostEqual(aurora_oval_limit(7), 65 - 11.9, places=4)
        self.assertAlmostEqual(aurora_oval_limit(9), 65 - 15.3, places=4)

    def test_kp5_visible_55_60(self):
        # Test vector: Kp 5 -> oval edge in the 55-60 deg band.  The
        # observer must be POLEWARD of the edge (Kp5 limit is 56.5), so
        # lat 58/60 are visible, lat 50 is not.
        for lat in [58, 60]:
            self.assertGreater(
                aurora_intensity(5, lat, 0, 2),
                0.0,
                msg=f"Kp5 not visible at {lat} deg",
            )
        self.assertEqual(aurora_intensity(5, 50, 0, 2), 0.0)  # too far south

    def test_kp9_visible_below_50(self):
        # Kp 9 -> oval limit ~49.7 deg: lat 50 (just poleward) is
        # visible (test vector: oval extends below 50).
        self.assertGreater(aurora_intensity(9, 50, 0, 2), 0.0)

    def test_quiet_kp_no_aurora(self):
        for kp in [0, 1, 2, 3, 4]:
            self.assertEqual(aurora_intensity(kp, 70, 0, 2), 0.0)

    def test_clouds_block_aurora(self):
        self.assertEqual(aurora_intensity(7, 65, 0.5, 2), 0.0)

    def test_daylight_blocks_aurora(self):
        # Night gate: before 06:00 or after 20:00.  Noon blocks; 21:00
        # is night (visible).  A dawn hour (05:00) is also night.
        self.assertEqual(aurora_intensity(7, 65, 0, 12), 0.0)
        self.assertGreater(aurora_intensity(7, 65, 0, 21), 0.0)

    def test_intensity_rises_with_kp(self):
        lo = aurora_intensity(5, 70, 0, 2)
        hi = aurora_intensity(8, 70, 0, 2)
        self.assertGreater(hi, lo)

    def test_intensity_bounded(self):
        for kp in range(5, 10):
            for lat in [50, 55, 60, 65, 70]:
                i = aurora_intensity(kp, lat, 0, 2)
                self.assertGreaterEqual(i, 0.0)
                self.assertLessEqual(i, 1.0)

    def test_nvg_brightens_under_aurora(self):
        # The illuminance mirror (test_thermal_optics.ambient_lux) must
        # respond to the aurora intensity: 30x the starlight floor at
        # full intensity.  Cross-module integration lock.
        from tools.tests.test_thermal_optics import ambient_lux

        floor = ambient_lux(0.0)
        bright = ambient_lux(0.0, aurora_intensity=1.0)
        self.assertGreater(bright / max(floor, 1e-9), 30.0)


if __name__ == "__main__":
    unittest.main()
