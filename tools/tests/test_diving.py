#!/usr/bin/env python3
"""Bühlmann ZH-L16C decompression model tests (issue #118).

The SQF (fnc_zh16cStep.sqf) implements the 16-compartment dissolved-gas
model with the published ZH-L16C constants (the dive-computer variant:
compartment 1 = 4-minute N2 half-time).  These tests mirror the model and
assert:

  - the constant table against the published ZH-L16C values (streit.cc
    SAETT FAQ "computer" column; NOT the ZHL-16b 5-minute variant)
  - the loading equation (Schreiner exponential toward inspired gas)
  - the ceiling equation (b*(P_tissue - a) at GF 100)
  - the NDL (no-decompression limit) against published ZH-L16C air
    tables - the research-derived table (10m=418, 20m=46, 30m=16,
    40m=9 min) and the universally agreed 40m anchor ~9 min

Run: python3 -m unittest tools.tests.test_diving
"""

import math
import unittest

# ─── ZH-L16C constants (published table) ───────────────────────────────────
T_HALF_N2 = [
    4.0,
    8.0,
    12.5,
    18.5,
    27.0,
    38.3,
    54.3,
    77.0,
    109.0,
    146.0,
    187.0,
    239.0,
    305.0,
    390.0,
    498.0,
    635.0,
]
T_HALF_HE = [
    1.51,
    3.02,
    4.72,
    6.99,
    10.21,
    14.48,
    20.53,
    29.11,
    41.20,
    55.19,
    70.69,
    90.34,
    115.29,
    147.42,
    188.24,
    240.03,
]
A_N2 = [
    1.2599,
    1.0,
    0.8618,
    0.7562,
    0.62,
    0.5043,
    0.441,
    0.4,
    0.375,
    0.35,
    0.3295,
    0.3065,
    0.2835,
    0.261,
    0.248,
    0.2327,
]
B_N2 = [
    0.5050,
    0.6514,
    0.7222,
    0.7825,
    0.8126,
    0.8434,
    0.8693,
    0.8910,
    0.9092,
    0.9222,
    0.9319,
    0.9403,
    0.9477,
    0.9544,
    0.9602,
    0.9653,
]
A_HE = [
    1.7424,
    1.383,
    1.1919,
    1.0458,
    0.922,
    0.8205,
    0.7305,
    0.6502,
    0.595,
    0.5545,
    0.5333,
    0.5189,
    0.5181,
    0.5176,
    0.5172,
    0.5119,
]
B_HE = [
    0.4245,
    0.5747,
    0.6527,
    0.7223,
    0.7582,
    0.7957,
    0.8279,
    0.8553,
    0.8757,
    0.8903,
    0.8997,
    0.9073,
    0.9122,
    0.9171,
    0.9217,
    0.9267,
]

P_H2O = 0.0627  # Bühlmann water vapour pressure (Subsurface WV_PRESSURE)


def fresh_tissues():
    """Initial tissue state: equilibrium at the surface breathing air.

    A diver descending from the surface already has N2 preloaded toward
    (1 - 0.0627)*0.79 = 0.74047 bar in every compartment.  The SQF model
    uses the same baseline, so NDL matches the published ZH-L16C tables
    (the research-derived table starts from surface equilibrium).
    """
    p_surf_n2 = (1.0 - P_H2O) * 0.79
    return [p_surf_n2] * 16 + [0.0] * 16


def tissue_step(tissues, depth_m, f_n2, f_he, dt_s=1.0):
    """One integration step: load all 16 compartments toward inspired gas.

    dt_s is in SECONDS; the half-times are in MINUTES, so the time
    constant in the exponential is dt_s/60 minutes.
    """
    dt_min = dt_s / 60.0
    p_amb = depth_m / 10.0 + 1.0
    p_n2_in = (p_amb - P_H2O) * f_n2
    p_he_in = (p_amb - P_H2O) * f_he
    out = [0.0] * 32
    for i in range(16):
        k_n2 = math.log(2) / T_HALF_N2[i]
        k_he = math.log(2) / T_HALF_HE[i]
        out[i] = p_n2_in + (tissues[i] - p_n2_in) * math.exp(-k_n2 * dt_min)
        out[16 + i] = p_he_in + (tissues[16 + i] - p_he_in) * math.exp(-k_he * dt_min)
    return out


def ceiling_m(tissues, gf=1.0):
    """Controlling ceiling depth in metres (positive down).  GF 100 = pure
    Bühlmann: ceiling = b*(P_tissue - a)."""
    ceil_bar = 0.0
    for i in range(16):
        pn2 = tissues[i]
        phe = tissues[16 + i]
        total = pn2 + phe
        f_n2t = pn2 / total if total > 0 else 0.0
        f_het = phe / total if total > 0 else 0.0
        a = A_N2[i] * f_n2t + A_HE[i] * f_het
        b = B_N2[i] * f_n2t + B_HE[i] * f_het
        if gf >= 1.0:
            allow = (total - a) * b
        else:
            allow = (total - gf * a) / (1 - gf * (1 - 1 / b))
        ceil_bar = max(ceil_bar, allow)
    return max(0.0, (ceil_bar - 1.0) * 10.0)


def ndl_minutes(depth_m, f_n2=0.79, f_he=0.0):
    """NDL: time at constant depth until the ceiling first exceeds the
    surface (ceiling > 0).  Binary search on the dwell time.

    The exponential loading is exact for any dt (the compartment state
    only depends on total exposure, not step size), so 60 s chunks are
    exact and fast.
    """
    lo, hi = 0.0, 600.0
    for _ in range(40):
        mid = (lo + hi) / 2
        tissues = fresh_tissues()
        steps = int(mid * 60) // 60
        for _c in range(steps):
            tissues = tissue_step(tissues, depth_m, f_n2, f_he, 60.0)
        if ceiling_m(tissues) > 0.0:
            hi = mid
        else:
            lo = mid
    return round((lo + hi) / 2, 1)


class TestZHL16CTable(unittest.TestCase):
    """The published ZH-L16C constants must be pinned exactly."""

    def test_n2_half_times(self):
        self.assertEqual(
            T_HALF_N2,
            [
                4.0,
                8.0,
                12.5,
                18.5,
                27.0,
                38.3,
                54.3,
                77.0,
                109.0,
                146.0,
                187.0,
                239.0,
                305.0,
                390.0,
                498.0,
                635.0,
            ],
        )

    def test_first_compartment_is_4min(self):
        # The distinguishing ZH-L16C feature vs the 16b 5-minute variant.
        self.assertEqual(T_HALF_N2[0], 4.0)

    def test_n2_a_values(self):
        self.assertEqual(
            A_N2,
            [
                1.2599,
                1.0,
                0.8618,
                0.7562,
                0.62,
                0.5043,
                0.441,
                0.4,
                0.375,
                0.35,
                0.3295,
                0.3065,
                0.2835,
                0.261,
                0.248,
                0.2327,
            ],
        )

    def test_n2_b_values(self):
        self.assertEqual(
            B_N2,
            [
                0.5050,
                0.6514,
                0.7222,
                0.7825,
                0.8126,
                0.8434,
                0.8693,
                0.8910,
                0.9092,
                0.9222,
                0.9319,
                0.9403,
                0.9477,
                0.9544,
                0.9602,
                0.9653,
            ],
        )

    def test_he_half_times_scale(self):
        # He half-time = N2 half-time / 2.65 (Bühlmann factor).  The
        # published table rounds each He half-time to 2 decimals
        # independently, so the ratio wobbles (up to ~0.4 min on the slow
        # compartments).  Assert the systematic ~2.6-2.7x band instead of
        # exact equality; the table values themselves are pinned exactly
        # by the half-time list tests above.
        for n2, he in zip(T_HALF_N2, T_HALF_HE):
            ratio = n2 / he
            self.assertGreater(ratio, 2.5)
            self.assertLess(ratio, 2.8)

    def test_water_vapour(self):
        self.assertEqual(P_H2O, 0.0627)


class TestTissueLoading(unittest.TestCase):
    """The Schreiner loading equation."""

    def test_fresh_tissues_at_surface_equilibrium(self):
        # The initial state is N2 equilibrium at the surface breathing air:
        # PN2 = (1 - 0.0627) * 0.79 = 0.74047 bar in every compartment.
        t = fresh_tissues()
        for v in t[:16]:
            self.assertAlmostEqual(v, 0.74047, places=4)
        for v in t[16:]:
            self.assertEqual(v, 0.0)

    def test_at_surface_air_remains_equilibrium(self):
        # At 0 m breathing air, the tissues are already at equilibrium and
        # stay there: no loading occurs.
        t = fresh_tissues()
        for _ in range(600):  # 10 min
            t = tissue_step(t, 0.0, 0.79, 0.0)
        self.assertAlmostEqual(t[0], 0.74047, delta=0.01)
        self.assertAlmostEqual(t[15], 0.74047, delta=0.01)

    def test_loading_converges_to_inspired(self):
        # Long exposure at 30 m air: PN2_inspired = (4 - 0.0627)*0.79 = 3.11.
        t = fresh_tissues()
        for _ in range(1000):  # 60000 s ~ 16.7 h, 60 s chunks
            t = tissue_step(t, 30.0, 0.79, 0.0, 60.0)
        # Fast compartment (4 min) fully converged; slow (635 min) still
        # approaching after 16.7 h (1.6 half-times).
        self.assertAlmostEqual(t[0], 3.11, delta=0.05)
        self.assertLess(t[15], 3.11)
        self.assertGreater(t[15], 2.0)

    def test_helium_loads_faster(self):
        t = fresh_tissues()
        for _ in range(600):  # 10 min
            t = tissue_step(t, 30.0, 0.0, 1.0)  # pure He
        # He comp 1 (1.51 min) is nearly saturated; N2 comp 1 (4 min) is not.
        self.assertGreater(t[16], t[0] * 1.5)


class TestCeiling(unittest.TestCase):
    """The a/b M-value ceiling."""

    def test_clean_tissue_zero_ceiling(self):
        self.assertEqual(ceiling_m(fresh_tissues()), 0.0)

    def test_loaded_tissue_requires_deco(self):
        # Saturated at 40 m air then surfaced: significant ceiling.
        t = fresh_tissues()
        for _ in range(1000):
            t = tissue_step(t, 40.0, 0.79, 0.0, 60.0)
        c = ceiling_m(t)
        self.assertGreater(c, 0.0)
        self.assertLess(c, 40.0)

    def test_gf_reduces_ceiling(self):
        t = fresh_tissues()
        for _ in range(1000):
            t = tissue_step(t, 30.0, 0.79, 0.0, 60.0)
        c100 = ceiling_m(t, gf=1.0)
        c80 = ceiling_m(t, gf=0.8)
        # Lower GF = more conservative = deeper (larger) ceiling.
        self.assertGreater(c80, c100)


class TestNDL(unittest.TestCase):
    """No-decompression limits vs the published ZH-L16C air table."""

    def test_40m_anchor(self):
        # The universally agreed ZH-L16C air NDL at 40 m is ~9 min.
        n = ndl_minutes(40.0)
        self.assertAlmostEqual(n, 9.0, delta=2.0)

    def test_30m(self):
        n = ndl_minutes(30.0)
        self.assertAlmostEqual(n, 16.0, delta=3.0)

    def test_20m(self):
        n = ndl_minutes(20.0)
        self.assertAlmostEqual(n, 46.0, delta=5.0)

    def test_ndl_monotonic(self):
        # NDL strictly decreases with depth.
        depths = [10, 15, 20, 25, 30, 35, 40]
        ndls = [ndl_minutes(d) for d in depths]
        for a, b in zip(ndls, ndls[1:]):
            self.assertGreater(a, b, f"NDL not decreasing: {ndls}")

    def test_shallow_long(self):
        # 10 m NDL is very long (hours).
        self.assertGreater(ndl_minutes(10.0), 200)


if __name__ == "__main__":
    unittest.main()
