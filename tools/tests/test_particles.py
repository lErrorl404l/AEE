#!/usr/bin/env python3
"""Particle material + state coupling tests (issue #150).

The engine's particle solver uses weight (gravity), volume (drag), rubbing
(wind coupling), and bounceOnSurface (ground restitution).  These tests
lock the material table and the environmental coupling: air density scales
drag, ground state sets dust restitution, wind couples advection.

Run: python3 -m unittest tools.tests.test_particles
"""

import unittest

# ─── Mirror of fnc_particleMaterial.sqf ──────────────────────────────────
MATERIALS = {
    "smoke": {"weight": 1.0, "volume": 1.0, "rubbing": 0.05, "bounce": -1},
    "dust": {"weight": 1.0, "volume": 0.6, "rubbing": 0.5, "bounce": 0.4},
    "spray": {"weight": 0.5, "volume": 2.0, "rubbing": 0.7, "bounce": 0.8},
    "debris": {"weight": 3.0, "volume": 0.2, "rubbing": 0.2, "bounce": 0.6},
    "plume": {"weight": -0.5, "volume": 0.5, "rubbing": 0.1, "bounce": -1},
}


def particle_material(material):
    return MATERIALS.get(material, MATERIALS["smoke"])


# ─── Mirror of fnc_particleState.sqf coupling ────────────────────────────
def coupled_params(material, rho=1.225, ground_state="Normal", wind_str=0.0):
    """Mirror of the state coupling: density drag, ground restitution,
    wind advection."""
    base = particle_material(material)
    weight, volume, rubbing, bounce = (
        base["weight"],
        base["volume"],
        base["rubbing"],
        base["bounce"],
    )

    # Density -> drag: volume scales inversely with the density ratio.
    rho = max(0.1, min(1.5, rho))
    volume = volume * (1.225 / rho)

    # Ground state -> dust restitution.
    if material == "dust":
        bounce = {
            "Frozen": 0.45,
            "Hardpack": 0.4,
            "Normal": 0.25,
            "Mud": 0.1,
            "Snow": 0.05,
        }.get(ground_state, 0.25)

    # Wind -> dust advection.
    if material == "dust":
        rubbing = min(0.3 + (min(wind_str, 15) / 15) * 0.4, 0.7)

    return weight, volume, rubbing, bounce


class TestParticleMaterial(unittest.TestCase):
    """The material table itself."""

    def test_material_present(self):
        for m in ["smoke", "dust", "spray", "debris", "plume"]:
            self.assertIn(m, MATERIALS)

    def test_plume_is_buoyant(self):
        # Negative weight = rises (hot gas), the fire-plume physics.
        self.assertLess(particle_material("plume")["weight"], 0)

    def test_smoke_no_bounce(self):
        self.assertEqual(particle_material("smoke")["bounce"], -1)

    def test_debris_heavy_low_drag(self):
        d = particle_material("debris")
        self.assertGreater(d["weight"], 2.0)
        self.assertLess(d["volume"], 0.3)

    def test_unknown_falls_back_to_smoke(self):
        self.assertEqual(particle_material("nope"), MATERIALS["smoke"])


class TestDensityCoupling(unittest.TestCase):
    """Air density scales drag: thin air drags less."""

    def test_volume_scales_inverse_density(self):
        # rho 0.6 -> volume x (1.225/0.6) = x2.04
        _, vol_thin, _, _ = coupled_params("smoke", rho=0.6)
        _, vol_sea, _, _ = coupled_params("smoke", rho=1.225)
        self.assertAlmostEqual(vol_thin / vol_sea, 1.225 / 0.6, places=4)

    def test_dust_travels_farther_in_thin_air(self):
        # Spec vector: rho 0.6 -> ~1.7x farther (sqrt of the drag ratio).
        _, vol_thin, _, _ = coupled_params("dust", rho=0.6)
        _, vol_sea, _, _ = coupled_params("dust", rho=1.225)
        self.assertAlmostEqual(vol_thin / vol_sea, 1.225 / 0.6, places=4)

    def test_density_clamped(self):
        # Thin air (low rho) -> high volume (less drag); dense air (high
        # rho) -> low volume.  Clamped to rho 0.1..1.5.
        _, vol_thin, _, _ = coupled_params("dust", rho=0.01)
        _, vol_dense, _, _ = coupled_params("dust", rho=10.0)
        self.assertGreater(vol_thin, vol_dense)
        # At the clamp extremes: 0.1 -> x12.25, 1.5 -> x0.82.
        self.assertAlmostEqual(vol_thin, 0.6 * (1.225 / 0.1), places=4)
        self.assertAlmostEqual(vol_dense, 0.6 * (1.225 / 1.5), places=4)


class TestGroundStateCoupling(unittest.TestCase):
    """Ground state sets dust restitution."""

    def test_bounce_by_ground(self):
        self.assertEqual(coupled_params("dust", ground_state="Hardpack")[3], 0.4)
        self.assertEqual(coupled_params("dust", ground_state="Mud")[3], 0.1)
        self.assertEqual(coupled_params("dust", ground_state="Snow")[3], 0.05)

    def test_only_dust_couples_ground(self):
        # Smoke has no ground coupling (bounce stays -1).
        self.assertEqual(coupled_params("smoke", ground_state="Mud")[3], -1)


class TestWindCoupling(unittest.TestCase):
    """Wind couples dust advection."""

    def test_dust_rubbing_rises_with_wind(self):
        calm = coupled_params("dust", wind_str=0.0)[2]
        windy = coupled_params("dust", wind_str=15.0)[2]
        self.assertGreater(windy, calm)

    def test_wind_capped(self):
        cap = coupled_params("dust", wind_str=50.0)[2]
        self.assertLessEqual(cap, 0.7)


if __name__ == "__main__":
    unittest.main()
