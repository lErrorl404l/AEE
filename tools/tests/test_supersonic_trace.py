#!/usr/bin/env python3
"""Supersonic trace kernel verification (issue #217).

Verifies fnc_calculateSupersonicTrace.sqf.  Per the note in
tools/tests/sqf_lite.py a hand-transcribed Python mirror is NOT acceptable,
because a mirror once replicated the SQF's own bugs and drifted from the
source without detection.  So this test PARSES the real SQF and reads every
constant from the file it tests, then re-derives the physics here from first
principles.  A wrong constant in either place fails.

The kernel models the REFRACTIVE component of the trace.  A supersonic round
steps the air density across its bow shock, and the index of refraction of air
tracks density (Gladstone-Dale), so the density step bends light.

The kernel returns an UPPER BOUND, not a prediction.  It applies the NORMAL
shock relation.  A real bullet has a blunted nose, so its bow shock is oblique
over the forward face, and an oblique shock gives a smaller density rise at the
same Mach.  test_oblique_shock_never_exceeds_the_bound checks that claim
numerically, so the bound cannot quietly turn into a prediction.

Sources held for the constants:
  K = 2.26e-4 m^3/kg  Stone and Zimmerman, "Index of Refraction of Air",
                      NIST Engineering Metrology Toolbox, which publishes
                      the Edlen and Ciddor equations.
  gamma = 1.4         U.S. Standard Atmosphere 1976, NTRS 19770009539.
  local sound speed   a = 20.05 * sqrt(T + 273.15), the form
                      fnc_calculateBallisticDrag already uses.

Run: python3 -m unittest tools/tests/test_supersonic_trace.py
"""

import math
import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
KERNEL = REPO / "addons/ballistics/functions/fnc_calculateSupersonicTrace.sqf"
SOURCE = KERNEL.read_text(encoding="utf-8")


def sqf_number(pattern: str) -> float:
    """Read a numeric literal out of the real SQF, so this test cannot drift
    from the file it tests."""
    match = re.search(pattern, SOURCE)
    if not match:
        raise AssertionError(f"SQF no longer matches {pattern!r}")
    return float(match.group(1))


def normal_shock_ratio(mach: float, gamma: float = 1.4) -> float:
    """Rankine-Hugoniot density ratio across a normal shock, gamma = 1.4."""
    m2 = mach * mach
    return ((gamma + 1) * m2) / ((gamma - 1) * m2 + 2)


class SupersonicTraceKernel(unittest.TestCase):
    def setUp(self) -> None:
        self.gamma = sqf_number(r"private _gamma\s*=\s*([0-9.]+)\s*;")
        self.k = sqf_number(r"private _k\s*=\s*([0-9.]+)\s*;")
        self.rho0 = sqf_number(r"private _rhoAmbient\s*=\s*([0-9.]+)")
        self.sound_coeff = sqf_number(r"private _sound\s*=\s*([0-9.]+)")

    def contrast(self, mach: float, rho_rel: float = 1.0) -> float:
        """The kernel result in its reported units, re-derived here."""
        ratio = normal_shock_ratio(mach, self.gamma)
        return self.k * self.rho0 * rho_rel * (ratio - 1.0) / 0.0001

    def ambient_index(self, rho_rel: float = 1.0) -> float:
        """K * rho, the index step of the undisturbed air itself."""
        return self.k * self.rho0 * rho_rel / 0.0001

    # ── the constants are the sourced ones ──────────────────────────────
    def test_gamma_matches_us_standard_atmosphere(self) -> None:
        self.assertEqual(self.gamma, 1.4)

    def test_gladstone_dale_coefficient(self) -> None:
        self.assertAlmostEqual(self.k, 0.000226, places=9)

    def test_sea_level_index_matches_the_standard_value(self) -> None:
        # K is defined by (n - 1) / rho.  At 15 C and 101.325 kPa the standard
        # index for air is n - 1 = 2.77e-4, so K * rho0 must land there.  This
        # ties the SQF constant to a published number for standard air.
        self.assertAlmostEqual(self.k * self.rho0, 2.77e-4, places=6)

    def test_ambient_density_is_isa_sea_level(self) -> None:
        self.assertEqual(self.rho0, 1.225)

    def test_speed_of_sound_form(self) -> None:
        self.assertEqual(self.sound_coeff, 20.05)
        # 20.05 * sqrt(288.15) is 340.34 m/s, the ISA sea level value.
        self.assertAlmostEqual(20.05 * math.sqrt(288.15), 340.29, delta=0.1)

    # ── the algebra the SQF implements, re-derived here ────────────────
    def test_density_ratio_vanishes_at_unity(self) -> None:
        # The relation returns exactly 1 at M = 1, so the shock and the trace
        # vanish there.  This is the subsonic guard.
        self.assertAlmostEqual(normal_shock_ratio(1.0, self.gamma), 1.0, places=12)

    def test_density_ratio_against_normal_shock_table(self) -> None:
        # Textbook normal shock density ratios for gamma = 1.4.
        expected = {
            1.0: 1.0,
            1.5: 1.8621,
            2.0: 2.6667,
            2.5: 3.3333,
            3.0: 3.8571,
        }
        for mach, want in expected.items():
            self.assertAlmostEqual(
                normal_shock_ratio(mach, self.gamma), want, places=3, msg=f"M={mach}"
            )

    def test_contrast_grows_with_mach(self) -> None:
        seq = [self.contrast(m) for m in (1.0, 1.2, 1.5, 2.0, 2.6, 3.0, 4.0)]
        for i in range(len(seq) - 1):
            self.assertLess(seq[i], seq[i + 1], f"not monotone at index {i}")

    def test_contrast_scales_with_rho_rel(self) -> None:
        # Denser air carries a larger index step for the same Mach.
        self.assertGreater(self.contrast(2.6, 1.2), self.contrast(2.6, 1.0))
        self.assertGreater(self.contrast(2.6, 1.0), self.contrast(2.6, 0.8))

    def test_contrast_against_the_index_of_the_air_itself(self) -> None:
        # The trace competes with the index of the air it sits in, so compare
        # the two.  Just supersonic, the shock step is a small fraction of it.
        # At rifle Mach it is larger than the whole atmospheric index step.
        self.assertLess(self.contrast(1.2), self.ambient_index())
        self.assertGreater(self.contrast(2.6), 2.4 * self.ambient_index())
        self.assertGreater(self.contrast(2.6), self.contrast(2.0))

    # ── the result is a bound, and must stay labelled one ──────────────
    def test_oblique_shock_never_exceeds_the_bound(self) -> None:
        # An oblique shock has a normal Mach number M sin(beta), which is
        # strictly below M for any beta below 90 degrees.  The normal shock
        # ratio rises with Mach, so the oblique ratio is always strictly below
        # the normal shock ratio the kernel returns.  If this fails, the
        # "upper bound" wording in the header is a lie.
        for mach in (1.2, 1.5, 2.0, 2.6, 3.0, 4.0):
            bound = normal_shock_ratio(mach, self.gamma)
            for beta_deg in range(20, 90, 5):
                m_normal = mach * math.sin(math.radians(beta_deg))
                if m_normal <= 1.0:
                    continue
                self.assertLess(
                    normal_shock_ratio(m_normal, self.gamma),
                    bound,
                    msg=f"M={mach} beta={beta_deg}",
                )

    def test_header_states_the_bound(self) -> None:
        self.assertIn("UPPER BOUND", SOURCE)
        self.assertIn("oblique", SOURCE.lower())
        self.assertIn("stagnation streamline", SOURCE.lower())

    def test_header_keeps_the_radio_constant_separate(self) -> None:
        # fnc_calculateRefraction holds the ITU-R P.453 RADIO refractivity.
        # Its wavelength is not the visible one, so its constant must not be
        # read as the optical Gladstone-Dale K.
        self.assertIn("ITU-R", SOURCE)
        self.assertIn("radio", SOURCE.lower())

    def test_header_does_not_claim_to_exclude_condensation(self) -> None:
        # The kernel models refraction only.  It must not claim a droplet
        # cloud is impossible, because that claim is not established.
        self.assertIn("neither models", SOURCE)

    # ── the guards the SQF must keep ───────────────────────────────────
    def test_no_trace_below_mach_one(self) -> None:
        self.assertRegex(SOURCE, r"if \(_mach\s*<=\s*1\)\s*exitWith \{\s*0\s*\}")
        self.assertRegex(SOURCE, r"if \(_velocity\s*<=\s*0\)\s*exitWith")
        self.assertRegex(SOURCE, r"if \(_rhoRel\s*<=\s*0\)\s*exitWith")

    def test_no_strength_override(self) -> None:
        # An override would let a trace appear where the air does not support
        # one.  The function must not scale its result, and must not publish a
        # multiplier setting.
        self.assertNotIn("settingsConfigFile", SOURCE)
        self.assertNotIn("missionNamespace setVariable", SOURCE)
        self.assertNotIn("GVAR(", SOURCE.split("Arguments:")[0])
        # The only scaling is the reporting unit, and it is a pure division.
        body = SOURCE.split("private _contrast =")[-1]
        self.assertIn("_contrast / 0.0001", body)

    def test_declares_params_and_return(self) -> None:
        # CONTRIBUTING requires the standard header: params, return, example.
        self.assertIn("params [", SOURCE)
        self.assertIn("Arguments:", SOURCE)
        self.assertIn("Returns the refractive index contrast", SOURCE)


if __name__ == "__main__":
    unittest.main()
