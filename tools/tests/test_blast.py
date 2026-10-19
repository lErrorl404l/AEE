#!/usr/bin/env python3
"""Blast overpressure and injury tests (issue #132).

Mirrors fnc_calculateBlastOverpressure.sqf (Kingery-Bulmash / Swisdak
1994 simplified fits) and fnc_calculateBlastInjury.sqf (Bowen 1968 P-I
curves + measured tertiary blowdown).

The reference values are verified against the `kingery-bulmash` pip
package (fcento100, Swisdak ADA526744) and the issue's published anchors:
  Z=1 -> 1353.7 kPa, Z=2 -> 283.7, Z=5 -> 43.2, Z=10 -> 14.9.

Run: python3 -m unittest tools.tests.test_blast
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402


# ─── Mirrors ───────────────────────────────────────────────────────────────


def kb_incident_pressure(z):
    """Swisdak simplified KB incident overpressure fit (kPa).  Inside the
    fit's lower bound (contact range) Z is held at 0.2, as the SQF does."""
    z = max(z, 0.2)
    if z > 198.5:
        return 0.0
    lnz = math.log(z)
    if z <= 2.9:
        a, b, c, d, e = 7.2106, -2.1069, -0.3229, 0.1117, 0.0685
    elif z <= 23.8:
        a, b, c, d, e = 7.5938, -3.0523, 0.40977, 0.0261, -0.01267
    else:
        a, b = 6.0536, -1.4066
        c = d = e = 0.0
    return math.exp(a + b * lnz + c * lnz**2 + d * lnz**3 + e * lnz**4)


def kb_positive_duration(z, w):
    """Swisdak simplified KB positive-phase duration fit (ms)."""
    z = max(z, 0.2)
    if not (0.2 <= z <= 40):
        return 0.0
    lnz = math.log(z)
    if z <= 1.02:
        a, b, c, d, e, f = 0.5426, 3.2299, -1.5931, -5.9667, -4.0815, -0.9149
    elif z <= 2.8:
        a, b, c, d, e, f = 0.5440, 2.7082, -9.7354, 14.3425, -9.7791, 2.8535
    else:
        a, b, c, d, e, f = -2.4608, 7.1639, -5.6215, 2.2711, -0.44994, 0.03486
    return w * math.exp(a + b * lnz + c * lnz**2 + d * lnz**3 + e * lnz**4 + f * lnz**5)


def blast_overpressure(mass_kg, distance_m):
    """Mirror of fnc_calculateBlastOverpressure.sqf: [P_so kPa, t_d ms]."""
    if mass_kg <= 0 or distance_m <= 0:
        return [0.0, 0.0]
    w = mass_kg ** (1 / 3)
    z = distance_m / w
    return [kb_incident_pressure(z), kb_positive_duration(z, w)]


# Bowen P-I rows: [t_d, thresh, 1%, 50%, 99%]
BOWEN_ROWS = [
    [10, 55, 150, 200, 300],
    [50, 42, 110, 160, 220],
    [200, 28, 90, 125, 185],
]


def _interp(a, b, w):
    return a + (b - a) * w


def blast_injury(p_so, td, indoor_mult=1.0):
    """Mirror of fnc_calculateBlastInjury.sqf.

    Returns [eardrum01, lungThresh01, lung1Pct01, lung50Pct01, lung99Pct01,
             throw01].
    """
    P = p_so * max(indoor_mult, 1.0)
    if P <= 0:
        return [0.0] * 6

    # Eardrum: 35/103/202 -> 0/50/100%
    if P >= 202:
        eardrum = 1.0
    elif P >= 103:
        eardrum = 0.5 + (P - 103) * (0.5 / 99)
    elif P > 35:
        eardrum = (P - 35) * (0.5 / 68)
    else:
        eardrum = 0.0

    # Lung: interpolate thresholds in log-t_d, probability linearly.
    t = max(0.1, min(td, 200))
    if t <= 10:
        r0, r1, w = BOWEN_ROWS[0], BOWEN_ROWS[0], 0.0
    elif t >= 200:
        r0, r1, w = BOWEN_ROWS[2], BOWEN_ROWS[2], 0.0
    else:
        if t < 50:
            r0, r1 = BOWEN_ROWS[0], BOWEN_ROWS[1]
        else:
            r0, r1 = BOWEN_ROWS[1], BOWEN_ROWS[2]
        w = (math.log(t) - math.log(r0[0])) / (math.log(r1[0]) - math.log(r0[0]))
        w = max(0.0, min(1.0, w))
    thr = [_interp(r0[i], r1[i], w) for i in range(1, 5)]

    if P >= thr[3]:
        lung_thresh = 1.0
    elif P > thr[0]:
        if P < thr[1]:
            lung_thresh = (P - thr[0]) * (1 / (thr[1] - thr[0])) / 100
        elif P < thr[2]:
            lung_thresh = (1 + (P - thr[1]) * (49 / (thr[2] - thr[1]))) / 100
        else:
            lung_thresh = (50 + (P - thr[2]) * (49 / (thr[3] - thr[2]))) / 100
    else:
        lung_thresh = 0.0
    lung_thresh = max(0.0, min(1.0, lung_thresh))

    lung1 = 0.01 if P >= thr[1] else 0.0
    lung50 = 0.5 if P >= thr[2] else 0.0
    lung99 = 1.0 if P >= thr[3] else 0.0

    # Tertiary blowdown: Richmond & Fletcher dummy anchors (JRC119310
    # Table 3), log-interpolated in the dynamic-pressure impulse.
    qo = 2.5 * P * P / (7 * 101.325 + P)
    jq = qo * max(td, 0.0) / 2
    if jq <= 8.78:
        throw01 = 0.0
    elif jq >= 379.13:
        throw01 = 1.0
    elif jq >= 58.27:
        throw01 = 0.5 + 0.5 * (math.log(jq / 58.27) / math.log(379.13 / 58.27))
    else:
        throw01 = 0.5 * (math.log(jq / 8.78) / math.log(58.27 / 8.78))

    return [eardrum, lung_thresh, lung1, lung50, lung99, throw01]


# ─── Corpse blast throw (issue #160) ──────────────────────────────────────

P0_KPA = 101.325
RHO0 = 1.225


def blast_throw(p_so, td, mass_kg):
    """Mirror of fnc_calculateBlastThrow.sqf: [throwSpeed, tumbleRate]."""
    if p_so <= 0 or td <= 0 or mass_kg <= 0:
        return [0.0, 0.0]
    qo = 2.5 * p_so**2 / (7 * P0_KPA + p_so)  # kPa
    u = math.sqrt(2 * (qo * 1000) / RHO0)  # m/s
    cd, area = 1.2, 0.7
    j = cd * (qo * 1000) * area * (td / 1000)  # N.s
    dv = j / mass_kg
    dv = min(dv, u, 55.0)  # wind cap, then ceiling
    c_com, h, k = 0.57, 1.75, 0.30
    d = (c_com - 0.5) * h
    omega = dv * d / (k * k)
    return [dv, omega]


# ─── Tests ────────────────────────────────────────────────────────────────


class TestKBOverpressure(unittest.TestCase):
    """The Swisdak/KB fit must reproduce the published anchors."""

    def test_anchors(self):
        # Issue spec: Z=1 -> 1357, Z=2 -> 284, Z=5 -> 43.2, Z=10 -> 14.8 kPa.
        self.assertAlmostEqual(kb_incident_pressure(1.0), 1353.7, delta=5)
        self.assertAlmostEqual(kb_incident_pressure(2.0), 283.7, delta=5)
        self.assertAlmostEqual(kb_incident_pressure(5.0), 43.2, delta=2)
        self.assertAlmostEqual(kb_incident_pressure(10.0), 14.9, delta=1)

    def test_matches_pip_package(self):
        # Cross-check against the installed kingery-bulmash package.
        try:
            import kingery_bulmash as kb
        except ImportError:
            self.skipTest("kingery-bulmash not installed in this python")
        for z in [0.3, 0.8, 1.5, 3.0, 6.0, 12.0, 20.0]:
            r = kb.Blast_Parameters(
                unit_system=kb.Units.METRIC, neq=1.0, distance=z, safe=False
            )
            ref = r.incident_pressure or 0.0
            got = kb_incident_pressure(z)
            self.assertAlmostEqual(got, ref, delta=max(ref * 0.05, 1.0), msg=f"Z={z}")

    def test_monotonic_decreasing(self):
        zs = [x / 10 for x in range(2, 200, 5)]
        ps = [kb_incident_pressure(z) for z in zs]
        for a, b in zip(ps, ps[1:]):
            self.assertGreaterEqual(a, b, "P_so rose with Z")

    def test_mass_scaling(self):
        # Z = R/W^(1/3): double the mass at the same range halves the
        # scaled distance -> much higher pressure (not inverse-cube).
        p1 = blast_overpressure(7, 5)[0]  # 155mm M107 at 5 m
        p2 = blast_overpressure(100, 5)[0]  # Mk82 at 5 m
        self.assertGreater(p2, p1 * 2)

    def test_duration_scales_with_cuberoot_mass(self):
        # t_d scales with W^(1/3): 8x mass -> 2x duration at same Z.
        z = 3.0
        t1 = kb_positive_duration(z, 1.0)
        t8 = kb_positive_duration(z, 8.0 ** (1 / 3))
        self.assertAlmostEqual(t8, t1 * 2, delta=t1 * 0.1)


BLAST_INJURY_SQF = (
    Path(__file__).resolve().parents[2]
    / "addons/blast/functions/blast/fnc_calculateBlastInjury.sqf"
)
BLAST_THROW_SQF = (
    Path(__file__).resolve().parents[2]
    / "addons/blast/functions/blast/fnc_calculateBlastThrow.sqf"
)


class TestBlastInjurySqfMatchesTheMirror(unittest.TestCase):
    """The REAL kernel, executed, against the independent mirror above.

    Without this the mirror could drift from the shipped SQF unnoticed.
    """

    def test_the_sqf_matches_over_a_sweep(self):
        for p in (5, 20, 35, 60, 103, 160, 202, 300, 600):
            for td in (1, 5, 10, 30, 100, 200):
                with self.subTest(p=p, td=td):
                    got = run_sqf(BLAST_INJURY_SQF, [p, td, 1])
                    want = blast_injury(p, td)
                    for i, (g, w) in enumerate(zip(got, want)):
                        self.assertAlmostEqual(g, w, places=6, msg=f"slot {i}")

    def test_the_throw_kernel_uses_the_measured_drag_area(self):
        src = BLAST_THROW_SQF.read_text(encoding="utf-8")
        self.assertIn("_cdArea = 0.735", src)
        self.assertIn("Richmond & Fletcher", src)
        # 0.735 m2 is 0.01050 m/s per kPa.ms times the 70 kg subject.
        self.assertAlmostEqual(0.010499 * 70, 0.735, places=3)


class TestBlastInjury(unittest.TestCase):
    """Bowen P-I curves + measured tertiary blowdown."""

    def test_eardrum_thresholds(self):
        # 35 threshold, 103 50%, 202 100%.
        self.assertEqual(blast_injury(30, 5)[0], 0.0)
        self.assertAlmostEqual(blast_injury(103, 5)[0], 0.5, places=2)
        self.assertEqual(blast_injury(202, 5)[0], 1.0)

    def test_lung_thresholds_short_duration(self):
        # t_d <= 10 ms row: 55/150/200/300.
        self.assertEqual(blast_injury(50, 5)[1], 0.0)
        self.assertAlmostEqual(blast_injury(150, 5)[1], 0.01, places=3)
        self.assertAlmostEqual(blast_injury(200, 5)[1], 0.5, places=2)
        self.assertEqual(blast_injury(300, 5)[1], 1.0)

    def test_lung_thresholds_long_duration(self):
        # t_d >= 200 ms row: 28/90/125/185 (more dangerous at long duration).
        # At 30 kPa the 28 kPa threshold IS exceeded (tiny but nonzero).
        self.assertLess(blast_injury(30, 300)[1], 0.01)
        self.assertAlmostEqual(blast_injury(90, 300)[1], 0.01, places=3)
        self.assertAlmostEqual(blast_injury(125, 300)[1], 0.5, places=2)
        self.assertEqual(blast_injury(185, 300)[1], 1.0)

    def test_duration_interpolation(self):
        # Between rows: longer duration is MORE dangerous at same P.
        p10 = blast_injury(160, 5)[1]  # row 10ms: 160 is between 150(1%)/200(50%)
        p100 = blast_injury(160, 100)[1]  # row 50-200 interpolated
        self.assertGreater(p100, p10, "longer duration should be more dangerous")

    def test_blowdown_follows_the_measured_anchors(self):
        # The anchors are stated as a dynamic-pressure impulse, so drive the
        # kernel with the (P, t_d) pairs that produce them.
        def jq(p, td):
            return 2.5 * p * p / (7 * 101.325 + p) * td / 2

        # Below the measured 8.78 kPa.ms no-blowdown anchor.
        self.assertLess(jq(20, 10), 8.78)
        self.assertEqual(blast_injury(20, 10)[5], 0.0)
        # 50 % blowdown at 58.27 kPa.ms.
        p50 = 20.0
        while jq(p50, 10) < 58.27:
            p50 += 0.01
        self.assertAlmostEqual(blast_injury(p50, 10)[5], 0.5, places=2)
        # A long positive phase blows a body down at a far lower peak.
        self.assertGreater(blast_injury(20, 200)[5], blast_injury(20, 10)[5])

    def test_indoor_amplification(self):
        # Indoor 2x: a 60 kPa outdoor shot becomes 120 kPa indoors.
        out = blast_injury(60, 10)
        ind = blast_injury(60, 10, indoor_mult=2)
        self.assertGreater(ind[0], out[0], "indoor eardrum higher")
        self.assertGreater(ind[1], out[1], "indoor lung higher")
        self.assertEqual(ind[0], blast_injury(120, 10)[0])

    def test_zero_pressure_no_injury(self):
        self.assertEqual(blast_injury(0, 10), [0.0] * 6)


class TestValidationTargets(unittest.TestCase):
    """KB-consistent blast distances for the issue's two weapons.

    NOTE: the issue's original validation numbers (M107: 99% lethal 4.4 m,
    eardrum 50% 6.5 m; Mk82: 99% 10.7 m, safe 46.4 m) were computed with
    the OLD WRONG cubic model the issue replaces (P = 0.84·(W^(1/3)/Z)^3,
    2-17x error).  The correct Kingery-Bulmash distances, from this
    implementation (verified against the kingery-bulmash pip package):
      M107 (7 kg):  lung99 3.73 m, eardrum50 6.07 m, 50% blowdown 7.03 m
      Mk82 (100 kg): lung99 9.06 m, eardrum50 14.72 m
    """

    def test_m107_155mm(self):
        # 7 kg TNT surface burst, KB-consistent distances.
        m = 7.0
        # 99% lethal at ~3.7 m; falls off by 5 m.
        self.assertAlmostEqual(
            blast_injury(*blast_overpressure(m, 3.73))[4], 1.0, delta=0.1
        )
        self.assertLess(blast_injury(*blast_overpressure(m, 5.0))[4], 0.6)
        # eardrum 50% at ~6.1 m.
        e65 = blast_injury(*blast_overpressure(m, 6.07))[0]
        self.assertGreater(e65, 0.4)
        self.assertLess(e65, 0.6)
        # Blowdown follows the measured dynamic-pressure impulse, so it
        # depends on the positive-phase duration, not the peak alone: a
        # 7 kg shell has a ~8 ms phase, giving 50 % blowdown at ~7.0 m and
        # nothing beyond ~13.3 m (the 8.78 kPa.ms no-blowdown anchor).
        self.assertAlmostEqual(blast_injury(*blast_overpressure(m, 7.03))[5], 0.5, delta=0.02)
        self.assertEqual(blast_injury(*blast_overpressure(m, 13.4))[5], 0.0)
        # The larger charge's longer phase blows a body down much further.
        self.assertAlmostEqual(
            blast_injury(*blast_overpressure(100.0, 22.72))[5], 0.5, delta=0.02
        )
        self.assertLess(blast_injury(*blast_overpressure(m, 21.0))[0], 0.1)

    def test_mk82(self):
        # 100 kg TNT surface burst, KB-consistent distances.
        m = 100.0
        self.assertAlmostEqual(
            blast_injury(*blast_overpressure(m, 9.06))[4], 1.0, delta=0.15
        )
        e15 = blast_injury(*blast_overpressure(m, 14.72))[0]
        self.assertGreater(e15, 0.4)
        self.assertLess(e15, 0.6)
        self.assertLess(blast_injury(*blast_overpressure(m, 50.0))[0], 0.1)

    def test_scaled_distance_equivalence(self):
        # The same Z gives the same overpressure regardless of charge mass.
        # Use the exact Z values (1.9522) from the lung99 search.
        z = 3.7345045944197084 / (7 ** (1 / 3))
        self.assertAlmostEqual(kb_incident_pressure(z), 300, delta=20)


class TestBlastThrow(unittest.TestCase):
    """The corpse blast-throw kernel (issue #160)."""

    def test_zero_inputs(self):
        self.assertEqual(blast_throw(0, 10, 80), [0.0, 0.0])
        self.assertEqual(blast_throw(20, 0, 80), [0.0, 0.0])
        self.assertEqual(blast_throw(20, 10, 0), [0.0, 0.0])

    def test_rises_with_overpressure(self):
        lo = blast_throw(20, 20, 80)[0]
        hi = blast_throw(60, 20, 80)[0]
        self.assertGreater(hi, lo)

    def test_500lb_bomb_body_thrown(self):
        # 227 kg charge at 25 m: above the throw threshold, a sane throw.
        p_so, td = blast_overpressure(227.0, 25.0)
        self.assertGreater(p_so, 15.0)
        dv, omega = blast_throw(p_so, td, 80.0)
        self.assertGreater(dv, 0.5)
        self.assertLess(dv, 20.0)
        self.assertGreater(omega, 0.0)

    def test_capped_at_ceiling(self):
        # Close in the impulse model over-predicts; the ceiling holds.
        dv, _ = blast_throw(1000, 50, 80)
        self.assertLessEqual(dv, 55.0)

    def test_tumble_scales_with_speed(self):
        _, o_lo = blast_throw(20, 20, 80)
        _, o_hi = blast_throw(60, 20, 80)
        self.assertGreater(o_hi, o_lo)


class TestAirburstFragmentDensity(unittest.TestCase):
    """Issue #252: the airburst areal density must carry the geometry factor.

    Executes the shipped kernel (tools/tests/sqf_lite.py), not a mirror.  For an
    isotropic burst at height h over a ground plane, the ground annulus
    [R, R+dR] subtends dOmega = 2*pi*sin(theta)*dtheta and has area
    2*pi*R*dR with R = h*tan(theta).  The number falling in it is
    (N*f/4*pi)*dOmega, so

        rho(R) = N*f*h / (4*pi*(R^2 + h^2)^(3/2))

    which carries the cos(theta)/s^2 obliquity.  The pre-fix form
    N*f/(4*pi*h*s) omits it and over-predicts by (R^2 + h^2)/h^2: 101x at
    R=50, h=5 and at R=100, h=10, 7.25x at R=50, h=20.
    """

    KERNEL = (
        Path(__file__).resolve().parents[2]
        / "addons"
        / "blast"
        / "functions"
        / "fragmentation"
        / "fnc_calculateFragmentDensity.sqf"
    )

    def density(self, n, f, r, h):
        return run_sqf(self.KERNEL, [n, f, r, h], {})

    @staticmethod
    def closed_form(n, f, r, h):
        return n * f * h / (4 * math.pi * (r * r + h * h) ** 1.5)

    def test_three_published_geometry_pairs(self):
        # The three (R, h) pairs the issue quotes, against the closed form.
        for r, h in ((50.0, 5.0), (50.0, 20.0), (100.0, 10.0)):
            with self.subTest(r=r, h=h):
                got = self.density(1000, 1.0, r, h)
                self.assertAlmostEqual(got, self.closed_form(1000, 1.0, r, h), places=9)

    def test_the_obliquity_factor_is_present(self):
        # The over-prediction the pre-fix form carried: (R^2+h^2)/h^2.
        n, f = 1000.0, 1.0
        for r, h in ((50.0, 5.0), (50.0, 20.0), (100.0, 10.0)):
            with self.subTest(r=r, h=h):
                old = n / (4 * math.pi * h * math.sqrt(r * r + h * h))
                ratio = old / self.density(n, f, r, h)
                self.assertAlmostEqual(ratio, (r * r + h * h) / (h * h), places=6)

    def test_ground_burst_branch_unchanged(self):
        # h = 0 is the disk average, rho = N/(2*pi*R^2), and it is intentional.
        self.assertAlmostEqual(
            self.density(1000, 1.0, 50.0, 0.0),
            1000.0 / (2 * math.pi * 50.0 * 50.0),
            places=12,
        )

    def test_decreases_with_range(self):
        near = self.density(1000, 1.0, 20.0, 5.0)
        far = self.density(1000, 1.0, 200.0, 5.0)
        self.assertLess(far, near)


class TestContactRange(unittest.TestCase):
    def test_contact_range_is_not_harmless(self):
        # A 1 kg charge 0.1 m away (Z = 0.1) is inside the fit floor; the
        # pressure must not fall to zero there.
        self.assertGreaterEqual(kb_incident_pressure(0.1), kb_incident_pressure(0.2))
        src = (
            Path(__file__).resolve().parents[2]
            / "addons"
            / "blast"
            / "functions"
            / "blast"
            / "fnc_calculateBlastOverpressure.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("max 0.2", src)


if __name__ == "__main__":
    unittest.main()
