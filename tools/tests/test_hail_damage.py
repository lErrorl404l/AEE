"""Hailstone impact physics from the drag balance (#151 follow-on).

The channel is grounded in two published laws, so the test evaluates them
independently and compares the SQF against them.  It does NOT mirror the
SQF expression: the constants are read out of the SQF text and the physics
is computed here from the primary sources.  A mirror that encoded the same
bug would pass while the SQF stayed wrong.

Sources:
  v_t = sqrt(4 g rho_h D / (3 C_d rho_a))
    Dieling, Smith & Beruvides 2020, Geosciences 10(12):500, Eq. 2.
  m   = (pi/6) rho_h D^3
  E   = 0.5 m v_t^2
"""

import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENERGY = (
    ROOT / "addons" / "atmos" / "functions" / "physics" / "fnc_calculateHailEnergy.sqf"
)
DAMAGE = ROOT / "addons" / "atmos" / "functions" / "physics" / "fnc_hailDamage.sqf"

RHO_H = 917.0  # kg/m3, pure ice
C_D = 0.6  # near-spherical hail > 1 cm, Dieling 2020
RHO_A = 1.225  # kg/m3, sea level
G = 9.80665

NWS_SEVERE_M = 0.0254  # 1 inch, the NWS severe criterion
NWS_GRAPEFRUIT_M = 0.1016  # 4 inch, the largest modelled stone


def terminal_velocity(d_m):
    return math.sqrt((4 * G * RHO_H * d_m) / (3 * C_D * RHO_A))


def mass(d_m):
    return (math.pi / 6) * RHO_H * d_m**3


def energy(d_m):
    return 0.5 * mass(d_m) * terminal_velocity(d_m) ** 2


class TestHailPhysicsAgainstSource(unittest.TestCase):
    """The published laws, evaluated independently."""

    def test_five_cm_stone(self):
        # ~28.6 m/s and ~24 J from the laws above.
        self.assertAlmostEqual(terminal_velocity(0.05), 28.6, delta=0.5)
        self.assertAlmostEqual(energy(0.05), 24.0, delta=2.0)

    def test_ten_cm_stone(self):
        # ~40.4 m/s and ~392 J.
        self.assertAlmostEqual(terminal_velocity(0.10), 40.4, delta=1.0)
        self.assertAlmostEqual(energy(0.10), 392.0, delta=20.0)

    def test_velocity_scales_with_sqrt_diameter(self):
        # The drag balance gives v_t proportional to sqrt(D).
        ratio = terminal_velocity(0.10) / terminal_velocity(0.025)
        self.assertAlmostEqual(ratio, math.sqrt(4.0), delta=0.05)


class TestSqfConstantsMatchSources(unittest.TestCase):
    """Read the constants OUT of the SQF text; do not trust the comment."""

    def setUp(self):
        self.src = ENERGY.read_text(encoding="utf-8")

    def _number(self, name):
        m = re.search(rf"private _{name} = ([0-9.]+);", self.src)
        self.assertIsNotNone(m, f"constant _{name} is missing from the SQF")
        return float(m.group(1))

    def test_density_matches_ice(self):
        self.assertAlmostEqual(self._number("rhoH"), RHO_H, delta=1.0)

    def test_drag_coefficient_matches_the_large_hail_fit(self):
        self.assertAlmostEqual(self._number("cd"), C_D, delta=0.05)

    def test_air_density_matches_sea_level(self):
        self.assertAlmostEqual(self._number("rhoA"), RHO_A, delta=0.005)

    def test_velocity_uses_the_drag_balance(self):
        # The expression must be the drag balance, not an invented constant.
        expr = re.search(
            r"private _vT = sqrt \(\(4 \* _g \* _rhoH \* _diameter\) / \(3 \* _cd \* _rhoA\)\);",
            self.src,
        )
        self.assertIsNotNone(
            expr,
            "the terminal velocity is not the published drag balance",
        )

    def test_mass_uses_spherical_volume(self):
        self.assertIn("(pi / 6) * _rhoH * (_diameter ^ 3)", self.src)

    def test_energy_is_half_mass_v_squared(self):
        self.assertIn("0.5 * _mass * _vT * _vT", self.src)

    def test_size_band_spans_severe_to_grapefruit(self):
        self.assertAlmostEqual(self._number("severeM"), NWS_SEVERE_M, delta=0.0005)
        self.assertAlmostEqual(self._number("maxM"), NWS_GRAPEFRUIT_M, delta=0.0005)


class TestNoInventedInjuryThreshold(unittest.TestCase):
    """NWS publishes no joules-to-injury law, so the code must not invent one.

    The channel exposes the energy and maps it to the engine's OWN damage
    scale.  A hard-coded "X joules = Y injury" constant would be fabricated
    physics, which this project rejects.
    """

    def setUp(self):
        self.src = DAMAGE.read_text(encoding="utf-8")

    def test_damage_maps_energy_onto_the_engine_scale(self):
        self.assertIn("linearConversion", self.src)
        # Bounds are the computed energies of the extreme modelled stones.
        self.assertIn("[24, 392, _energy", self.src)

    def test_damage_reads_the_published_energy(self):
        # The source names it through the QEGVAR macro; the preprocessor
        # expands that to aee_core_hailEnergy at build time.
        self.assertIn("QEGVAR(core,hailEnergy)", self.src)

    def test_no_publication_of_core_state(self):
        # Determinism contract: no broadcast for core state.
        self.assertNotIn("publicVariable", self.src)

    def test_ace_medical_used_when_present(self):
        self.assertIn("ace_medical_fnc_addDamageToUnit", self.src)
        self.assertIn("setDamage", self.src)

    def test_soft_targets_in_vehicles_are_protected(self):
        # A stone must reach the unit; an occupied vehicle blocks it.
        self.assertIn("objectParent _unit", self.src)


if __name__ == "__main__":
    unittest.main()
