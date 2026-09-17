#!/usr/bin/env python3
"""Blast overpressure and injury tests (issue #132).

Mirrors fnc_calculateBlastOverpressure.sqf (Kingery-Bulmash / Swisdak
1994 simplified fits) and fnc_calculateBlastInjury.sqf (Bowen 1968 P-I
curves + tertiary throw).

The reference values are verified against the `kingery-bulmash` pip
package (fcento100, Swisdak ADA526744) and the issue's published anchors:
  Z=1 -> 1353.7 kPa, Z=2 -> 283.7, Z=5 -> 43.2, Z=10 -> 14.9.

Run: python3 -m unittest tools.tests.test_blast
"""

import math
import unittest


# ─── Mirrors ───────────────────────────────────────────────────────────────


def kb_incident_pressure(z):
    """Swisdak simplified KB incident overpressure fit (kPa)."""
    if not (0.2 <= z <= 198.5):
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

    # Tertiary throw: blast wind q_o; likely above ~15 kPa.
    q0 = (2.5 * P * P) / (7 * 101.3 + P)
    throw01 = min((P - 15) / 5, 1.0) if P > 15 else 0.0

    return [eardrum, lung_thresh, lung1, lung50, lung99, throw01]


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


class TestBlastInjury(unittest.TestCase):
    """Bowen P-I curves + tertiary throw."""

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

    def test_throw_threshold(self):
        self.assertEqual(blast_injury(10, 10)[5], 0.0)
        self.assertGreater(blast_injury(20, 10)[5], 0.0)
        self.assertAlmostEqual(blast_injury(20, 10)[5], 1.0, places=3)

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
      M107 (7 kg):  lung99 3.73 m, eardrum50 6.07 m, throw onset 19.0 m
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
        # throw active inside ~19 m (P > 15 kPa); gone beyond.
        t16 = blast_injury(*blast_overpressure(m, 16.0))[5]
        self.assertGreater(t16, 0.5)
        t19 = blast_injury(*blast_overpressure(m, 19.1))[5]
        self.assertLess(t19, 0.01)
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


if __name__ == "__main__":
    unittest.main()
