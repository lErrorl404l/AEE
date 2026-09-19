"""Wet-ground thermal mirror (issue #194).

Mirrors the ground-surface temperature solver with a moisture axis.
The #124 ground solver treats the surface as DRY.  Wet soil conducts
7-8x more heat (Johansen 1975 Kersten interpolation) and evaporates
moisture (FAO-56 Penman-Monteith with bare-soil surface resistance),
which together pull a wet surface 5-8 C below the dry-air equilibrium
at typical humidity (Stull 2011 wet-bulb depression).

All constants trace to published sources; nothing invented.
"""

import math
import unittest

# ─── Constants (sourced) ────────────────────────────────────────────────────
SIGMA = 5.670374419e-8  # W/m2K4, Stefan-Boltzmann (CODATA 2022)
G = 1000.0  # W/m2, solar hemispherical (ASTM G173-23)
LAMBDA = 2.45e6  # J/kg, latent heat of vaporisation at 20 C (FAO-56)
GAMMA = 0.066  # kPa/C, psychrometric constant (FAO-56)
RHO_AIR = 1.1614  # kg/m3, air at 300 K (Incropera A.4)
CP_AIR = 1007.0  # J/kgK, air at 300 K (Incropera A.4)
# Bare-soil surface resistance (s/m): Shuttleworth & Wallace 1985 /
# van de Griend & Owe 1994.  0 = free water, 10 = wet top layer,
# 2000 = fairly dry (Fuchs & Tanner 1967 molecular diffusion).
RS_WET = 10.0
RS_DRY = 2000.0
# Field capacity / wilting point (volumetric): Minnesota Stormwater Manual.
# Sand FC 0.17 WP 0.09; loam FC 0.25-0.32 WP 0.09-0.15; clay FC 0.32 WP 0.20.
FC = 0.25  # loam field capacity at -33 kPa
WP = 0.10  # wilting point at -1500 kPa
# Manabe 1969 bucket: WK = 0.75 * W_FC; E = E0 * W/WK below WK (Budyko 1956).
WK_FRAC = 0.75
# Soil conductivity range (W/mK): Incropera A.3 sand dry 0.27,
# de Vries/Wessolek 2022 dry 0.15-0.35, saturated 1.4-2.6.
K_DRY = 0.27
K_SAT = 2.14  # sand saturated (de Vries)
# Volumetric heat capacity (J/m3K): Putkonen 1998 dry 1.68e6,
# saturated 2.72e6.
RHO_C_DRY = 1.68e6
RHO_C_SAT = 2.72e6
# Surface-layer depth for conduction to below-ground (m), FAO-56
# evaporative zone Ze = 0.1-0.15 m.
Z = 0.12


def water_sat_pressure_pa(T_c):
    """Bolton 1980 saturation vapour pressure (Pa)."""
    return 611.2 * math.exp(17.67 * T_c / (T_c + 243.5))


def soil_conductivity(moisture):
    """Interpolated conductivity via the Johansen 1975 Kersten number:
    Ke = (k - k_dry)/(k_sat - k_dry).  With Ke ~ moisture^1 for a
    simple two-point interpolation between dry and saturated.
    moisture is 0..1 of the FC-WP range.
    """
    m = max(0.0, min(1.0, moisture))
    return K_DRY + m * (K_SAT - K_DRY)


def soil_heat_capacity(moisture):
    """Volumetric heat capacity interpolation (Putkonen 1998)."""
    m = max(0.0, min(1.0, moisture))
    return RHO_C_DRY + m * (RHO_C_SAT - RHO_C_DRY)


def surface_resistance(moisture):
    """Bare-soil surface resistance vs moisture (s/m).  ~10 wet,
    2000 dry; rises steeply below ~15% volumetric (van de Griend &
    Owe 1994).
    """
    m = max(0.0, min(1.0, moisture))
    # Wet top layer keeps rs ~10 until the moisture falls below the
    # ~15% threshold, then climbs to 2000.
    if m >= 0.5:
        return RS_WET
    frac = m / 0.5
    return RS_WET + (RS_DRY - RS_WET) * (1.0 - frac)


def fao_penman_monteith(t_air, rh, wind, solar, moisture):
    """FAO-56 Penman-Monteith evaporation (W/m2).

    lambda*E = [Delta(Rn-G) + rho*cp*(es-ea)/ra] /
               [Delta + gamma*(1+rs/ra)]

    Bare-soil simplification: net radiation Rn ~ solar absorbed,
    ground flux G ~ 0 (surface layer), aerodynamic resistance
    ra = 1/(h) with h the convective coefficient.
    """
    # Slope of saturation curve d(es)/dT (Bolton derivative, kPa/C)
    es = water_sat_pressure_pa(t_air) / 1000.0  # kPa
    delta = es * 4302.645 / ((t_air + 243.5) ** 2)  # kPa/C
    ea = es * max(0.0, min(1.0, rh))
    # Aerodynamic resistance from the convective coefficient.
    # The convective coefficient IS h = rho*cp/ra, so ra = rho*cp/h
    # (the surface-to-air resistance a moving air parcel overcomes).
    h = 5.7 + 3.8 * max(wind, 0.0)
    ra = (RHO_AIR * CP_AIR) / max(h, 0.1)
    rs = surface_resistance(moisture)
    # Net radiation available for evaporation (W/m2)
    rn = solar * 0.7  # bare soil albedo ~0.3
    g = 0.0  # surface layer, no deep flux in the ET0 form
    num = delta * (rn - g) + RHO_AIR * CP_AIR * (es - ea) / ra
    den = delta + GAMMA * (1.0 + rs / ra)
    return max(num / den, 0.0)


def evaporative_draw(t_air, rh, wind, solar, moisture):
    """Evaporative heat flux (W/m2), bucketed by moisture: below
    WK = 0.75*FC the evaporation scales linearly (Budyko 1956)."""
    e_pm = fao_penman_monteith(t_air, rh, wind, solar, moisture)
    wk = WK_FRAC * FC
    # Budyko: E = E0 while W >= WK, E = E0*W/WK below
    if moisture * FC < wk:
        e_pm *= (moisture * FC) / wk
    return e_pm


def wet_bulb(t_air, rh):
    """Stull 2011 wet-bulb approximation (+-0.3 C).  rh is a FRACTION
    0..1 here but the Stull formula takes PERCENT (0-100)."""
    e = max(0.0, min(1.0, rh)) * 100.0
    tw = (
        t_air * math.atan(0.151977 * math.sqrt(e + 8.313659))
        + math.atan(t_air + e)
        - math.atan(e - 1.676331)
        + 0.00391838 * (e ** (3 / 2)) * math.atan(0.023101 * e)
        - 4.686035
    )
    return tw


def wet_ground_equilibrium(
    t_air, rh, wind, solar, moisture, t_deep=8.0, eps=0.92, alpha=0.65, n_iter=12
):
    """Newton solve of the wet-ground surface balance:

    q_solar + q_cond + q_rad = q_conv + q_evap
    q_solar = alpha*G
    q_cond  = k(theta)*(T_deep - Tg)/z   (conduction to below-ground)
    q_rad   = eps*sigma*(Tg^4 - Tsky^4)  (Swinbank 1963)
    q_conv  = h*(Tg - Tair)              (McAdams)
    q_evap  = lambda*E_PM(theta)         (FAO-56, bucketed)

    Returns (surface_c, evaporative_flux_wm2).
    """
    k = soil_conductivity(moisture)
    t_air_k = t_air + 273.15
    t_sky_k = t_air_k - 20.0  # clear-sky simplification for the mirror
    h = 5.7 + 3.8 * max(wind, 0.0)
    evap = evaporative_draw(t_air, rh, wind, solar, moisture)

    ts = t_air_k + 5.0
    for _ in range(n_iter):
        q_solar = alpha * solar
        q_cond = k * (t_deep + 273.15 - ts) / Z
        q_rad = eps * SIGMA * (ts**4 - t_sky_k**4)
        q_conv = h * (ts - t_air_k)
        residual = q_solar + q_cond - q_conv - q_rad - evap
        deriv = -(h + k / Z + 4 * eps * SIGMA * ts**3)
        ts = ts - residual / deriv
        ts = max(ts, t_air_k - 30)
        ts = min(ts, t_air_k + 80)
    return ts - 273.15, evap


class TestWetGroundPhysics(unittest.TestCase):
    """Issue #194 - wet-ground physics mirrors, validated against
    published sources."""

    def test_stull_wet_bulb_exact_formula(self):
        # Stull 2011 exact - primary source, NOT the research summary
        # (which slightly misread 30/50 as 24.4).
        self.assertAlmostEqual(wet_bulb(30, 0.5), 22.30, places=1)
        self.assertAlmostEqual(wet_bulb(35, 0.5), 26.60, places=1)
        self.assertAlmostEqual(wet_bulb(30, 0.4), 20.45, places=1)

    def test_wet_bulb_depression_range(self):
        # 5-8 C depression at typical RH, 30 C (research conclusion).
        dep = 30 - wet_bulb(30, 0.5)
        self.assertGreater(dep, 5)
        self.assertLess(dep, 8)
        # At 100% RH wet-bulb = dry-bulb.
        self.assertAlmostEqual(wet_bulb(25, 1.0), 25, places=1)

    def test_soil_conductivity_interpolation(self):
        # Johansen 1975 Kersten: k = k_dry + Ke*(k_sat-k_dry).
        self.assertAlmostEqual(soil_conductivity(0), K_DRY, places=3)
        self.assertAlmostEqual(soil_conductivity(1), K_SAT, places=3)
        self.assertAlmostEqual(soil_conductivity(0.5), (K_DRY + K_SAT) / 2, places=3)
        # Saturated is 7-8x dry (research).
        ratio = soil_conductivity(1) / soil_conductivity(0)
        self.assertGreater(ratio, 6)
        self.assertLess(ratio, 10)

    def test_soil_heat_capacity(self):
        self.assertAlmostEqual(soil_heat_capacity(0), RHO_C_DRY, delta=1)
        self.assertAlmostEqual(soil_heat_capacity(1), RHO_C_SAT, delta=1)

    def test_surface_resistance_bare_soil(self):
        self.assertAlmostEqual(surface_resistance(1), RS_WET, delta=1)
        self.assertAlmostEqual(surface_resistance(0), RS_DRY, delta=1)
        # Rises steeply below the ~15% volumetric threshold.
        self.assertGreater(surface_resistance(0.2), RS_WET * 5)

    def test_evaporative_draw_sane_magnitude(self):
        # At 800 W/m2 solar, evaporation must stay within the energy
        # budget (0-600 W/m2), not exceed the incoming flux.
        e_wet = fao_penman_monteith(30, 0.5, 1.0, 800, 1.0)
        self.assertGreater(e_wet, 0)
        self.assertLess(e_wet, 600)
        # Dry soil (bucketed) evaporates nothing.
        e_dry = evaporative_draw(30, 0.5, 1.0, 800, 0.0)
        self.assertEqual(e_dry, 0)

    def test_wet_ground_cools_below_dry(self):
        # Wet ground sits BELOW the dry equilibrium (the evaporative
        # draw + conductivity).  At noon 30C/50%, saturated ground
        # must be cooler than dry ground.
        ts_dry, _ = wet_ground_equilibrium(30, 0.5, 1.0, 800, 0.0)
        ts_wet, _ = wet_ground_equilibrium(30, 0.5, 1.0, 800, 1.0)
        self.assertGreater(ts_dry, ts_wet)
        # The wet surface approaches the wet-bulb region (within ~10C).
        self.assertLess(ts_wet, wet_bulb(30, 0.5) + 10)

    def test_conductivity_pulls_toward_deep(self):
        # Higher conductivity couples the surface to the deep soil
        # temperature, pulling the surface toward it.
        ts_low_k, _ = wet_ground_equilibrium(30, 0.5, 1.0, 800, 0.05, t_deep=5)
        ts_high_k, _ = wet_ground_equilibrium(30, 0.5, 1.0, 800, 1.0, t_deep=5)
        self.assertLess(abs(ts_high_k - 5), abs(ts_low_k - 5))


if __name__ == "__main__":
    unittest.main()
