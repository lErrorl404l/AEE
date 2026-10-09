#!/usr/bin/env python3
"""Particle material + state coupling tests (issue #150).

The engine's particle solver uses weight (gravity), volume (drag), rubbing
(wind coupling), and bounceOnSurface (ground restitution).  These tests
lock the material table and the environmental coupling: air density scales
drag, ground state sets dust restitution, wind couples advection.

Run: python3 -m unittest tools.tests.test_particles
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# A class body with no parent shadows the vanilla class at run time.  The
# `class Default {};` form is the Empty syntax; `class X {` is a bare block.
BARE_INLINE_RE = re.compile(r"^[ \t]+class (\w+) \{\s*\}\s*;", re.M)
BARE_BLOCK_RE = re.compile(r"^[ \t]+class (\w+) \{\s*$", re.M)
FORWARD_DEFAULT_RE = re.compile(r"^[ \t]+class Default;\s*$", re.M)

# ─── Mirror of fnc_particleMaterial.sqf ──────────────────────────────────
# Values track the ONE material table (issue #149 unification).  The
# surface materials carry the values the live kickup functions used, so the
# pipeline migration does not change their behaviour.
MATERIALS = {
    "dust": {"weight": 1.00, "volume": 0.60, "rubbing": 0.50, "bounce": 0.25},
    "sand": {"weight": 1.45, "volume": 0.45, "rubbing": 0.42, "bounce": 0.20},
    "dirt": {"weight": 1.10, "volume": 0.70, "rubbing": 0.55, "bounce": 0.15},
    "snow": {"weight": 0.55, "volume": 1.10, "rubbing": 0.75, "bounce": 0.05},
    "mud": {"weight": 1.60, "volume": 0.30, "rubbing": 0.20, "bounce": 0.05},
    "gravel": {"weight": 1.80, "volume": 0.25, "rubbing": 0.15, "bounce": 0.35},
    "spray": {"weight": 0.80, "volume": 1.40, "rubbing": 0.35, "bounce": 0.60},
    "smoke": {"weight": 1.0, "volume": 1.0, "rubbing": 0.05, "bounce": -1},
    "debris": {"weight": 3.0, "volume": 0.2, "rubbing": 0.2, "bounce": 0.6},
    "plume": {"weight": -0.5, "volume": 0.5, "rubbing": 0.1, "bounce": -1},
    "hail": {"weight": 2.2, "volume": 0.15, "rubbing": 0.10, "bounce": 0.60},
    "rain": {"weight": 0.9, "volume": 1.30, "rubbing": 0.80, "bounce": -1},
}

# Materials whose base bounce >= 0 collide with the ground, so the ground
# state overrides their restitution.
GROUND_COLLIDERS = {"dust", "sand", "dirt", "snow", "mud", "gravel"}


def particle_material(material):
    return MATERIALS.get(material, MATERIALS["dust"])


# ─── Mirror of fnc_particleState.sqf coupling ────────────────────────────
def coupled_params(
    material, rho=1.225, ground_state="Normal", wind_str=0.0, wave_height=0.0
):
    """Mirror of the state coupling: density drag, ground restitution,
    wind advection, water-surface tracking."""
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

    # Ground state -> restitution for the colliding materials.
    if material in GROUND_COLLIDERS:
        bounce = {
            "Frozen": 0.45,
            "Hardpack": 0.4,
            "Normal": 0.25,
            "Mud": 0.1,
            "Snow": 0.05,
        }.get(ground_state, 0.25)

    # Wind -> advection: the production formula from fnc_kickupParams.
    rubbing = min(rubbing * (1 + (min(wind_str, 15) / 15) * 0.6), 0.9)

    # Water surface -> keepOnSurface + surfaceOffset (wave height).
    keep = material == "spray"
    offset = max(0.0, wave_height) if keep else 0.0

    return weight, volume, rubbing, bounce, keep, offset


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

    def test_unknown_falls_back_to_dust(self):
        # The unified table falls back to dust, the production default
        # (fnc_kickupParams used dust as its default too).
        self.assertEqual(particle_material("nope"), MATERIALS["dust"])


class TestDensityCoupling(unittest.TestCase):
    """Air density scales drag: thin air drags less."""

    def test_volume_scales_inverse_density(self):
        # rho 0.6 -> volume x (1.225/0.6) = x2.04
        vol_thin = coupled_params("smoke", rho=0.6)[1]
        vol_sea = coupled_params("smoke", rho=1.225)[1]
        self.assertAlmostEqual(vol_thin / vol_sea, 1.225 / 0.6, places=4)

    def test_dust_travels_farther_in_thin_air(self):
        # Spec vector: rho 0.6 -> ~1.7x farther (sqrt of the drag ratio).
        vol_thin = coupled_params("dust", rho=0.6)[1]
        vol_sea = coupled_params("dust", rho=1.225)[1]
        self.assertAlmostEqual(vol_thin / vol_sea, 1.225 / 0.6, places=4)

    def test_density_clamped(self):
        # Thin air (low rho) -> high volume (less drag); dense air (high
        # rho) -> low volume.  Clamped to rho 0.1..1.5.
        vol_thin = coupled_params("dust", rho=0.01)[1]
        vol_dense = coupled_params("dust", rho=10.0)[1]
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
        # The production coupling caps rubbing at 0.9 (fnc_kickupParams).
        cap = coupled_params("dust", wind_str=50.0)[2]
        self.assertLessEqual(cap, 0.9)


class TestWaterSurfaceCoupling(unittest.TestCase):
    """Spray tracks the water surface (issue #150)."""

    def test_spray_keeps_on_surface_with_wave_offset(self):
        keep, offset = coupled_params("spray", wave_height=2.5)[4:]
        self.assertTrue(keep)
        self.assertEqual(offset, 2.5)

    def test_dust_does_not_keep_on_surface(self):
        keep, offset = coupled_params("dust", wave_height=2.5)[4:]
        self.assertFalse(keep)
        self.assertEqual(offset, 0.0)


class TestCloudletOverrideShape(unittest.TestCase):
    """AEE's CfgCloudlets blocks must forward-declare Default, not reopen it.

    Regression: `class Default {};` inside CfgCloudlets reopens the vanilla
    CfgCloudlets/Default bare.  The engine treats a reopen with no parent as
    the Empty syntax and SHADOWS the class, and every base-game smoke cloudlet
    inherits Default, so the smoke stops drawing.  The parent is
    forward-declared once and the children restate it, so the engine merges.
    """

    CONFIGS = (REPO / "addons" / "fx" / "config.cpp",)

    @staticmethod
    def _cloudlets_block(text):
        start = text.index("class CfgCloudlets")
        depth = 0
        for i in range(text.index("{", start), len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        raise AssertionError("unbalanced CfgCloudlets block")

    def test_default_is_forward_declared_not_reopened(self):
        for path in self.CONFIGS:
            block = self._cloudlets_block(path.read_text(encoding="utf-8"))
            with self.subTest(config=path.name):
                self.assertEqual(BARE_INLINE_RE.findall(block), [])
                self.assertEqual(BARE_BLOCK_RE.findall(block), [])
                self.assertRegex(block, FORWARD_DEFAULT_RE)


if __name__ == "__main__":
    unittest.main()
