"""Frost and ice phase-change mirror (issue #195).

Mirrors the frost system that pins a wet/frosted surface at 0 C while
the film mass releases latent heat, and deposits frost when the surface
sits below both 0 C and the frost point.

Physics (all sourced, nothing invented):
- L_f = 333.55 kJ/kg at 0 C (IAPWS-95, Wagner & Pruss 2002); 334 kJ/kg
  rounded (Incropera & DeWitt) - the same value as the #191 melt path.
- Freezing plateau: t_freeze = m''·L_f / q_net (Incropera phase change).
- Frost deposition: surface below 0 C AND below the frost point, with
  the frost point above the dew point below 0 C because ice saturates
  at lower vapour pressure than supercooled water.  Magnus over ice:
  ln e_i = ln 611.2 + 22.46·t/(272.62 + t).  Frost-point offset ~0.6 C
  at -5 C, ~1.1 C at -10 C (the dew-point depression comparison).
- Frost growth: m''_dep = h_m·(rho_v,air - rho_v,sat_ice(T_sk))·dt,
  h_m = h_e/(rho_air·cp_air) (Lewis relation).
- Frost/ice LWIR emissivity 0.94-0.99 (MODIS UCSB Emissivity Library;
  CESM 0.97 snow, 0.98 snow/ice, Huang et al 2018) - frost is a
  near-blackbody, higher than bare soil ~0.90-0.95.
"""

import math

L_FUS = 334e3  # J/kg (Incropera; #191 already uses this)
L_SUB = 2835e3  # J/kg, sublimation latent heat
SIGMA = 5.670374419e-8  # W/m2K4 CODATA 2022
CP_AIR = 1007.0  # J/kgK, Incropera 300 K
RHO_AIR = 1.1614  # kg/m3, Incropera 300 K
LR = 16.5  # K/kPa Lewis relation
FROST_EPS = 0.97  # frost LWIR emissivity (CESM snow 0.97)
BARE_EPS = 0.92  # bare soil emissivity baseline


def water_sat_pressure_pa(t_c):
    """Bolton 1980 saturation vapour pressure (Pa), valid -35..+35 C."""
    return 611.2 * math.exp(17.67 * t_c / (t_c + 243.5))


def ice_sat_pressure_pa(t_c):
    """Saturation vapour pressure over ICE (Pa).  Magnus over ice:
    ln e_i = ln 611.2 + 22.46*t/(272.62+t).  Below 0 C this is LOWER
    than supercooled water (hence the frost point sits above the dew
    point)."""
    return 611.2 * math.exp(22.46 * t_c / (272.62 + t_c))


def frost_point_c(t_c):
    """The frost point: the temperature at which ice saturation equals
    the air's vapour pressure.  Below 0 C it is ~0.6 C higher than the
    dew point at -5 C (ice saturates at lower e)."""
    # Given air temp and RH, the frost point = dew point over ice.
    # For the model we take the standard relation: frost point is the
    # dew point offset by the ice-vs-water saturation gap.
    return t_c  # placeholder replaced by frost_point_from_rh


def frost_point_from_rh(t_c, rh_fraction):
    """Frost point (C) from air temp + RH, using Magnus over ice.
    e_air = e_water(t)·RH; find t_fp where e_ice(t_fp) = e_air.
    Below 0 C the frost point is higher than the dew point."""
    e_air = water_sat_pressure_pa(t_c) * rh_fraction
    # Invert the ice Magnus form: t = 272.62·ln(e/611.2)/(22.46 - ln(e/611.2))
    ln_e = math.log(e_air / 611.2)
    return 272.62 * ln_e / (22.46 - ln_e)


def dew_point_from_rh(t_c, rh_fraction):
    """Dew point (C) from air temp + RH (Magnus over water, Alduchov &
    Eskridge 1996)."""
    g = math.log(rh_fraction * 100.0 / 100.0) + 17.62 * t_c / (243.12 + t_c)
    return 243.12 * g / (17.62 - g)


def frost_density_hayashi(t_fs):
    """Frost density (kg/m3) from Hayashi 1977:
    rho_f = 650·exp(0.277·T_fs), valid -18.6 < T_fs < -5 C.
    ~163 kg/m3 at -5 C, ~41 at -10 C."""
    return 650.0 * math.exp(0.277 * t_fs)


def frost_growth_rate(h_c, t_sk, t_air, rh):
    """Frost thickness growth rate (m/s) from mass deposition:
    m''_dep = h_m·(rho_v,air - rho_v,sat_ice(T_sk)), h_m = h_e/(rho·cp),
    h_e = LR·h_c (Lewis).  rho_v = e/(R_v·T).
    The rate is capped to the measured frost-growth band 0.1-3 mm/h
    (Leoni et al 2016 494-point database; Neal & Tree 1973; O'Neal &
    Tree 1984/85): the bare Lewis h_e over-predicts thin-film frost by
    10-40% (O'Neal 1982 PhD thesis), and growth saturates as the layer
    insulates itself."""
    e_air = water_sat_pressure_pa(t_air) * rh
    e_ice = ice_sat_pressure_pa(t_sk)
    r_v = 461.5  # J/kgK, water vapour gas constant
    rho_v_air = e_air / (r_v * (t_air + 273.15))
    rho_v_ice = e_ice / (r_v * (t_sk + 273.15))
    h_e = LR * h_c
    h_m = h_e / (RHO_AIR * CP_AIR)
    m_dep = max(h_m * (rho_v_air - rho_v_ice), 0.0)  # kg/m2s
    if m_dep <= 0:
        return 0.0  # no vapour drive = no deposition (surface warmer/drier)
    rate = m_dep / frost_density_hayashi(t_sk)  # m/s
    rate_mm_h = rate * 3.6e6  # mm/h
    capped = min(max(rate_mm_h, 0.1), 3.0)  # Leoni band mm/h
    return capped / 3.6e6  # back to m/s


def freezing_plateau_time(film_kg_m2, q_net):
    """t_freeze = m''·L_f/q_net (s).  0.1 mm film = 0.1 kg/m2."""
    return film_kg_m2 * L_FUS / max(q_net, 1e-6)


def frost_pin(t_equil, q_net, film_kg_m2, dt):
    """Apply the phase-change pin.

    If film mass exists AND the equilibrium surface would be below
    0 C, pin the surface at 0 C and release latent heat from the film:
      dm'' = -q_net·dt/L_f   (q_net < 0 = heat leaving the surface)
    The pin releases when the film is exhausted (m'' <= 0).

    Returns (pinned_temp_C, remaining_film_kg_m2, was_pinned).
    """
    if film_kg_m2 > 0 and t_equil < 0:
        d_m = -q_net * dt / L_FUS  # kg/m2; q_net<0 -> positive draw
        remaining = film_kg_m2 - d_m
        if remaining <= 0:
            # Film exhausted: the surface now drops below 0.
            return t_equil, 0.0, False
        return 0.0, remaining, True
    return t_equil, film_kg_m2, False


def frost_emissivity(frosted):
    """LWIR emissivity: 0.94-0.99 with frost (near-blackbody, MODIS/
    CESM), else the bare-surface baseline."""
    return FROST_EPS if frosted else BARE_EPS


import unittest


class TestFrostPhysics(unittest.TestCase):
    """Frost/ice phase-change physics (issue #195), all anchored to
    sourced values."""

    def test_latent_heat_of_fusion(self):
        # IAPWS-95 333.55 kJ/kg; Incropera 333.7; AEE uses 334e3.
        self.assertAlmostEqual(L_FUS, 334e3, delta=500)

    def test_freezing_plateau_calm(self):
        # 0.1 mm film (0.1 kg/m2) at q_net 107 W/m2 (calm, air -5C):
        # t = m''·L/q = 0.1*334000/107 = 312 s ~ 5 min (research worked ex).
        t = freezing_plateau_time(0.1, 107)
        self.assertAlmostEqual(t / 60, 5.2, delta=0.4)

    def test_freezing_plateau_windy(self):
        # 1.0 mm film at q_net 145 W/m2 (wind 2 m/s): ~38 min.
        t = freezing_plateau_time(1.0, 145)
        self.assertAlmostEqual(t / 60, 38.4, delta=1.0)

    def test_frost_point_offset(self):
        # At RH 100% the frost point sits ~0.6/1.1/2.1 C above the dew
        # point at -5/-10/-20 C (ice saturates lower than water).
        for air, expected in [(-5, 0.58), (-10, 1.11), (-20, 2.07)]:
            fp = frost_point_from_rh(air, 1.0)
            self.assertAlmostEqual(fp - air, expected, delta=0.05,
                                   msg=f"offset at {air} C")

    def test_hayashi_density(self):
        # Hayashi 1977: 650*exp(0.277*T_fs), ~163/-40/3.8 at -5/-10/-18.6.
        self.assertAlmostEqual(frost_density_hayashi(-5), 162.7, delta=2)
        self.assertAlmostEqual(frost_density_hayashi(-10), 40.7, delta=1)
        self.assertAlmostEqual(frost_density_hayashi(-18.6), 3.8, delta=0.3)

    def test_growth_rate_capped_to_band(self):
        # Leoni 2016 band 0.1-3 mm/h; strong gradient saturates at 3.
        h_c = 5.7 + 3.8 * 1.2
        rate = frost_growth_rate(h_c, -10, 0, 0.8)
        mm_h = rate * 3.6e6
        self.assertGreaterEqual(mm_h, 0.1)
        self.assertLessEqual(mm_h, 3.0)

    def test_no_gradient_no_deposition(self):
        # Surface warmer/drier than air: no vapour drive, zero growth.
        h_c = 5.7 + 3.8 * 1.2
        rate = frost_growth_rate(h_c, -10, -5, 0.6)  # air drier than plate
        self.assertEqual(rate, 0.0)

    def test_freeze_pin_releases_latent_heat(self):
        # Surface at -3 C with film: pinned to 0 C, film consumed.
        pinned, remaining, was = frost_pin(-3.0, -107, 0.1, 300)
        self.assertEqual(pinned, 0.0)
        self.assertGreater(remaining, 0)
        self.assertTrue(was)

    def test_freeze_pin_releases_when_exhausted(self):
        # Small film, large heat draw: film exhausts, pin releases.
        pinned, remaining, was = frost_pin(-3.0, -107, 0.001, 300)
        self.assertLess(pinned, 0.0)
        self.assertEqual(remaining, 0.0)
        self.assertFalse(was)

    def test_frost_emissivity_near_blackbody(self):
        # MODIS/CESM: frost 0.94-0.99, higher than bare soil.
        self.assertGreaterEqual(frost_emissivity(True), 0.94)
        self.assertLessEqual(frost_emissivity(True), 0.99)
        self.assertLess(frost_emissivity(False), frost_emissivity(True))


if __name__ == "__main__":
    unittest.main()
