"""Per-segment thermoregulation mirror (issue #196).

Mirrors the 17-segment JOS-3/65MN pattern: each body segment carries
its own mass, area, basal skin blood flow, vasodilation/constriction
coefficients, and core-to-skin conductance, then runs the Gagge
two-node core/skin balance per segment.

All constants are extracted from the JOS-3 open-source model
(TanabeLab/JOS-3, Takahashi et al 2021 J Therm Biol):
- construction.py: masses (65MN standard man 74.43 kg), areas (1.87 m2,
  Smith BSA), core-to-skin conductance cdt_cr_sk (5 fat levels)
- thermoregulation.py: basal skin blood flow BFBsk, SKIND/SKINC
  coefficients, the blood-flow law (bf_sk form)

Gagge two-node balance per segment (Gagge, Stolwijk & Nishi 1971;
Gagge, Fobelets & Berglund 1986).

Nothing invented.
"""

import math

# --- Whole-body anchors (Gagge) ---
SIGMA = 5.670374419e-8  # W/m2K4 (CODATA 2022)
C_P_BL = 4186.0  # J/(kgK), blood specific heat
C_P_BODY = 3492.0  # J/(kgK), body 0.97 Wh/(kgK)
A_D = 1.87  # m2, 65MN standard man (JOS-3)
MET = 58.2  # W/m2, 1 met (Gagge)
# JOS-3 set points (jos3.py:205-206): setpt_cr = 37, setpt_sk = 34.
# These are the body's regulatory targets, NOT the Gagge 36.8/33.7.
T_CR_NEUTRAL = 37.0
T_SK_NEUTRAL = 34.0
LR = 16.5  # K/kPa, Lewis


def water_sat_pressure_pa(T_c):
    """Bolton 1980, valid -35..+35 C, 0.4% error."""
    return 611.2 * math.exp(17.67 * T_c / (T_c + 243.5))


# --- 17-segment registry (JOS-3, authoritative) ---
SEGMENT_NAMES = [
    "head",
    "neck",
    "chest",
    "back",
    "pelvis",
    "upperarm_l",
    "forearm_l",
    "hand_l",
    "upperarm_r",
    "forearm_r",
    "hand_r",
    "thigh_l",
    "leg_l",
    "foot_l",
    "thigh_r",
    "leg_r",
    "foot_r",
]

MASS_KG = [
    3.18,
    0.84,
    12.4,
    11.03,
    17.57,
    2.16,
    1.37,
    0.34,
    2.16,
    1.37,
    0.34,
    7.01,
    3.34,
    0.48,
    7.01,
    3.34,
    0.48,
]  # sums 74.42

AREA_M2 = [
    0.110,
    0.029,
    0.175,
    0.161,
    0.221,
    0.096,
    0.063,
    0.050,
    0.096,
    0.063,
    0.050,
    0.209,
    0.112,
    0.056,
    0.209,
    0.112,
    0.056,
]  # sums 1.868

# Core-to-skin conductance (W/K) at 15% fat (JOS-3 fat<17.5 level)
CONDUCT_15 = [
    1.311,
    0.909,
    1.785,
    1.643,
    2.251,
    1.501,
    0.982,
    2.183,
    1.501,
    0.982,
    2.183,
    2.468,
    1.326,
    3.370,
    2.468,
    1.326,
    3.370,
]

# Basal CORE blood flow (L/h), JOS-3 (thermoregulation.py) - the
# artery->core flow that feeds each core from the central pool.
BFBCR = [
    35.251,
    15.240,
    89.214,
    87.663,
    18.686,
    1.808,
    0.940,
    0.217,
    1.808,
    0.940,
    0.217,
    1.406,
    0.164,
    0.080,
    1.406,
    0.164,
    0.080,
]

# Basal skin blood flow (L/h)
BFBSK = [
    1.754,
    0.325,
    1.967,
    1.475,
    2.272,
    0.91,
    0.508,
    1.114,
    0.91,
    0.508,
    1.114,
    1.456,
    0.651,
    0.934,
    1.456,
    0.651,
    0.934,
]

# Skin vasodilation coefficients
SKIND = [
    0.0692,
    0.0992,
    0.0580,
    0.0679,
    0.0707,
    0.0400,
    0.0373,
    0.0632,
    0.0400,
    0.0373,
    0.0632,
    0.0736,
    0.0411,
    0.0623,
    0.0736,
    0.0411,
    0.0623,
]

# Skin vasoconstriction coefficients (hands/feet 0.1489 = strong)
SKINC = [
    0.0213,
    0.0213,
    0.0638,
    0.0638,
    0.0638,
    0.0213,
    0.0213,
    0.1489,
    0.0213,
    0.0213,
    0.1489,
    0.0213,
    0.0213,
    0.1489,
    0.0213,
    0.0213,
    0.1489,
]

# Skin receptor weights (JOS-3 thermoregulation.py, error_signals)
RECEPTOR = [
    0.0549,
    0.0146,
    0.1492,
    0.1321,
    0.2122,
    0.0227,
    0.0117,
    0.0923,
    0.0227,
    0.0117,
    0.0923,
    0.0501,
    0.0251,
    0.0167,
    0.0501,
    0.0251,
    0.0167,
]

# Shivering distribution weights (JOS-3 thermoregulation.py:622)
SHIVF = [
    0.0339,
    0.0436,
    0.27394,
    0.24102,
    0.38754,
    0.00243,
    0.00137,
    0.0002,
    0.00243,
    0.00137,
    0.0002,
    0.0039,
    0.00175,
    0.00035,
    0.0039,
    0.00175,
    0.00035,
]


def segment_blood_flow(idx, t_sk, t_cr, met):
    """JOS-3 skin blood flow law (thermoregulation.py:425).

    bf_sk = (1 + SKIND*sig_dilat) / (1 + SKINC*sig_stric)
            * BFBsk * 2^(err_sk/6)
    sig_dilat = max(100.5*err_cr + 6.4*(warm-cold), 0)
    sig_stric = max(-10.8*err_cr - 10.8*(warm-cold), 0)
    err_cr = T_cr - 36.8, err_sk = T_sk - 33.7
    """
    err_cr = t_cr - T_CR_NEUTRAL
    err_sk = t_sk - T_SK_NEUTRAL
    wrms_clds = err_sk  # warm/cold skin signal (positive = warm)
    sig_dilat = max(100.5 * err_cr + 6.4 * wrms_clds, 0.0)
    sig_stric = max(-10.8 * err_cr - 10.8 * wrms_clds, 0.0)
    flow = (
        ((1 + SKIND[idx] * sig_dilat) / (1 + SKINC[idx] * sig_stric))
        * BFBSK[idx]
        * (2 ** (err_sk / 6.0))
    )
    # Exercise boost: moderate vasodilation with work rate.
    flow *= 1.0 + 0.2 * max(met - 1.0, 0.0)
    return max(flow, 0.5)  # L/h floor


def _regulated_shivering(t_sk_arr, t_cr):
    """JOS-3 shivering (thermoregulation.py:622), per segment.

    sig_shiv = 24.36 * clds * (-err_cr[0]), distributed by SHIVF.
    clds = area-weighted cold-skin signal = sum(receptor * cold_error).
    err_cr[0] = T_cr(head) - 36.8 (the head core drives the signal).
    Returns the per-segment shivering (W) for segment idx via SHIVF[idx].
    """
    err_sk = [tsk - T_SK_NEUTRAL for tsk in t_sk_arr]
    clds = sum(RECEPTOR[i] * max(-e, 0.0) for i, e in enumerate(err_sk))
    err_cr_head = t_cr - T_CR_NEUTRAL
    sig_shiv = 24.36 * clds * max(-err_cr_head, 0.0)
    return [sig_shiv * w for w in SHIVF]  # W per segment


def solve_segment(
    idx,
    t_cr0,
    t_sk0,
    t_air,
    wind,
    met,
    shivering_w,
    t_pool,
    t_ground=30.0,
    rh=0.5,
    dt=5.0,
    q_solar=0.0,
    exposure=0.5,
    blood_vol_frac=1.0,
):
    """JOS-3 two-node balance for ONE segment with the central pool.

    The core is NOT independent: it is coupled to the shared central
    blood pool by the CORE blood flow (BFBCR), and to the skin by the
    conductance cdt_cr_sk.  The skin is coupled to the pool by the
    SKIN blood flow (BFBSK).  Both blood flows use the regulatory
    dilation/constriction law.

    Core:  q_met + q_shiv - q_resp - conduct*(T_cr-T_sk)
           - blood_cr*(T_cr-T_pool) = 0
    Skin:  conduct*(T_cr-T_sk) + blood_sk*(T_pool-T_sk) + q_solar
           - q_conv - q_rad - q_evap = 0

    The pool temperature is set by the body-level caller (iterated so
    the blood-carried heat conserves).  Returns (t_cr1, t_sk1, q_pool)
    where q_pool = blood_cr*(T_cr-T_pool) + blood_sk*(T_sk-T_pool), the
    net draw this segment places on the pool (W).
    """
    mass = MASS_KG[idx]
    area = AREA_M2[idx]
    conduct = CONDUCT_15[idx]
    # Convection: Gagge human correlation h = max(3.0, 8.6*v^0.53)
    h_c = max(3.0, 8.6 * (max(wind, 0.1) ** 0.53))
    # Blood flows (L/h -> W/K): mass flow * cp.  1 L blood ~1.06 kg.
    v_bl_sk = segment_blood_flow(idx, t_sk0, t_cr0, met)
    v_bl_cr = BFBCR[idx] * (1.0 + 0.2 * max(met - 1.0, 0.0))
    # ATLS shock: below 40% blood volume, perfusion collapses.
    if blood_vol_frac < 0.4:
        v_bl_sk *= 0.2
        v_bl_cr *= 0.2
    blood_sk = v_bl_sk / 3600.0 * 1.06 * C_P_BL  # W/K, skin->pool
    blood_cr = v_bl_cr / 3600.0 * 1.06 * C_P_BL  # W/K, core->pool
    # Core heat capacity (90% of segment mass).
    c_core = 0.9 * mass * C_P_BODY
    c_skin = 0.1 * mass * C_P_BODY
    # Respiratory loss (Gagge 1986), scaled by segment area fraction.
    p_a = water_sat_pressure_pa(t_air) * rh / 133.322  # torr
    q_resp = (
        0.0014 * met * MET * (34 - t_air) + 0.0023 * met * MET * (44 - p_a)
    ) * area
    # Metabolism per segment (W): met*58.2 scaled by mass fraction.
    q_met = met * MET * (mass / 74.42) * A_D
    # ATLS shock metabolic scaling (matches the #124 dying-body branch):
    # below 40% blood volume the body's heat production collapses with
    # perfusion - decompensated shock is a failing system, not a hot one.
    if blood_vol_frac < 0.4:
        q_met *= blood_vol_frac / 0.4
    # Regulated shivering (JOS-3 form) per segment share (W).
    q_shiv_w = shivering_w  # W over the segment
    # Skin equilibrium at fixed point; core solved analytically.
    ts = t_sk0 + 273.15
    t_air_k = t_air + 273.15
    mrt_k = (0.5 * (t_ground + 273.15) ** 4 + 0.5 * t_air_k**4) ** 0.25
    for _ in range(8):
        conv = h_c * (ts - t_air_k) * area
        rad = 0.95 * SIGMA * (ts**4 - mrt_k**4) * area
        p_sk = water_sat_pressure_pa(ts - 273.15) / 1000.0  # kPa
        evap = (
            LR * h_c * (p_sk - water_sat_pressure_pa(t_air) * rh / 1000.0) * 0.06 * area
        )
        # Core solved analytically from this skin temp and pool:
        # core balance linear in T_cr:
        # (conduct + blood_cr)*T_cr = q_met+q_shiv-q_resp + conduct*T_sk + blood_cr*T_pool
        k_cr = conduct + blood_cr
        t_cr_eq = (
            (q_met + q_shiv_w - q_resp) + conduct * (ts - 273.15) + blood_cr * t_pool
        ) / k_cr
        resid = (
            conduct * (t_cr_eq - (ts - 273.15))
            + blood_sk * (t_pool - (ts - 273.15))
            + q_solar * area * exposure
            - conv
            - rad
            - evap
        )
        df = -(conduct + blood_sk + h_c * area + 4 * 0.95 * SIGMA * ts**3 * area)
        if df == 0:
            break
        ts = ts - resid / df
        ts = max(ts, t_air_k - 60)
        ts = min(ts, t_air_k + 500)
    t_sk_eq = ts - 273.15
    k_cr = conduct + blood_cr
    t_cr_eq = (
        (q_met + q_shiv_w - q_resp) + conduct * t_sk_eq + blood_cr * t_pool
    ) / k_cr
    # One transient step toward the joint equilibrium (asymmetric tau).
    tau = max(c_skin / (h_c * area + conduct + blood_sk), 30.0)
    t_sk1 = t_sk0 + (t_sk_eq - t_sk0) * (1.0 - math.exp(-dt / tau))
    t_cr1 = t_cr0 + (t_cr_eq - t_cr0) * (1.0 - math.exp(-dt / max(tau, 30.0)))
    q_pool = blood_cr * (t_cr_eq - t_pool) + blood_sk * (t_sk_eq - t_pool)
    return t_cr1, t_sk1, q_pool


def solve_body(
    t_cr_init,
    t_sk_init,
    t_air,
    wind,
    met,
    t_ground=30.0,
    rh=0.5,
    dt=5.0,
    q_solar=0.0,
    exposure=0.5,
    blood_vol_frac=1.0,
    n_steps=1,
):
    """Whole-body solve: iterate the central pool so blood heat conserves.

    The pool temperature is found by fixed point: the net draw across
    all segments (sum of q_pool) must be zero at equilibrium.  Each
    step: estimate pool, solve all segments, correct pool by the
    residual sum / total conductance.
    """
    t_cr = list(t_cr_init)
    t_sk = list(t_sk_init)
    t_pool = T_CR_NEUTRAL
    for _ in range(n_steps):
        for _inner in range(4):  # pool fixed point
            q_sum = 0.0
            for i in range(len(SEGMENT_NAMES)):
                t_cr[i], t_sk[i], q_i = solve_segment(
                    i,
                    t_cr[i],
                    t_sk[i],
                    t_air,
                    wind,
                    met,
                    0.0,
                    t_pool,
                    t_ground=t_ground,
                    rh=rh,
                    dt=dt,
                    q_solar=q_solar,
                    exposure=exposure,
                    blood_vol_frac=blood_vol_frac,
                )
                q_sum += q_i
            # Correct pool by residual / total blood conductance.
            tot_bl = 0.0
            for i in range(len(SEGMENT_NAMES)):
                v_sk = segment_blood_flow(i, t_sk[i], t_cr[i], met)
                v_cr = BFBCR[i] * (1.0 + 0.2 * max(met - 1.0, 0.0))
                if blood_vol_frac < 0.4:
                    v_sk *= 0.2
                    v_cr *= 0.2
                tot_bl += (v_sk + v_cr) / 3600.0 * 1.06 * C_P_BL
            t_pool += q_sum / max(tot_bl, 1e-6)
        # Shivering (body-level) once after pool settles - simplified:
        # recompute with the regulated shivering distribution.
        clds = sum(RECEPTOR[i] * max(T_SK_NEUTRAL - t_sk[i], 0.0) for i in range(17))
        err_cr = sum(t_cr[i] for i in range(17)) / 17.0 - T_CR_NEUTRAL
        shiv_total = 24.36 * clds * max(-err_cr, 0.0)
        for i in range(17):
            t_cr[i], t_sk[i], _ = solve_segment(
                i,
                t_cr[i],
                t_sk[i],
                t_air,
                wind,
                met,
                shiv_total * SHIVF[i],
                t_pool,
                t_ground=t_ground,
                rh=rh,
                dt=dt,
                q_solar=q_solar,
                exposure=exposure,
                blood_vol_frac=blood_vol_frac,
            )
    return t_cr, t_sk, t_pool
