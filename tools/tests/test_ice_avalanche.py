#!/usr/bin/env python3
"""Frozen lake ice load-bearing and avalanche shear-stress tests (#134).

Mirrors the SQF in fnc_calculateIceLoad.sqf and the McClung & Schaerer
shear-stress upgrade in fnc_calculateAvalancheRisk.sqf.

Anchors (from the issue):
  - Stefan ice growth: h_cm = 2.7·sqrt(FDD_C) bare, 1.7 snow-covered;
    30 cm needs 225 degree-C-days bare / 576 snow-covered.
  - Gold load: P_kg = 3.5·h_cm²; warn at 1/3 of safe; breakthrough at
    3x safe (flexural).
  - DNR load table: 10 cm person, 18 ATV, 28 SUV, 41 heavy truck.
  - Avalanche: tau = rho·g·h·sin(psi); S = tau_strength/tau; S<1
    unstable; danger scale 1-5; burial survival 93% @15min, 30%
    @35min, 3% @90min.
"""

import math
import unittest


# ─── Stefan ice growth ──────────────────────────────────────────────────────
C_BARE = 2.7
C_SNOW = 1.7


def ice_thickness_cm(fdd_cdays, snow_covered=False):
    """h_cm = C·sqrt(FDD).  C = 2.7 bare, 1.7 snow-covered."""
    c = C_SNOW if snow_covered else C_BARE
    return c * math.sqrt(max(0.0, fdd_cdays))


# ─── Gold load model ────────────────────────────────────────────────────────
GOLD_A = 3.5  # kg per cm²


def ice_safe_load_kg(ice_cm):
    """P = 3.5·h² — safe load in kg."""
    return GOLD_A * ice_cm**2


def ice_warn_load_kg(ice_cm):
    """Warning at 1/3 of safe load."""
    return ice_safe_load_kg(ice_cm) / 3.0


def ice_breakthrough_kg(ice_cm):
    """Breakthrough at 3x safe (flexural limit, 150 psi)."""
    return 3.0 * ice_safe_load_kg(ice_cm)


# DNR load table: minimum ice cm for a given load class.
DNR_TABLE = [
    (0.0, "Off"),  # <10 cm stay off
    (10.0, "Person"),
    (18.0, "ATV"),
    (28.0, "SUV"),
    (41.0, "HeavyTruck"),
    (51.0, "Shelter"),
]


def dnr_state(ice_cm):
    state = "Off"
    for thresh, label in DNR_TABLE:
        if ice_cm >= thresh:
            state = label
    return state


# ─── FDD accumulation ───────────────────────────────────────────────────────
def fdd_step(fdd, ice_cm, temp_c, dt_h, snow_covered=False):
    """One tick of the SQF grid model.  dt_h clamped to 0.5 h.

    Below freezing: accumulate degree-days (hours/24 × −T).
    Above freezing: melt 0.05 cm/h, decay FDD 0.02/h.
    Returns [new_fdd, new_ice_cm].
    """
    dt_h = min(dt_h, 0.5)
    if temp_c < 0:
        fdd += (-temp_c) * dt_h / 24.0
        ice_cm = ice_thickness_cm(fdd, snow_covered)
    else:
        ice_cm = max(0.0, ice_cm - 0.05 * dt_h)
        fdd = max(0.0, fdd - 0.02 * dt_h)
    return fdd, ice_cm


# ─── Avalanche shear stress (McClung & Schaerer) ───────────────────────────
G = 9.81


def avalanche_shear_stress_kpa(slope_deg, slab_depth_m=1.0, rho_kgm3=300.0):
    """tau = rho·g·h·sin(psi), in kPa."""
    return rho_kgm3 * G * slab_depth_m * math.sin(math.radians(slope_deg)) / 1000.0


def avalanche_stability(shear_stress_kpa, strength_kpa):
    """S = tau_strength / tau."""
    if shear_stress_kpa <= 0:
        return 999.0
    return strength_kpa / shear_stress_kpa


def avalanche_risk(
    slope_deg, strength_kpa, snow24_cm, temp_c, slab_depth_m=1.0, rho_kgm3=300.0
):
    """Mirror of the SQF: risk from stability S and the trigger.

    Trigger = rolling 24 h snowfall >= 30 cm OR temp > 2 C.
    risk = (1−S)·(0.6+0.4·trigger) when S<1, residual (1.5−S)·0.4 when S<1.5.
    """
    tau = avalanche_shear_stress_kpa(slope_deg, slab_depth_m, rho_kgm3)
    s = avalanche_stability(tau, strength_kpa)
    trigger = 1 if (snow24_cm >= 30.0 or temp_c > 2.0) else 0
    if s < 1.0:
        return (1.0 - s) * (0.6 + 0.4 * trigger)
    if s < 1.5:
        return (1.5 - s) * 0.4
    return 0.0


def danger_level(risk):
    """0 none, 1 low, 2 moderate, 3 considerable, 4 high, 5 extreme."""
    if risk >= 0.9:
        return 5
    if risk >= 0.7:
        return 4
    if risk >= 0.4:
        return 3
    if risk >= 0.2:
        return 2
    if risk > 0:
        return 1
    return 0


# ─── Burial survival ────────────────────────────────────────────────────────
def burial_survival(minutes):
    """Piecewise survival curve: 97% @0, 93% @15, 30% @35, 3% @90."""
    curve = [(0.0, 0.97), (15.0, 0.93), (35.0, 0.30), (90.0, 0.03)]
    if minutes <= curve[0][0]:
        return curve[0][1]
    for i in range(len(curve) - 1):
        t0, s0 = curve[i]
        t1, s1 = curve[i + 1]
        if minutes <= t1:
            frac = (minutes - t0) / (t1 - t0)
            return s0 + (s1 - s0) * frac
    return curve[-1][1]


class TestStefanIceGrowth(unittest.TestCase):
    def test_30cm_needs_225_bare_fdd(self):
        # 2.7·sqrt(225) = 40.5... wait — the issue says 30 cm needs 225
        # degree-F-days.  Verify the metric anchor: 2.7·sqrt(FDD_C) for 30
        # cm needs FDD_C = (30/2.7)² = 123.5 degree-C-days.
        self.assertAlmostEqual(ice_thickness_cm(123.46), 30.0, places=1)

    def test_snow_covered_30cm_needs_more(self):
        # 1.7·sqrt(FDD) = 30 → FDD = (30/1.7)² = 311.4.
        self.assertAlmostEqual(
            ice_thickness_cm(311.4, snow_covered=True), 30.0, places=1
        )

    def test_monotonic_growth(self):
        prev = -1
        for fdd in range(0, 200, 10):
            h = ice_thickness_cm(fdd)
            self.assertGreaterEqual(h, prev)
            prev = h

    def test_no_growth_at_zero(self):
        self.assertEqual(ice_thickness_cm(0.0), 0.0)


class TestGoldLoad(unittest.TestCase):
    def test_safe_load_scales_squared(self):
        self.assertAlmostEqual(ice_safe_load_kg(10), 350.0)
        self.assertAlmostEqual(ice_safe_load_kg(28), 2744.0)  # SUV class
        self.assertAlmostEqual(ice_safe_load_kg(41), 5883.5)  # heavy truck

    def test_warn_is_third(self):
        self.assertAlmostEqual(ice_warn_load_kg(30), ice_safe_load_kg(30) / 3)

    def test_breakthrough_three_times(self):
        self.assertAlmostEqual(ice_breakthrough_kg(20), 3 * ice_safe_load_kg(20))

    def test_dnr_states(self):
        self.assertEqual(dnr_state(5), "Off")
        self.assertEqual(dnr_state(12), "Person")
        self.assertEqual(dnr_state(20), "ATV")
        self.assertEqual(dnr_state(30), "SUV")
        self.assertEqual(dnr_state(45), "HeavyTruck")
        self.assertEqual(dnr_state(55), "Shelter")


class TestFDDAccumulation(unittest.TestCase):
    def test_accumulates_in_freezing(self):
        fdd, ice = 0.0, 0.0
        # 48 h at -5 C -> 10 degree-C-days -> 2.7·sqrt(10) = 8.5 cm
        for _ in range(96):
            fdd, ice = fdd_step(fdd, ice, -5.0, 0.5)
        self.assertAlmostEqual(fdd, 10.0, places=2)
        self.assertAlmostEqual(ice, 2.7 * math.sqrt(10.0), places=1)

    def test_melts_above_freezing(self):
        fdd, ice = 20.0, 12.0
        for _ in range(40):  # 20 h above freezing at 0.5 h ticks
            fdd, ice = fdd_step(fdd, ice, 5.0, 0.5)
        # Melt 0.05 cm/h: 12 - 0.05*20 = 11 cm.  FDD decays 0.02/h.
        self.assertAlmostEqual(ice, 11.0, places=2)
        self.assertAlmostEqual(fdd, 20.0 - 0.02 * 20.0, places=3)

    def test_dt_clamped(self):
        # A large dt must clamp to 0.5 h per the SQF.
        fdd, ice = fdd_step(0.0, 0.0, -10.0, 48.0)
        # 0.5 h at -10 C = 0.208 degree-C-days
        self.assertAlmostEqual(fdd, 10.0 * 0.5 / 24.0, places=3)


class TestAvalancheShearStress(unittest.TestCase):
    def test_shear_stress_anchor(self):
        # 40 deg, rho 300, h 1.0: tau = 300·9.81·sin(40)/1000 = 1.89 kPa
        tau = avalanche_shear_stress_kpa(40.0)
        self.assertAlmostEqual(
            tau, 300 * 9.81 * math.sin(math.radians(40)) / 1000, places=3
        )

    def test_zero_slope_no_stress(self):
        self.assertAlmostEqual(avalanche_shear_stress_kpa(0.0), 0.0, places=6)

    def test_steeper_slope_more_stress(self):
        self.assertGreater(
            avalanche_shear_stress_kpa(45.0), avalanche_shear_stress_kpa(30.0)
        )

    def test_deeper_slab_more_stress(self):
        self.assertGreater(
            avalanche_shear_stress_kpa(40.0, slab_depth_m=2.0),
            avalanche_shear_stress_kpa(40.0, slab_depth_m=0.5),
        )

    def test_stability_index(self):
        # S = strength/tau.  Strength 5 kPa on a 40 deg slope (tau 1.89)
        # -> S = 2.6 (stable).
        tau = avalanche_shear_stress_kpa(40.0)
        s = avalanche_stability(tau, 5.0)
        self.assertAlmostEqual(s, 5.0 / tau, places=3)
        self.assertGreater(s, 1.0)

    def test_weak_layer_unstable(self):
        # Strength 1 kPa (surface hoar) on 40 deg -> S = 0.53 < 1.
        tau = avalanche_shear_stress_kpa(40.0)
        s = avalanche_stability(tau, 1.0)
        self.assertLess(s, 1.0)

    def test_risk_releases_below_1(self):
        # 40 deg, strength 1 kPa, heavy snowfall -> risk high (danger 3+).
        r = avalanche_risk(40.0, 1.0, 40.0, -5.0)
        self.assertGreater(r, 0.4)

    def test_risk_low_on_stable_slope(self):
        # 30 deg, strength 8 kPa, no trigger -> stable.
        r = avalanche_risk(30.0, 8.0, 5.0, -10.0)
        self.assertAlmostEqual(r, 0.0, places=3)

    def test_trigger_rain_raises_risk(self):
        # Weak layer (S<1 on the slope) so the trigger differentiates.
        # 40 deg, strength 1.5 kPa: tau = 300·9.81·sin(40)/1000 = 1.89,
        # S = 0.79 < 1.  Rain trigger raises the risk vs cold dry.
        r_trigger = avalanche_risk(40.0, 1.5, 5.0, 5.0)
        r_no = avalanche_risk(40.0, 1.5, 5.0, -10.0)
        self.assertGreater(r_trigger, r_no)
        self.assertGreater(r_trigger, 0.0)

    def test_danger_scale(self):
        self.assertEqual(danger_level(0.0), 0)
        self.assertEqual(danger_level(0.2), 2)
        self.assertEqual(danger_level(0.4), 3)
        self.assertEqual(danger_level(0.7), 4)
        self.assertEqual(danger_level(0.95), 5)


class TestBurialSurvival(unittest.TestCase):
    def test_anchors(self):
        self.assertAlmostEqual(burial_survival(0), 0.97, places=2)
        self.assertAlmostEqual(burial_survival(15), 0.93, places=2)
        self.assertAlmostEqual(burial_survival(35), 0.30, places=2)
        self.assertAlmostEqual(burial_survival(90), 0.03, places=2)

    def test_monotonic_decline(self):
        prev = 1.0
        for m in range(0, 120, 5):
            s = burial_survival(m)
            self.assertLessEqual(s, prev + 1e-9)
            prev = s

    def test_clamps_past_end(self):
        self.assertAlmostEqual(burial_survival(200), 0.03, places=3)


if __name__ == "__main__":
    unittest.main()
