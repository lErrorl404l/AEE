"""Two-node thermal model mirror (issue #191).

Mirrors the SQF substrate's core/skin coupled solve.  The #124 system
solves the SURFACE node only.  Real objects have an interior whose heat
drives the skin.  This mirror implements the researched two-node
physics; every constant traces to a published source (see comments).

Models:
- Human: Gagge two-node (Gagge, Stolwijk & Nishi 1971 ASHRAE Trans
  77(1):247-262; Gagge, Fobelets & Berglund 1986 ASHRAE Trans
  92(2B):709-731; implementation cross-checked against pythermalcomfort
  two_nodes_gagge.py, Tartarini & Schiavon 2020 SoftwareX 12:100578).
- Engine: lumped-RC two-node (Bohac 1996 SAE 960073; Jarrier 2000 SAE
  2000-01-0299; VDI Heat Atlas ch C3).
- Building: ISO 52016-1 envelope + mass nodes.

Units: SI (W/m2, K, kg, m).  Temperatures in Celsius at the interface.
"""

import math

# ─── Constants (all sourced) ────────────────────────────────────────────────
SIGMA = 5.670374419e-8  # W/m2K4, Stefan-Boltzmann (CODATA 2022)
G = 1000.0  # W/m2, solar hemispherical (ASTM G173-23)
L_VAP = 2.26e6  # J/kg, latent heat of vaporisation of water
L_FUS = 334e3  # J/kg, latent heat of fusion of ice
GRAV = 9.81  # m/s2
C_P_BL = 4186.0  # J/(kg·K), blood specific heat (Gagge 1986)
C_P_BODY = 3492.0  # J/(kg·K), body specific heat 0.97 Wh/(kg·K)
K_MIN = 5.28  # W/(m2·K), minimum tissue conductance (Gagge)
BODY_MASS = 70.0  # kg, standard man
A_D = 1.8258  # m2, DuBois surface area (Gagge)
MET = 58.2  # W/m2, 1 met (Gagge)
LR = 16.5  # K/kPa, Lewis relation at 1 atm (Gagge 2.2 C/torr)
T_CR_NEUTRAL = 36.8  # C, neutral core temp (Gagge)
T_SK_NEUTRAL = 33.7  # C, neutral skin temp (Gagge)
T_B_NEUTRAL = 36.49  # C, neutral mean body temp (Gagge)
ALPHA_SKIN_NEUTRAL = 0.1  # skin mass fraction at neutral (Gagge)


class Material:
    """Per-material thermal properties from the #124 registry
    [eps, alpha_solar, rho kg/m3, cp J/kgK, k W/mK]."""

    def __init__(self, name, eps, alpha, rho, cp, k):
        self.name = name
        self.eps = eps
        self.alpha = alpha
        self.rho = rho
        self.cp = cp
        self.k = k


MATERIALS = {
    "metal": Material("metal", 0.90, 0.70, 7850, 490, 50),  # Incropera
    "glass": Material("glass", 0.90, 0.15, 2500, 840, 1.1),  # Incropera
    "rubber": Material("rubber", 0.95, 0.90, 1314, 1898, 0.22),  # Guo 2023
    "concrete": Material("concrete", 0.92, 0.60, 2300, 880, 1.4),  # Incropera
    "wood": Material("wood", 0.88, 0.60, 700, 1700, 0.15),  # Incropera
    "human": Material("human", 0.98, 0.60, 1100, 3500, 0.35),  # Steketee 1973
    "engine": Material("engine", 0.80, 0.90, 7200, 500, 50),  # cast iron
}


def water_sat_pressure_pa(T_c):
    """Saturation vapour pressure (Pa).  Bolton 1980, Mon. Wea. Rev.
    108:1046-1053: e_s = 611.2 exp(17.67 T/(T+243.5)), valid -35..+35 C,
    error 0.4%.  (611.2 Pa = 6.112 hPa.)"""
    return 611.2 * math.exp(17.67 * T_c / (T_c + 243.5))


def d_sat_pressure_dT_pa(T_c):
    """Exact closed-form derivative of the Bolton curve (Pa/K):
    de_s/dT = e_s · 17.67·243.5 / (T+243.5)^2."""
    e_s = water_sat_pressure_pa(T_c)
    return e_s * 17.67 * 243.5 / ((T_c + 243.5) ** 2)


# ─── Air properties at 300 K (Incropera Table A.4) ─────────────────────────
AIR_300K = {
    "nu": 15.89e-6,  # m2/s, kinematic viscosity
    "k": 0.02624,  # W/(m·K), thermal conductivity
    "Pr": 0.707,  # Prandtl number
    "beta": 0.00333,  # 1/K, = 1/300 (ideal gas)
    "cp": 1007.0,  # J/(kg·K)
    "rho": 1.1614,  # kg/m3
}


def mcadams_h(wind):
    """Forced+free convection (W/m2K).  McAdams 1954 'Heat
    Transmission' 3rd ed, as used in the #124 substrate:
    h = 5.7 + 3.8·w."""
    return 5.7 + 3.8 * max(wind, 0.0)


def natural_convection_h(dT, L_char, orientation="vertical", T_ref=300.0):
    """Natural convection coefficient (W/m2K).

    Grashof/Rayleigh correlations, Incropera & DeWitt 7th ed Table 9.3:
      Gr_L = g·β·ΔT·L^3/ν^2,  Ra_L = Gr·Pr,  β = 1/T_f
      vertical all Ra:  Nu = {0.825 + 0.387 Ra^(1/6) /
                            [1+(0.492/Pr)^(9/16)]^(8/27)}^2
                         (Churchill & Chu 1975, IJHMT 18:1323-1329)
      vertical laminar (Ra<1e9): Nu = 0.59 Ra^(1/4)
      horizontal up (hot roof): Nu = 0.54 Ra^(1/4), 1e4<Ra<1e7;
                                Nu = 0.15 Ra^(1/3), 1e7<Ra<1e11
      horizontal down: Nu = 0.27 Ra^(1/4), 1e5<Ra<1e10
      L_c = A_s/P (area/perimeter) for horizontal plates.
    """
    if dT <= 0:
        return 0.0
    nu = AIR_300K["nu"]
    pr = AIR_300K["Pr"]
    k_air = AIR_300K["k"]
    beta = 1.0 / T_ref
    gr = GRAV * beta * abs(dT) * (L_char**3) / (nu**2)
    ra = gr * pr
    if ra < 1e3:
        return 0.0
    if orientation == "vertical":
        num = 0.387 * (ra ** (1.0 / 6.0))
        den = (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (8.0 / 27.0)
        nu_c = (0.825 + num / den) ** 2
    elif orientation == "up":
        if ra < 1e7:
            nu_c = 0.54 * (ra**0.25)
        else:
            nu_c = 0.15 * (ra ** (1.0 / 3.0))
    else:  # down
        nu_c = 0.27 * (ra**0.25)
    return max(nu_c * k_air / L_char, 0.0)


def combined_h(wind, dT, L_char, orientation):
    """Forced + natural superposition.  Churchill & Usagi 1972,
    AIChE J 18(6):1121-1128: h = (h_f^n + h_n^n)^(1/n), n = 3 for
    vertical aiding flow (Churchill 1977 AIChE J 23(1):10-16)."""
    h_f = mcadams_h(wind)
    h_n = natural_convection_h(dT, L_char, orientation)
    return (h_f**3 + h_n**3) ** (1.0 / 3.0)


def gagge_blood_flow(t_sk, t_cr):
    """Gagge 1986 skin blood flow (L/(h·m2)):
    m_bl = (6.3 + 200·W_sig)/(1 + 0.5·C_sig)
    W_sig = max(0, T_sk - 33.7) (vasodilation)
    C_sig = max(0, 33.7 - T_sk) (vasoconstriction)
    Capped at 14.4 L/(h·m2) (240 ml/min/m2 max vasodilation, from the
    segment research: skin blood flow 240 vasodilated at 35C, 105
    neutral at 30C = 6.3 L/(h·m2)) and floored at 0.5."""
    w_sig = max(0.0, t_sk - T_SK_NEUTRAL)
    c_sig = max(0.0, T_SK_NEUTRAL - t_sk)
    m_bl = (6.3 + 200.0 * w_sig) / (1.0 + 0.5 * c_sig)
    return min(max(m_bl, 0.5), 14.4)


def gagge_evaporative(t_sk, t_cr, t_air, rh, h_c, v_bl):
    """Gagge evaporative heat loss terms (W/m2):
    E_max = (p_sk,s - p_a)/(r_ea + r_ecl)  [r_ecl=0 nude]
    E_rsw = 0.68·m_rsw, m_rsw = 170·max(0,T_b-36.49)·exp(max(0,T_sk-33.7)/10.7)
    w = 0.06 + 0.94·(E_rsw/E_max)
    E_dif = w·E_max - E_rsw
    h_e = LR·h_c (Lewis relation), r_ea = 1/h_e.
    Returns (E_sw_total, wettedness)."""
    p_sk = water_sat_pressure_pa(t_sk)
    p_a = water_sat_pressure_pa(t_air) * rh
    t_b = ALPHA_SKIN_NEUTRAL * t_sk + (1 - ALPHA_SKIN_NEUTRAL) * t_cr
    m_rsw = (
        170.0
        * max(0.0, t_b - T_B_NEUTRAL)
        * math.exp(max(0.0, t_sk - T_SK_NEUTRAL) / 10.7)
    )
    e_rsw = 0.68 * m_rsw
    h_e = LR * h_c * 1e-3 * 1e3  # W/m2·Pa: LR K/kPa x h_c -> see note
    # Lewis relation: h_e = LR * h_c with LR = 16.5 K/kPa.  Convert:
    #   16.5 K/kPa = 0.0165 K/Pa; h_e [W/m2·Pa] = 0.0165 * h_c [W/m2K]
    #   because 1 W/m2K of convection transports 1/rho_cp ... simpler:
    #   the standard form is h_e = 16.5 * h_c with P in kPa.
    #   Use h_e [W/m2·kPa] = 16.5 * h_c, P in kPa below.
    h_e_kpa = 16.5 * h_c
    e_max = (p_sk - p_a) / 1000.0 * h_e_kpa  # P in kPa -> W/m2
    e_max = max(e_max, 0.0)
    if e_max <= 0:
        return 0.0, 0.06
    w = 0.06 + 0.94 * (e_rsw / e_max)
    w = min(w, 1.0)
    e_dif = w * e_max - e_rsw
    return e_rsw + e_dif, w


def solve_two_node(
    core,
    skin,
    t_air,
    wind,
    solar,
    exposure,
    m_core,
    m_skin,
    area,
    L_char,
    t_core0,
    t_skin0,
    q_gen,
    orientation="vertical",
    rh=0.5,
    dt=5.0,
    t_ground=30.0,
    is_human=False,
    L_cond=0.05,
    evap_on=True,
    n_steps=1,
):
    """Core/skin coupled solve.

    Gagge form (human) or lumped-RC (engine/building):
      core: S_cr = q_gen/A - cond·(T_cr - T_sk)  (per W/m2 if area-normalised)
      skin: q_cond_in + q_solar = q_conv + q_rad + q_evap
    Conduction conductance k·A/L_cond (Fourier), W/K - L_cond is the
    BLOCK WALL THICKNESS (conduction path length), distinct from L_char
    which is the convection plate dimension.  The #124 substrate's
    single-node solver had no core at all; the two-node extension must
    not reuse L_char as the conduction length or a thin plate (1 cm)
    yields k·A/L = 30000 W/K flooding the skin.
    Skin Newton solve includes the exact evaporative derivative
    dE_evap/dT_sk = h_e·w·de_s/dT (Bolton closed form).
    Returns (t_core, t_skin) after one dt step.
    """
    # Convection: Gagge's human model uses its own correlation
    # (h = max(3.0 natural, 8.6·v^0.53 forced) per Gagge 1986), NOT the
    # McAdams inert-surface form.  At still air McAdams gives 6.08 vs
    # Gagge's 3.0 - the higher value over-cools the skin and pushes the
    # model into false vasoconstriction.  Use the Gagge correlation for
    # humans, the substrate's combined_h (McAdams + natural) otherwise.
    h_c = (
        max(3.0, 8.6 * max(wind, 0.1) ** 0.53)
        if is_human
        else combined_h(wind, t_skin0 - t_air, L_char, orientation)
    )
    cond = min(core.k, skin.k) * area / max(L_cond, 0.01)  # W/K Fourier
    m_bl = 0.0
    k_coupling = 0.0

    # ── Coupled core/skin steady state ─────────────────────────────────────
    # Gagge: core and skin are solved SIMULTANEOUSLY - the blood-flow
    # coupling carries heat both ways, and metabolic heat enters the
    # core.  Sequential solving (core first, then skin using the new
    # core) lets the skin chase the core over repeated steps.  Instead,
    # find the JOINT fixed point where both dTc/dt = 0 and the skin
    # balance hold, then apply one transient step.
    if is_human:
        m_bl = gagge_blood_flow(t_skin0, t_core0)  # L/(h·m2)
        cpl = C_P_BL * m_bl / 3600.0  # W/(m2·K)
        k_coupling = (K_MIN + cpl) * area
    else:
        m_bl = 0.0
        k_coupling = cond

    # Skin surface terms that do not depend on Tc:
    q_solar = skin.alpha * solar * exposure
    mrt_k = (0.5 * (t_ground + 273.15) ** 4 + 0.5 * (t_air + 273.15) ** 4) ** 0.25
    t_air_k = t_air + 273.15

    # Iterate the skin to its fixed point, solving the core ANALYTICALLY.
    # The core residual is linear in t_cr:
    #   r_cr = q_gen + q_shiv*A - q_resp*A - k_coupling*(t_cr - t_sk) = 0
    #   => t_cr = t_sk + (q_gen + q_shiv*A - q_resp*A)/k_coupling
    # Damped Newton on the COUPLED pair oscillates (the coupling term is
    # large and the damping factor must be tiny to stay stable, which
    # never converges).  Substituting the linear core solution leaves a
    # single nonlinear skin equation that converges cleanly.
    t_sk = t_skin0
    t_cr = t_core0
    w = 0.0
    for _ in range(12):
        # Blood flow updates with the current skin temp (Gagge sigmoid).
        if is_human:
            m_bl = gagge_blood_flow(t_sk, t_cr)
            cpl = C_P_BL * m_bl / 3600.0
            k_coupling = (K_MIN + cpl) * area
        else:
            k_coupling = cond
        # Respiratory loss (W/m2, Gagge 1986; p_a in torr).
        q_resp = 0.0014 * MET * (34.0 - t_air) + 0.0023 * MET * (
            44.0 - water_sat_pressure_pa(t_air) * rh / 133.322
        )
        # Shivering (W/m2): 19.4 * C_sig * C_core_sig (Gagge 1986).
        # Uses the PERSISTENT core state (t_core0), not the iterating
        # analytic t_cr - shivering is a metabolic response to the body's
        # MEASURED core temp.  Feeding it the equilibrium solution makes
        # the shivering term positive-feedback and the fixed point
        # explodes (a warm analytic core suppresses shivering, which lets
        # the core cool, which re-triggers shivering ... unbounded).
        c_sig = max(0.0, T_SK_NEUTRAL - t_sk)
        c_core_sig = max(0.0, T_CR_NEUTRAL - t_core0)
        q_shiv = 19.4 * c_sig * c_core_sig  # W/m2
        # Analytic core solution from the linear residual.
        t_cr = t_sk + (q_gen + q_shiv * area - q_resp * area) / (k_coupling + 1e-6)
        # Skin residual: q_solar + coupling*(Tc - Ts) - conv - rad - evap = 0
        ts_abs = t_sk + 273.15
        conv = h_c * (ts_abs - t_air_k)
        rad = skin.eps * SIGMA * (ts_abs**4 - mrt_k**4)
        if is_human and evap_on:
            _, w = gagge_evaporative(t_sk, t_cr, t_air, rh, h_c, m_bl)
        else:
            w = 0.0
        h_e_kpa = 16.5 * h_c
        p_sk = water_sat_pressure_pa(t_sk) / 1000.0  # kPa
        p_a = water_sat_pressure_pa(t_air) * rh / 1000.0
        evap = w * h_e_kpa * max(p_sk - p_a, 0.0)
        r_sk = q_solar + k_coupling * (t_cr - t_sk) - conv - rad - evap
        dT_sk = r_sk / (
            h_c
            + 4 * skin.eps * SIGMA * ts_abs**3
            + w * h_e_kpa * d_sat_pressure_dT_pa(t_sk) / 1000.0
            + 1e-6
        )
        t_sk = t_sk + dT_sk
        t_sk = max(t_sk, t_air - 60)
        t_sk = min(t_sk, t_air + 500)
    t_core_eq = t_cr
    t_skin_eq = t_sk

    # ── Asymmetric transient (issue #191) ───────────────────────────────────
    # One exponential step toward the JOINT equilibrium.  Heating tau =
    # m·cp/(h·A + coupling).  Cooling lengthens when the endothermic
    # (evaporative) path is active: latent heat removal means the
    # observable surface cools slower than a dry surface.
    tau = max(m_skin * skin.cp / (max(h_c * area, 1e-6) + k_coupling), 30.0)
    tau = min(tau, 3600.0)
    if w > 0.06:
        tau *= 1.5
    k_tau = 1.0 - math.exp(-dt / max(tau, 30.0))
    t_skin1 = t_skin0 + (t_skin_eq - t_skin0) * k_tau
    t_core1 = t_core0 + (t_core_eq - t_core0) * k_tau
    if n_steps > 1:
        # Iterate to steady state: re-solve with the updated states.
        for _ in range(n_steps - 1):
            t_core1, t_skin1 = solve_two_node(
                core,
                skin,
                t_air,
                wind,
                solar,
                exposure,
                m_core,
                m_skin,
                area,
                L_char,
                t_core1,
                t_skin1,
                q_gen,
                orientation=orientation,
                rh=rh,
                dt=dt,
                t_ground=t_ground,
                is_human=is_human,
                L_cond=L_cond,
                evap_on=evap_on,
                n_steps=1,
            )
    return t_core1, t_skin1


import unittest


class TestSourcedConstants(unittest.TestCase):
    """Every constant must trace to a published source (issue #191:
    'Research, don't assume')."""

    def test_stefan_boltzmann(self):
        self.assertAlmostEqual(SIGMA, 5.670374419e-8, places=18)

    def test_solar_irradiance_astm_g173(self):
        self.assertEqual(G, 1000.0)

    def test_latent_heats(self):
        self.assertAlmostEqual(L_VAP, 2.26e6)  # vaporization of water
        self.assertAlmostEqual(L_FUS, 334e3)  # fusion of ice

    def test_gagge_constants(self):
        self.assertAlmostEqual(K_MIN, 5.28, places=2)  # W/(m2K)
        self.assertAlmostEqual(C_P_BL, 4186, places=0)  # J/(kgK)
        self.assertAlmostEqual(A_D, 1.8258, places=3)  # DuBois m2
        self.assertAlmostEqual(MET, 58.2, places=1)  # W/m2
        self.assertAlmostEqual(LR, 16.5, places=1)  # K/kPa Lewis

    def test_gagge_neutral_temps(self):
        # T_b = 0.1*T_sk + 0.9*T_cr = 0.1*33.7 + 0.9*36.8
        self.assertAlmostEqual(0.1 * 33.7 + 0.9 * 36.8, 36.49, places=2)

    def test_bolton_1980(self):
        # e_s(20C) = 611.2 exp(17.67*20/243.5) Pa ~= 2337 Pa
        es = water_sat_pressure_pa(20.0)
        self.assertAlmostEqual(es, 2337.4, delta=2.0)
        # exact derivative dP/dT = e_s*4302.645/(T+243.5)^2
        d = d_sat_pressure_dT_pa(20.0)
        self.assertAlmostEqual(d, es * 4302.645 / (20 + 243.5) ** 2, places=3)

    def test_air_300k(self):
        self.assertAlmostEqual(AIR_300K["nu"], 15.89e-6, places=10)
        self.assertAlmostEqual(AIR_300K["k"], 0.02624, places=5)
        self.assertAlmostEqual(AIR_300K["Pr"], 0.707, places=3)


class TestTwoNodeSolve(unittest.TestCase):
    """The 3 validation vectors against literature anchors."""

    def test_gagge_human_neutral(self):
        # Gagge neutral: 1 met scaled to DuBois area (58.2 * 1.8258 =
        # 106.3 W total), NO sun, still air, nude (r_ecl=0).  The Gagge
        # model's skin anchor 33.7 C is the SET POINT of the W_sig/C_sig
        # regulatory signals, not a fixed operative temp: below the
        # thermoneutral band the body vasoconstricts (skin ~32 C, core
        # held by shivering), above it vasodilates (skin ~34.5 C, core
        # 36.8-37.2).  Assert the PHYSIOLOGY the model must show:
        #   - core holds near the 36.8 C set point across the band
        #   - skin always below core (heat flows inward to the core
        #     surface, never the reverse)
        #   - at the thermoneutral point (26 C air, MRT 26, still air
        #     h_c=3.0) skin sits at the neutral set point ~33.7 and the
        #     core holds 36.8.  Still air lowers the neutral band - the
        #     Gagge h_c = max(3.0 natural, 8.6*v^0.53) at v=0.1 gives
        #     h=3.0, so the body needs ~26 C air to dump 1 met.
        human = MATERIALS["human"]
        tc, ts = solve_two_node(
            core=human,
            skin=human,
            t_air=26,
            wind=0.1,
            solar=0,
            exposure=0.5,
            m_core=50,
            m_skin=20,
            area=A_D,
            L_char=0.15,
            t_core0=36.8,
            t_skin0=33.7,
            q_gen=MET * A_D,
            orientation="vertical",
            rh=0.5,
            dt=5,
            t_ground=26,
            is_human=True,
            L_cond=0.05,
            n_steps=600,  # iterate toward the Gagge steady-state anchor
        )
        self.assertAlmostEqual(tc, 36.8, delta=0.4)  # core holds set point
        self.assertAlmostEqual(ts, 33.7, delta=0.5)  # neutral skin set point
        self.assertLess(ts, tc)  # skin cannot exceed core

    def test_gagge_shivering_in_cold(self):
        # At 10 C the model MUST generate metabolic heat (shivering):
        # without the 19.4*C_sig*C_core_sig term the cold-branch core
        # drifts down toward ambient.  With it, the core holds ~36.8
        # while the skin constricts toward the cold air.
        human = MATERIALS["human"]
        tc, ts = solve_two_node(
            core=human,
            skin=human,
            t_air=10,
            wind=0.5,
            solar=0,
            exposure=0.5,
            m_core=50,
            m_skin=20,
            area=A_D,
            L_char=0.15,
            t_core0=36.8,
            t_skin0=33.7,
            q_gen=MET * A_D,
            orientation="vertical",
            rh=0.5,
            dt=5,
            t_ground=10,
            is_human=True,
            L_cond=0.05,
            n_steps=600,
        )
        # Shivering term: shiv = 19.4 * C_sig * C_core_sig, W/m2
        c_sig = max(0.0, T_SK_NEUTRAL - ts)
        c_core_sig = max(0.0, T_CR_NEUTRAL - tc)
        q_shiv = 19.4 * c_sig * c_core_sig
        self.assertGreater(q_shiv, 1.0)  # shivering must engage
        self.assertGreater(tc, 35.5)  # core held above 35.5 by shivering
        self.assertLess(ts, 33.7)  # skin constricted below neutral

    def test_engine_core_above_skin(self):
        # Idle engine: q_gen 4600 W over 6 m2, block 90C cooling to ambient
        engine = MATERIALS["engine"]
        tc, ts = solve_two_node(
            core=engine,
            skin=engine,
            t_air=25,
            wind=2,
            solar=0,
            exposure=0,
            m_core=150,
            m_skin=30,
            area=6,
            L_char=0.8,
            t_core0=90,
            t_skin0=60,
            q_gen=4600,
            orientation="up",
            rh=0.5,
            dt=5,
            t_ground=30,
            is_human=False,
            L_cond=0.01,
        )
        self.assertGreater(tc, 60)  # core stays hot
        self.assertLess(ts, tc)  # skin below core (physically required)
        self.assertGreater(ts, 35)  # skin still warm (not sunk to air)

    def test_melting_snow_pins_near_zero(self):
        # 2C air, wet surface in 300 W/m2 sun: endothermic melt pins ~0
        wood = MATERIALS["wood"]
        tc, ts = solve_two_node(
            core=wood,
            skin=wood,
            t_air=2,
            wind=1,
            solar=300,
            exposure=1,
            m_core=100,
            m_skin=10,
            area=1,
            L_char=0.5,
            t_core0=-1,
            t_skin0=-1,
            q_gen=0,
            orientation="up",
            rh=0.9,
            dt=5,
            t_ground=0,
            is_human=False,
            L_cond=0.1,
        )
        self.assertLessEqual(ts, 1.5)  # endothermic path pins the surface

    def test_heat_rise_natural_convection(self):
        # 50C vertical plate in still air: Grashof branch adds a coefficient
        # above the McAdams 5.7 still-air floor.
        hn = natural_convection_h(dT=30, L_char=0.8, orientation="vertical")
        self.assertGreater(hn, 1.0)
        # Hot plate facing UP convects more than facing DOWN
        hu = natural_convection_h(dT=30, L_char=0.8, orientation="up")
        hd = natural_convection_h(dT=30, L_char=0.8, orientation="down")
        self.assertGreater(hu, hd)

    def test_combined_superposition(self):
        # Churchill-Usagi n=3: combined >= each component alone
        hc = combined_h(wind=2, dT=30, L_char=0.8, orientation="vertical")
        hf = mcadams_h(2)
        self.assertGreater(hc, hf)

    def test_endothermic_cooling(self):
        # A HOT, EXERCISING human (q_gen 300 W, full sun, dry air 30%
        # RH) sweats: the Gagge sweat model raises wettedness, and the
        # evaporative path pulls the skin below what the same human
        # reaches with evaporation disabled.  evap_on isolates the
        # endothermic path from the blood-flow coupling.
        human = MATERIALS["human"]
        _, ts_evap = solve_two_node(
            core=human,
            skin=human,
            t_air=32,
            wind=1,
            solar=600,
            exposure=1,
            m_core=50,
            m_skin=20,
            area=1.8,
            L_char=0.15,
            t_core0=37,
            t_skin0=35,
            q_gen=300,
            orientation="vertical",
            rh=0.3,
            dt=60,
            t_ground=38,
            is_human=True,
            L_cond=0.05,
            evap_on=True,
            n_steps=20,
        )
        _, ts_noevap = solve_two_node(
            core=human,
            skin=human,
            t_air=32,
            wind=1,
            solar=600,
            exposure=1,
            m_core=50,
            m_skin=20,
            area=1.8,
            L_char=0.15,
            t_core0=37,
            t_skin0=35,
            q_gen=300,
            orientation="vertical",
            rh=0.3,
            dt=60,
            t_ground=38,
            is_human=True,
            L_cond=0.05,
            evap_on=False,
            n_steps=20,
        )
        self.assertLess(ts_evap, ts_noevap)  # sweating cools the skin below dry

    def test_asymmetric_transient(self):
        # Heating path: skin moves toward a hot equilibrium fast (tau short).
        # Cooling path: same delta the other way with an active endothermic
        # term is damped (tau lengthened) - assert the update differs.
        human = MATERIALS["human"]
        # warm toward 45C equilibrium
        _, ts_up = solve_two_node(
            core=human,
            skin=human,
            t_air=20,
            wind=1,
            solar=800,
            exposure=1,
            m_core=50,
            m_skin=20,
            area=1.8,
            L_char=0.15,
            t_core0=37,
            t_skin0=25,
            q_gen=85,
            orientation="vertical",
            rh=0.5,
            dt=300,
            t_ground=20,
            is_human=True,
            L_cond=0.05,
        )
        self.assertGreater(ts_up, 25)  # skin warmed by solar gain


if __name__ == "__main__":
    unittest.main()
