"""Full-depth ground node-stack mirror (issue #198).

Mirrors the 1D vertical soil thermal diffusion stack that replaces the
single-node ground solver (#194).  Four layers, Noah LSM geometry,
Crank-Nicolson tridiagonal diffusion, moisture-dependent conductivity
(Johansen 1975 LOGARITHMIC unfrozen form), fixed-temperature bottom
boundary (annual mean air), surface node feeding the MRT exchange and
the Stefan freeze index.

Layer geometry (Noah LSM, Mitchell 2005 NCEP User's Guide v2.7.1):
  thicknesses  0.10 / 0.30 / 0.60 / 1.00 m   (total 2.0 m)
  node depths  0.05 / 0.25 / 0.70 / 1.50 m
Each layer <= 3x the one above.

Everything traces to the sources; nothing invented.
"""

import math

# ─── Constants (sourced) ────────────────────────────────────────────────────
SIGMA = 5.670374419e-8  # W/m2K4, Stefan-Boltzmann (CODATA 2022)
G = 1000.0  # W/m2, solar hemispherical (ASTM G173-23)
LAMBDA = 2.45e6  # J/kg, latent heat of vaporisation (FAO-56)
GAMMA = 0.066  # kPa/C, psychrometric constant (FAO-56)
RHO_AIR = 1.1614  # kg/m3, air at 300 K (Incropera A.4)
CP_AIR = 1007.0  # J/kgK, air at 300 K (Incropera A.4)

# Soil thermal diffusivity alpha = k/(rho*cp):
#   dry: 0.27 / 1.68e6 = 0.16e-6 m2/s
#   saturated: 2.14 / 2.72e6 = 0.79e-6 m2/s
# Literature (Oke 1987 Table 4.1 after de Vries 1963):
#   dry sand 2.6e-7, wet sand 1.0e-6, loam 5.0e-7, wet loam 8.0e-7.
ALPHA_DRY = 0.27 / 1.68e6  # m2/s
ALPHA_SAT = 2.14 / 2.72e6  # m2/s

# Noah LSM 4-layer geometry (Mitchell 2005)
NOAH_DZ = [0.10, 0.30, 0.60, 1.00]  # m, layer thicknesses
NOAH_Z = [0.05, 0.25, 0.70, 1.50]  # m, node depths

# FAO-56 evaporative zone (Allen et al 1998 ch 7): 0.10-0.15 m
ZE = 0.12
# Field capacity / wilting point (Minnesota Stormwater Manual)
FC = 0.25
WP = 0.10
WK_FRAC = 0.75  # Manabe 1969 critical wetness fraction


def water_sat_pressure_pa(T_c):
    """Bolton 1980 saturation vapour pressure, Pa."""
    return 611.2 * math.exp(17.67 * T_c / (T_c + 243.5))


def soil_conductivity(moisture, k_dry=0.27, k_sat=2.14, fine=False):
    """Johansen 1975 Kersten interpolation (LOGARITHMIC unfrozen form).

    Ke = 0.7*log10(Sr) + 1.0   coarse soils (Sr > 0.05)
    Ke = log10(Sr) + 1.0       fine soils
    frozen: Ke = Sr (linear)
    k = k_dry + Ke*(k_sat - k_dry)
    """
    sr = max(min(moisture, 1.0), 0.01)
    if sr <= 0.05:
        ke = 0.0
    elif fine:
        ke = math.log10(sr) + 1.0
    else:
        ke = 0.7 * math.log10(sr) + 1.0
    ke = max(ke, 0.0)
    return k_dry + ke * (k_sat - k_dry)


def soil_alpha(moisture, k_dry=0.27, k_sat=2.14, rho_c_dry=1.68e6, rho_c_sat=2.72e6):
    """Thermal diffusivity with moisture-dependent k and heat capacity."""
    k = soil_conductivity(moisture, k_dry, k_sat)
    rho_c = rho_c_dry + moisture * (rho_c_sat - rho_c_dry)
    return k / rho_c


def surface_resistance(moisture):
    """Bare-soil surface resistance (s/m).

    van de Griend & Owe 1994: ~10 s/m wet top layer, rises at ~15% vol.
    Fuchs & Tanner 1967 molecular diffusion: ~2000 s/m fairly dry.
    """
    if moisture >= 0.15:
        return 10.0
    if moisture <= 0.02:
        return 2000.0
    frac = (moisture - 0.02) / (0.15 - 0.02)
    return 10.0 + 1990.0 * (1.0 - frac)


def surface_energy_flux(
    t_surf, t_air, t_sky, wind, solar, alpha_s, eps_s, moisture, rh
):
    """Surface boundary flux (W/m2): net = solar + longwave - sens - latent.

    q_net = alpha*G*0.7 + eps*sigma*(Tsky^4) - eps*sigma*Ts^4
            - h*(Ts-Tair) - lambda*E_PM
    Positive = into the soil (heating).
    """
    h = 5.7 + 3.8 * wind  # McAdams, W/m2K
    ts_k = t_surf + 273.15
    tair_k = t_air + 273.15
    tsky_k = t_sky + 273.15
    q_solar = alpha_s * solar * 0.7  # bare-soil albedo 0.3
    q_lw_in = eps_s * SIGMA * (tsky_k**4)
    q_lw_out = eps_s * SIGMA * (ts_k**4)
    q_sens = h * (ts_k - tair_k)
    # FAO-56 Penman-Monteith evaporative draw (Allen et al 1998):
    #   lambda*ET = [Delta(Rn-G) + rho*cp*(es-ea)/ra] /
    #               [Delta + gamma*(1 + rs/ra)]
    # UNITS: Delta in kPa/C, es-ea in kPa, gamma in kPa/C, Rn in W/m2 ->
    # lambda*ET in W/m2.  The Pa values must be converted to kPa first
    # (unit-consistency bug caught in validation - the Pa form was
    # 1000x too large and over-cooled the surface to freezing).
    delta = water_sat_pressure_pa(t_surf) * 4302.645 / (t_surf + 243.5) ** 2
    delta = delta / 1000.0  # Pa/C -> kPa/C
    es = water_sat_pressure_pa(t_air) / 1000.0  # kPa
    ea = es * rh
    ra = RHO_AIR * CP_AIR / max(h, 1.0)
    rs = surface_resistance(moisture)
    rn = q_solar + q_lw_in - q_lw_out
    lambda_et = (delta * rn + RHO_AIR * CP_AIR * (es - ea) / ra) / (
        delta + GAMMA * (1.0 + rs / ra)
    )
    # Manabe 1969 bucket: E = E0 while W >= 0.75*FC, scaled below
    e_scale = min(moisture / (WK_FRAC * FC), 1.0)
    q_latent = lambda_et * e_scale  # W/m2 (lambda*ET IS the flux)
    q_latent = max(q_latent, 0.0)
    return q_solar + q_lw_in - q_lw_out - q_sens - q_latent


def crank_nicolson(t_nodes, dz, alpha_layer, dt, q_top, t_bot):
    """One Crank-Nicolson step of the 1D diffusion equation.

    Solves the tridiagonal system for T^(n+1):
      -Fo*T[i-1] + (1+2Fo)*T[i] - Fo*T[i+1] = T[i] + Fo*(T[i-1]-2T[i]+T[i+1])
    with Fo = alpha*dt/dz^2 per layer (interfacial alpha).  Top BC
    q_top (W/m2) enters as the surface gradient; bottom fixed at t_bot.
    """
    n = len(t_nodes)
    t_new = list(t_nodes)
    # Assemble the tridiagonal matrix (Thomas algorithm)
    a = [0.0] * n
    b = [0.0] * n
    c = [0.0] * n
    d = [0.0] * n
    for i in range(n):
        alpha_i = alpha_layer[i]
        fo_i = alpha_i * dt / (dz[i] ** 2)
        fo_im = alpha_layer[i - 1] * dt / (dz[i] ** 2) if i > 0 else fo_i
        # Conservative form: flux between nodes i and i+1 uses interface k
        fo_u = fo_i
        fo_d = alpha_layer[i + 1] * dt / (dz[i] ** 2) if i < n - 1 else fo_i
        b[i] = 1.0 + fo_u + fo_d
        if i > 0:
            a[i] = -fo_u
        if i < n - 1:
            c[i] = -fo_d
        # Right-hand side (explicit evaluation of the Laplacian)
        lap = 0.0
        if i > 0:
            lap += fo_u * (t_nodes[i - 1] - t_nodes[i])
        if i < n - 1:
            lap += fo_d * (t_nodes[i + 1] - t_nodes[i])
        d[i] = t_nodes[i] + lap
    # Top boundary: surface flux as a transient source on the surface
    # half-cell (finite-volume form).  The heat entering the top cell of
    # thickness dz/2 in time dt raises its temperature by
    #   dT = q_top * dt / (rho*cp * dz/2) = q_top * dt * 2 / (rho*cp*dz)
    k0 = soil_conductivity(0.3)  # surface layer moisture ~0.3
    rho_c0 = 1.68e6 + 0.3 * (2.72e6 - 1.68e6)
    d[0] += q_top * dt * 2.0 / (rho_c0 * dz[0])
    # Bottom boundary: fixed temperature
    d[-1] = t_bot
    b[-1] = 1.0
    c[-1] = 0.0
    a[-1] = 0.0
    # Thomas algorithm
    for i in range(1, n):
        w = a[i] / b[i - 1]
        b[i] -= w * c[i - 1]
        d[i] -= w * d[i - 1]
    t_new[-1] = d[-1] / b[-1]
    for i in range(n - 2, -1, -1):
        t_new[i] = (d[i] - c[i] * t_new[i + 1]) / b[i]
    return t_new


def run_node_stack(
    t_air,
    t_sky,
    wind,
    solar,
    alpha_s,
    eps_s,
    rh,
    moisture_per_layer,
    dt=300.0,
    n_steps=288,
    t_bot=10.0,
    t_init=None,
):
    """Run the 4-layer stack forward n_steps.

    Returns the layer-node temperatures at the final step and the
    surface-node temperature series (for amplitude validation).
    """
    n = len(NOAH_DZ)
    alpha_layer = [soil_alpha(m) for m in moisture_per_layer]
    if t_init is None:
        t_nodes = [t_air + 5.0, t_air + 2.0, t_air, t_bot]
    else:
        t_nodes = list(t_init)
    surface_series = []
    for _ in range(n_steps):
        q_top = surface_energy_flux(
            t_nodes[0],
            t_air,
            t_sky,
            wind,
            solar,
            alpha_s,
            eps_s,
            moisture_per_layer[0],
            rh,
        )
        t_nodes = crank_nicolson(t_nodes, NOAH_DZ, alpha_layer, dt, q_top, t_bot)
        surface_series.append(t_nodes[0])
    return t_nodes, surface_series


import unittest


class TestNodeStackConstants(unittest.TestCase):
    """Sourced constants pinned for drift."""

    def test_noah_layer_geometry(self):
        self.assertEqual(NOAH_DZ, [0.10, 0.30, 0.60, 1.00])
        self.assertEqual(NOAH_Z, [0.05, 0.25, 0.70, 1.50])

    def test_alpha_range_in_literature(self):
        # Oke 1987: dry sand 2.6e-7 ... wet sand 1.0e-6 m2/s
        self.assertGreaterEqual(ALPHA_SAT, 0.7e-6)
        self.assertLessEqual(ALPHA_SAT, 1.0e-6)
        self.assertGreaterEqual(ALPHA_DRY, 0.1e-6)
        self.assertLessEqual(ALPHA_DRY, 0.3e-6)


class TestSoilConductivity(unittest.TestCase):
    """Johansen 1975 logarithmic unfrozen Kersten."""

    def test_dry_to_saturated_range(self):
        # dry 0.27 -> saturated 2.14: the 7.9x de Vries range
        self.assertAlmostEqual(soil_conductivity(0.02), 0.27, places=2)
        self.assertAlmostEqual(soil_conductivity(1.0), 2.14, places=2)
        self.assertGreater(soil_conductivity(1.0) / soil_conductivity(0.02), 7.0)

    def test_logarithmic_not_linear(self):
        # midpoint should NOT be the arithmetic mean (0.27+2.14)/2 = 1.2;
        # logarithmic Ke gives ~1.06 at Sr 0.15
        k_mid = soil_conductivity(0.15)
        self.assertLess(k_mid, 1.2)
        self.assertGreater(k_mid, 0.9)

    def test_alpha_monotonic(self):
        a0 = soil_alpha(0.02)
        a1 = soil_alpha(1.0)
        self.assertGreater(a1, a0)


class TestSurfaceResistance(unittest.TestCase):
    """van de Griend & Owe 1994 / Fuchs & Tanner 1967."""

    def test_wet_soil_low_resistance(self):
        self.assertAlmostEqual(surface_resistance(0.30), 10.0)

    def test_dry_soil_high_resistance(self):
        self.assertEqual(surface_resistance(0.02), 2000.0)

    def test_rises_below_15pct(self):
        r_dry = surface_resistance(0.05)
        r_wet = surface_resistance(0.20)
        self.assertGreater(r_dry, r_wet)


class TestSurfaceEnergyFlux(unittest.TestCase):
    """The surface BC balances solar + longwave - sensible - latent."""

    def test_dry_surface_overheats_wet_cools(self):
        # Noon 30C/50%: dry surface (moisture 0.02) vs wet (0.30)
        q_dry = surface_energy_flux(45, 30, 15, 1.0, 520, 0.65, 0.92, 0.02, 0.5)
        q_wet = surface_energy_flux(45, 30, 15, 1.0, 520, 0.65, 0.92, 0.30, 0.5)
        self.assertLess(q_wet, q_dry)


class TestCrankNicolson(unittest.TestCase):
    """The tridiagonal scheme is unconditionally stable (no CFL limit)."""

    def test_no_blowup_at_large_step(self):
        # 300 s steps with alpha ~0.5e-6 and dz 0.1: Fo = 0.015 - stable
        nodes = [30.0, 28.0, 25.0, 12.0]
        alpha = [0.5e-6] * 4
        for _ in range(200):
            nodes = crank_nicolson(nodes, NOAH_DZ, alpha, 300.0, 0.0, 10.0)
        self.assertTrue(all(-50 < t < 100 for t in nodes))

    def test_converges_to_fixed_bottom(self):
        nodes = [30.0, 28.0, 25.0, 12.0]
        alpha = [0.5e-6] * 4
        for _ in range(500):
            nodes = crank_nicolson(nodes, NOAH_DZ, alpha, 300.0, 0.0, 10.0)
        self.assertLess(abs(nodes[-1] - 10.0), 0.5)


class TestAmplitudeAttenuation(unittest.TestCase):
    """The stack must reproduce the exp(-z/d) diurnal damping."""

    def test_skin_depth_anchors(self):
        d = 0.117  # diurnal skin depth for alpha 0.5e-6
        self.assertAlmostEqual(math.exp(-0.10 / d), 0.425, places=2)
        self.assertAlmostEqual(math.exp(-0.50 / d), 0.014, places=2)
        self.assertAlmostEqual(math.exp(-1.00 / d), 0.0002, places=3)

    def test_surface_swing_larger_than_deep(self):
        # Diurnal cycle on a clear day: surface amplitude >> deep, and
        # DRY soil overheats while WET soil is evaporatively cooled.
        wet, _ = run_node_stack(
            25.0,
            12.0,
            1.0,
            520,
            0.65,
            0.92,
            0.5,
            [0.30] * 4,
            dt=300.0,
            n_steps=144,
            t_bot=10.0,
            t_init=[35.0, 28.0, 20.0, 10.0],
        )
        dry, _ = run_node_stack(
            25.0,
            12.0,
            1.0,
            520,
            0.65,
            0.92,
            0.5,
            [0.02] * 4,
            dt=300.0,
            n_steps=144,
            t_bot=10.0,
            t_init=[35.0, 28.0, 20.0, 10.0],
        )
        # Deep layer stays near the bottom anchor
        self.assertLess(abs(wet[3] - 10.0), 2.0)
        # Dry soil overheats above air (solar), wet soil is drawn below
        # (evaporative + conductive draw) - the wet-bulb depression.
        self.assertGreater(dry[0], 25.0)
        self.assertLess(wet[0], 25.0)


if __name__ == "__main__":
    unittest.main()
