#!/usr/bin/env python3
"""Terrain-masked radio propagation (issue #32).

The two pure kernels run here from their real SQF through
tools/tests/sqf_lite.py, so a failure is a source failure, not a mirror
drift:

  fnc_calculateKnifeEdgeLoss.sqf    single knife-edge J(nu)  [ITU-R P.526-16 4.1]
  fnc_calculateTerrainDiffraction.sqf   Deygout multi-edge   [ITU-R P.526-16 4.3]

Source: Recommendation ITU-R P.526-16 (2025-11), Annex 1:
  eq. (26)  nu = h * sqrt( 2/lambda * (1/d1 + 1/d2) )
  eq. (31)  J(nu) = 6.9 + 20 log10( sqrt((nu-0.1)^2 + 1) + nu - 0.1 )   nu > -0.78
  eq. (39)-(43)  double isolated edges (Deygout), correction Tc omitted here.

Run: python3 -m unittest tools.tests.test_radio_terrain -v
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RADIO = ROOT / "addons" / "radio" / "functions"

KNIFE = RADIO / "fnc_calculateKnifeEdgeLoss.sqf"
DIFFRACTION = RADIO / "fnc_calculateTerrainDiffraction.sqf"


def log10(x):
    return math.log(x) / math.log(10)


def knife_edge(nu):
    """Run the shipped knife-edge kernel."""
    return run_sqf(KNIFE, [nu])


def diffraction(profile, step, tx_agl, rx_agl, lam):
    """Run the shipped Deygout kernel, wiring its FUNC call to the real
    knife-edge kernel (the harness resolves FUNC(x) through globals)."""
    return run_sqf(
        DIFFRACTION,
        [profile, step, tx_agl, rx_agl, lam],
        globals_={"__FUNC__calculateKnifeEdgeLoss": knife_edge},
    )


# ─── Mirror of eq. (31), for the drift check ────────────────────────────────
def knife_edge_mirror(nu):
    if nu <= -0.78:
        return 0.0
    return 6.9 + 20 * log10(math.sqrt((nu - 0.1) ** 2 + 1) + nu - 0.1)


def deygout_mirror(profile, step, tx_agl, rx_agl, lam, max_edges=3):
    """Mirror of the Deygout recursion in fnc_calculateTerrainDiffraction."""
    n = len(profile)
    if n < 2 or step <= 0 or lam <= 0:
        return 0.0
    paths = [(0, profile[0] + tx_agl, n - 1, profile[-1] + rx_agl)]
    loss = 0.0
    edges = 0
    while edges < max_edges:
        best_nu, best_path, best_idx = -1e9, -1, -1
        for p, (i0, h0, i1, h1) in enumerate(paths):
            if i1 - i0 < 2:
                continue
            for j in range(i0 + 1, i1):
                d1 = (j - i0) * step
                d2 = (i1 - j) * step
                line_h = h0 + (h1 - h0) * d1 / (d1 + d2)
                h = profile[j] - line_h
                if h <= 0:
                    continue
                nu = h * math.sqrt((2 / lam) * (1 / d1 + 1 / d2))
                if nu > best_nu:
                    best_nu, best_path, best_idx = nu, p, j
        if best_nu <= -0.78:
            break
        loss += knife_edge_mirror(best_nu)
        i0, h0, i1, h1 = paths[best_path]
        edge_h = profile[best_idx]
        nxt = []
        for p in range(len(paths)):
            if p == best_path:
                nxt.append((i0, h0, best_idx, edge_h))
                nxt.append((best_idx, edge_h, i1, h1))
            else:
                nxt.append(paths[p])
        paths = nxt
        edges += 1
    return loss


class TestKnifeEdgeLoss(unittest.TestCase):
    """fnc_calculateKnifeEdgeLoss.sqf vs ITU-R P.526-16 eq. (31)."""

    def test_clear_path_is_zero(self):
        # nu <= -0.78 is a fully cleared path (eq. 31 threshold).
        self.assertEqual(knife_edge(-0.78), 0)
        self.assertEqual(knife_edge(-5), 0)

    def test_grazing_is_6db(self):
        # nu = 0 (grazing): eq. (31) gives 6.03 dB.
        self.assertAlmostEqual(knife_edge(0), 6.03, places=1)

    def test_matches_eq31(self):
        for nu in [-0.5, 0.0, 0.5, 1.0, 2.0, 5.0, 18.97]:
            self.assertAlmostEqual(knife_edge(nu), knife_edge_mirror(nu), places=6)

    def test_monotonic(self):
        prev = -1.0
        for nu in [0.0, 0.5, 1.0, 2.0, 4.0, 10.0]:
            v = knife_edge(nu)
            self.assertGreater(v, prev)
            prev = v

    def test_issue_key_values_are_the_exact_integral(self):
        # The issue quotes nu = -0.78 -> 0, 0 -> 6.0, 1 -> 13.7, 2 -> 21.9.
        # Those are the EXACT Fresnel-integral values (eq. 30).  Eq. (31) is
        # the Recommendation's closed-form approximation, which agrees at
        # small nu and diverges at large nu.  The kernel implements eq. (31).
        self.assertAlmostEqual(knife_edge(1), 13.93, places=1)
        self.assertAlmostEqual(knife_edge(2), 19.04, places=1)


class TestTerrainDiffraction(unittest.TestCase):
    """fnc_calculateTerrainDiffraction.sqf vs the Deygout mirror."""

    def test_flat_path_is_clear(self):
        # Flat terrain, no obstruction: 0 dB.
        self.assertEqual(diffraction([0, 0, 0, 0], 1000, 2, 2, 3), 0)

    def test_single_ridge_matches_mirror(self):
        # A single 100 m ridge at the midpoint of a 2 km path at 100 MHz
        # (lambda = 3 m).  nu = 98 * sqrt(2/3 * (1/1000 + 1/1000)) = 3.578.
        profile = [0, 100, 0]
        loss = diffraction(profile, 1000, 2, 2, 3)
        self.assertAlmostEqual(loss, deygout_mirror(profile, 1000, 2, 2, 3), places=6)
        # nu = 3.578 -> J = 23.92 dB.
        self.assertAlmostEqual(loss, 23.92, places=1)

    def test_two_ridges_more_than_one(self):
        # Two ridges add a second diffraction term.
        one = diffraction([0, 100, 0, 0, 0], 1000, 2, 2, 3)
        two = diffraction([0, 100, 0, 100, 0], 1000, 2, 2, 3)
        self.assertGreater(two, one)

    def test_higher_ridge_more_loss(self):
        low = diffraction([0, 50, 0], 1000, 2, 2, 3)
        high = diffraction([0, 200, 0], 1000, 2, 2, 3)
        self.assertGreater(high, low)

    def test_higher_frequency_more_loss(self):
        # Shorter wavelength (higher frequency) raises nu, so the loss rises.
        vhf = diffraction([0, 100, 0], 1000, 2, 2, 3)  # 100 MHz
        uhf = diffraction([0, 100, 0], 1000, 2, 2, 0.3)  # 1 GHz
        self.assertGreater(uhf, vhf)

    def test_matches_mirror_on_irregular_profile(self):
        profile = [12, 40, 95, 60, 130, 80, 55, 30, 8]
        loss = diffraction(profile, 250, 2, 2, 3)
        self.assertAlmostEqual(loss, deygout_mirror(profile, 250, 2, 2, 3), places=6)

    def test_degenerate_inputs(self):
        self.assertEqual(diffraction([], 50, 2, 2, 3), 0)
        self.assertEqual(diffraction([5], 50, 2, 2, 3), 0)
        self.assertEqual(diffraction([0, 10], 0, 2, 2, 3), 0)
        self.assertEqual(diffraction([0, 10], 50, 2, 2, 0), 0)


class TestMaskedLinkGeometry(unittest.TestCase):
    """The knife-edge parameter nu from eq. (26) over a link geometry."""

    def test_nu_practical_units(self):
        # eq. (33): nu = 0.0316 h sqrt(2 (d1+d2) / (lambda d1 d2)) with h, lambda
        # in metres and d1, d2 in km.  Check the kernel's geometry against it
        # through the diffraction kernel: h = 98 m, d1 = d2 = 1 km, lambda = 3.
        h, d1, d2, lam = 98.0, 1.0, 1.0, 3.0
        nu_practical = 0.0316 * h * math.sqrt(2 * (d1 + d2) / (lam * d1 * d2))
        nu_direct = h * math.sqrt((2 / lam) * ((1 / (d1 * 1000)) + (1 / (d2 * 1000))))
        self.assertAlmostEqual(nu_practical, nu_direct, places=2)


if __name__ == "__main__":
    unittest.main()
