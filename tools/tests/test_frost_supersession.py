"""The supersessions issue #11 depends on.

Issue #11 asked for three things. One is implemented directly (the
soil-type-dependent Stefan coefficient, see test_stefan_coefficient.py).
One is satisfied by a later change that replaced the model it named
(force-restore, superseded by the 4-node Crank-Nicolson stack).

The third category is the one that matters here: a supersession is only
real when every consumer of the old approximation has been moved. Issue
#11 named two specific approximations:

  1. the surface temperature approximated as T_air - 2 C on a clear calm
     night, to be replaced by the solved surface node;
  2. the frost depth as 0.05 * sqrt(FDD), to be replaced by the
     soil-dependent Stefan coefficient.

Both were still in the tree after the replacement landed. These tests
guard the routes, so a later edit cannot quietly restore the shortcut.
They read the source, because the property is "this file uses the solved
value", which no runtime test can see on a headless server.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"


def read(rel):
    return (ADDONS / rel).read_text(encoding="utf-8")


class TestSurfaceTemperatureRoute(unittest.TestCase):
    """fnc_detectGroundFrost must read the node stack, not T_air - 2."""

    def setUp(self):
        self.src = read("environmental/functions/terrain/fnc_detectGroundFrost.sqf")

    def test_reads_the_published_surface_temperature(self):
        self.assertIn("groundSurfaceTemp", self.src)

    def test_the_heuristic_is_only_a_fallback(self):
        """The -2 must sit in an else branch, not stand alone."""
        # Find the fallback and check it is guarded by a lookup that
        # already succeeded or failed.
        self.assertRegex(self.src, r"else\s*\{[^}]*_temp\s*-\s*2", re.S)

    def test_the_node_stack_publishes_it(self):
        src = read("thermal/functions/ground/fnc_calculateGroundTemperature.sqf")
        self.assertIn("groundSurfaceTemp", src)
        self.assertIn("_ts", src)


class TestStefanRoute(unittest.TestCase):
    """Freeze-thaw depth must use the soil coefficient, not a constant."""

    def setUp(self):
        self.src = read(
            "environmental/functions/terrain/fnc_calculateFreezeThawCycling.sqf"
        )

    def test_uses_the_coefficient_function(self):
        self.assertIn("calculateStefanCoefficient", self.src)

    def test_the_hardcoded_constant_is_gone(self):
        """0.05 was the metres form of a generic soil. It must not return:
        it hides the water-content dependence the coefficient exists for."""
        body = re.sub(r"//[^\n]*", "", self.src)
        self.assertNotRegex(body, r"0\.05\s*\*\s*\(\s*sqrt")

    def test_converts_cm_to_metres(self):
        """The coefficient is cm per sqrt(degC-day); the depth is metres."""
        self.assertIn("/ 100", self.src)


class TestForceRestoreSupersession(unittest.TestCase):
    """The node stack must still be the full solve, not a reduced model.

    Issue #11 named force-restore. A later change replaced the single-node
    solver it was meant to improve with a 4-node Crank-Nicolson stack,
    which solves the same heat equation at higher order. If someone ever
    swaps the stack for force-restore, this test fails, because the
    documented supersession would have been reversed.
    """

    def setUp(self):
        self.src = read("thermal/functions/ground/fnc_calculateGroundNodeStack.sqf")

    def test_solves_the_heat_equation(self):
        self.assertIn("Crank", self.src)
        self.assertRegex(self.src, r"d2T/dz2|d\^2T|second derivative", re.I)

    def test_has_four_nodes(self):
        self.assertRegex(self.src, r"\[0\.10,\s*0\.30,\s*0\.60,\s*1\.00\]")

    def test_force_restore_is_not_the_model(self):
        body = re.sub(r"//[^\n]*", "", self.src)
        self.assertNotIn("force_restore", body)
        self.assertNotIn("forceRestore", body)

    def test_the_header_states_the_anchor_limitation(self):
        """The bottom node is a fixed Dirichlet term inside the annual
        damping depth for wet soil. That is a known limit and it is
        recorded, not hidden."""
        self.assertRegex(self.src, r"bottom|anchor|_tBot", re.I)


if __name__ == "__main__":
    unittest.main()


class TestSnowInsulation(unittest.TestCase):
    """The node stack must carry a snow term, and it must be a series
    resistance rather than a blend into the soil node."""

    def setUp(self):
        self.src = read("thermal/functions/ground/fnc_calculateGroundNodeStack.sqf")

    def test_has_sturm_conductivity(self):
        self.assertIn("0.234", self.src)
        self.assertIn("3.233", self.src)

    def test_snow_sits_in_series(self):
        """1/h_eff = 1/h + depth/k. A blend into the node would not."""
        self.assertRegex(self.src, r"1 / \(\(1 / _h\) \+ _rSnow\)")

    def test_reuses_the_existing_density_setting(self):
        """One snowpack has one density. A second setting could disagree."""
        self.assertIn("slabDensity", self.src)
        self.assertNotIn("snowDensity_gcm3", self.src)

    def test_suppresses_soil_solar_under_snow(self):
        """The snow surface absorbs the sun, not the ground beneath."""
        self.assertRegex(self.src, r"_snowCovered\) then \{ 0 \}")

    def test_the_melt_sink_is_now_coupled(self):
        """This test once asserted the melt was NOT coupled, which was the
        documented limitation. The coupling landed (see TestMeltCoupling),
        so the assertion is reversed: the stack must carry the sink, and
        it must not carry the old limitation note."""
        self.assertIn("_meltSink", self.src)
        self.assertNotRegex(self.src, r"melt heat is not\s+yet\s+coupled", re.I)


class TestMeltCoupling(unittest.TestCase):
    """Melting must consume latent heat from the surface balance.

    Without it the soil surface reads warm through a thaw, which was a
    documented limitation of the snow work. The snow owner computes the
    melt, so the snow owner publishes the flux and the node stack reads
    it: one writer per variable.
    """

    def setUp(self):
        self.snow = read(
            "environmental/functions/terrain/fnc_calculateSnowAccumulation.sqf"
        )
        self.stack = read("thermal/functions/ground/fnc_calculateGroundNodeStack.sqf")

    def test_the_snow_owner_publishes_the_flux(self):
        self.assertIn("snowMeltFlux_Wm2", self.snow)

    def test_the_flux_uses_the_latent_heat_of_fusion(self):
        self.assertIn("334e3", self.snow)

    def test_the_stack_subtracts_it(self):
        self.assertRegex(self.stack, r"-\s*_meltSink")

    def test_the_stack_does_not_compute_the_melt_itself(self):
        """Two writers of one quantity is the defect class the project
        already removed twice. The stack must only READ the flux."""
        body = re.sub(r"//[^\n]*", "", self.stack)
        self.assertNotIn("meltDepth", body)

    def test_the_limitation_note_is_gone(self):
        """The header used to say the melt was not coupled. It is now."""
        self.assertNotRegex(self.stack, r"melt heat is not\s+yet\s+coupled")
