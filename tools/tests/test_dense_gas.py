#!/usr/bin/env python3
"""Dense-gas dispersion reference checks (issue #120).

The pure kernels in addons/weather/functions/dispersion/ are executed
through tools/tests/sqf_lite.py, so these checks run the real SQF and not
a Python mirror that can drift from it.

Sources (each constant is drift-locked to its source):
  DEGADIS User's Manual (Havens & Spicer 1985, USCG-D-24-85, DTIC
  ADA171524) - frontal velocity u_f = C_e*sqrt(g*A'*H), C_e = 1.15;
  Richardson number Ri* = g*A'*H/u^2; frontal entrainment e = 0.59;
  gravity-spreading cut-off delrhomin = 0.025.
  Kawamura & Mackay 1987, J Hazard Mater 15(3):343-364, with Mackay &
  Matsugu 1973 - evaporation flux E = k*M*P/(R*Ts), k =
  0.029*u^0.78*X^-0.11*Sc^-0.67.
  EPA AEGL (chlorine, tear gas), NIOSH IDLH, ACGIH TLV - acute endpoints.
  ISO 2533 - dry-air molar mass 28.97 g/mol and density 1.204 kg/m3.

Run: python3 -m unittest tools/tests/test_dense_gas.py
"""

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DISP = ROOT / "addons" / "weather" / "functions" / "dispersion"
PROPS = DISP / "fnc_getGasProperties.sqf"
SLUMP = DISP / "fnc_calculateDenseGasSlumping.sqf"
MIX = DISP / "fnc_calculateGasMixtureDensity.sqf"
POOL = DISP / "fnc_calculateDenseGasPooling.sqf"
EVAP = DISP / "fnc_calculatePoolEvaporation.sqf"
TOX = DISP / "fnc_classifyToxicExposure.sqf"
DRIVER = DISP / "fnc_calculateDenseGasDispersion.sqf"
PREP = ROOT / "addons" / "weather" / "XEH_PREP.hpp"
SETTINGS = ROOT / "addons" / "weather" / "initSettings.inc.sqf"
STRINGTABLE = ROOT / "addons" / "weather" / "stringtable.xml"
ENV = ROOT / "addons" / "core" / "functions" / "fnc_updateEnvironment.sqf"
RUNNER = ROOT / "tools" / "run_tests.py"

G = 9.80665
M_AIR = 28.97
RHO_A = 1.204


def _strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


class TestGasProperties(unittest.TestCase):
    def test_chlorine(self):
        p = run_sqf(PROPS, ["chlorine"])
        self.assertEqual(p[0], 70.90)
        self.assertAlmostEqual(p[1], 70.90 / M_AIR, places=3)
        self.assertEqual(p[1], 2.447)
        self.assertEqual(p[2], -34.04)  # normal boiling point, C

    def test_cs(self):
        p = run_sqf(PROPS, ["cs"])
        self.assertEqual(p[0], 188.61)
        self.assertEqual(p[1], 6.511)

    def test_density_ratio_is_the_ideal_gas_result(self):
        # rho_g / rho_a = M_gas / M_air at equal T, P.
        for agent, mw in (
            ("carbon-dioxide", 44.01),
            ("phosgene", 98.91),
            ("sarin", 140.09),
            ("hydrogen-cyanide", 27.03),
        ):
            p = run_sqf(PROPS, [agent])
            self.assertAlmostEqual(p[1], mw / M_AIR, places=3, msg=agent)

    def test_unknown_agent_is_empty(self):
        self.assertEqual(run_sqf(PROPS, ["unobtainium"]), [])

    def test_case_insensitive(self):
        self.assertEqual(run_sqf(PROPS, ["CHLORINE"]), run_sqf(PROPS, ["chlorine"]))


class TestDenseGasSlumping(unittest.TestCase):
    def test_frontal_velocity_test_vector(self):
        # Issue vector: rho = 2*rho_a, H = 1 m -> u_f = 3.60 m/s.
        out = run_sqf(SLUMP, [2, 1, 2])
        self.assertAlmostEqual(out[1], 1.15 * math.sqrt(G * 1 * 1), places=6)
        self.assertAlmostEqual(out[1], 3.60, places=2)

    def test_reduced_gravity(self):
        out = run_sqf(SLUMP, [2, 1, 0])
        self.assertAlmostEqual(out[0], G * 1.0, places=6)

    def test_richardson_number(self):
        # Ri* = g*A'*H/u^2.
        out = run_sqf(SLUMP, [2, 1, 2])
        self.assertAlmostEqual(out[2], G * 1.0 * 1 / 4.0, places=6)

    def test_entrainment_is_point_five_nine_times_the_front(self):
        out = run_sqf(SLUMP, [2, 1, 2])
        self.assertAlmostEqual(out[3], 0.59 * out[1], places=9)

    def test_buoyant_gas_does_not_slump(self):
        # HCN is lighter than air (ratio 0.93): no frontal velocity.
        out = run_sqf(SLUMP, [0.933, 1, 2])
        self.assertEqual(out[1], 0)
        self.assertFalse(out[4])


class TestGasMixtureDensity(unittest.TestCase):
    def test_transition_at_the_degadis_threshold(self):
        # delrhomin = 0.025: chlorine transitions at 0.051 kg/m3 (51 g/m3).
        out = run_sqf(MIX, [0, 2.447])
        expected = RHO_A * 0.025 / (1 - 1 / 2.447)
        self.assertAlmostEqual(out[2], expected, places=9)
        self.assertAlmostEqual(out[2] * 1000, 50.9, places=1)

    def test_issue_ratio_threshold_gives_204(self):
        # The issue's "ratio < 1.1" rule (unsourced) gives 0.204 kg/m3 for
        # chlorine, i.e. 204 g/m3.  The issue prints this as "204 mg/m3",
        # a factor-1000 unit slip; the kernel returns kg/m3.
        out = run_sqf(MIX, [0, 2.447, 0.1])
        self.assertAlmostEqual(out[2] * 1000, 204.0, places=0)

    def test_mixture_ratio_and_dense_flag(self):
        # At the transition concentration the cloud is exactly at the edge.
        c_trans = run_sqf(MIX, [0, 2.447])[2]
        out = run_sqf(MIX, [c_trans * 2, 2.447])
        self.assertTrue(out[1])
        self.assertAlmostEqual(out[0] - 1, 2 * 0.025, places=9)

    def test_neutral_gas_never_dense(self):
        out = run_sqf(MIX, [1.0, 1.0])
        self.assertFalse(out[1])
        self.assertEqual(out[2], 0)


class TestDenseGasPooling(unittest.TestCase):
    def test_pool_depth_and_enhancement(self):
        # A 3 m hollow doubles the concentration at k_pool = 0.5 only if
        # the gain is 1.5x; here 0.1 kg/m3 -> 0.25 kg/m3.
        out = run_sqf(POOL, [0, 3, 0.1, 0.5])
        self.assertEqual(out[0], 3)
        self.assertAlmostEqual(out[1], 0.1 * (1 + 0.5 * 3), places=9)

    def test_no_pool_on_a_ridge(self):
        out = run_sqf(POOL, [5, 0, 0.1, 0.5])
        self.assertEqual(out[0], 0)
        self.assertAlmostEqual(out[1], 0.1, places=9)


class TestPoolEvaporation(unittest.TestCase):
    def test_flux_matches_kawamura_mackay(self):
        # Reproduce the kernel arithmetic in Python.
        wind, x, m, p, ts, sc = 2.0, 2.0, 70.9, 101325.0, 239.15, 0.7
        k = 0.029 * (wind * 3600) ** 0.78 * x**-0.11 * sc**-0.67
        expected = k * m * p / (8.314 * ts) / 1000 / 3600
        self.assertAlmostEqual(run_sqf(EVAP, [wind, x, m, p, ts]), expected, places=12)

    def test_flux_rises_with_wind(self):
        calm = run_sqf(EVAP, [1, 2, 70.9, 101325, 239.15])
        windy = run_sqf(EVAP, [5, 2, 70.9, 101325, 239.15])
        self.assertGreater(windy, calm)

    def test_no_vapour_pressure_no_flux(self):
        self.assertEqual(run_sqf(EVAP, [2, 2, 70.9, 0, 293.15]), 0)


class TestToxicExposure(unittest.TestCase):
    # CS endpoints: AEGL-2 0.083, AEGL-3 11 (60 min), IDLH 2, TLV 0.4.
    CS = [0.083, 11.0, 2.0, 0.4]

    def test_cs_ladder(self):
        # For CS the TLV (0.4) sits above the AEGL-2 (0.083), so the AEGL-2
        # tier dominates and "tlv" is unreachable; the ladder is tested
        # through chlorine below.
        self.assertEqual(run_sqf(TOX, [0.004] + self.CS), "none")
        self.assertEqual(run_sqf(TOX, [0.083] + self.CS), "aegl-2")
        self.assertEqual(run_sqf(TOX, [0.4] + self.CS), "aegl-2")
        self.assertEqual(run_sqf(TOX, [2.0] + self.CS), "idlh")
        self.assertEqual(run_sqf(TOX, [11.0] + self.CS), "aegl-3")

    def test_chlorine_ladder_orders_idlh_below_aegl3(self):
        # Chlorine: AEGL-2 5.80, AEGL-3 58.0, IDLH 29.0, TLV 1.45 mg/m3.
        chl = [5.80, 58.0, 29.0, 1.45]
        self.assertEqual(run_sqf(TOX, [1.45] + chl), "tlv")
        self.assertEqual(run_sqf(TOX, [5.80] + chl), "aegl-2")
        self.assertEqual(run_sqf(TOX, [29.0] + chl), "idlh")
        self.assertEqual(run_sqf(TOX, [58.0] + chl), "aegl-3")

    def test_unpublished_endpoints_are_skipped(self):
        # Sarin has no published endpoint in the table: zeros, so "none".
        self.assertEqual(run_sqf(TOX, [1000, 0, 0, 0, 0]), "none")


class TestKernelsArePure(unittest.TestCase):
    KERNELS = (PROPS, SLUMP, MIX, POOL, EVAP, TOX)

    def test_no_engine_reads_or_writes(self):
        for path in self.KERNELS:
            code = _strip_comments(path.read_text(encoding="utf-8"))
            for forbidden in ("missionNamespace", "setVariable", "diag_log", "random"):
                self.assertNotIn(forbidden, code, f"{path.name} is not pure")

    def test_each_declares_its_purity(self):
        for path in self.KERNELS:
            self.assertIn("Pure:", path.read_text(encoding="utf-8"))


class TestSources(unittest.TestCase):
    def test_degadis_cited(self):
        self.assertIn("DEGADIS", SLUMP.read_text(encoding="utf-8"))
        self.assertIn("1.15", SLUMP.read_text(encoding="utf-8"))

    def test_kawamura_mackay_cited(self):
        self.assertIn("Kawamura", EVAP.read_text(encoding="utf-8"))
        self.assertIn("Mackay & Matsugu", EVAP.read_text(encoding="utf-8"))

    def test_aegl_and_idlh_cited(self):
        props = PROPS.read_text(encoding="utf-8")
        self.assertIn("AEGL", props)
        self.assertIn("IDLH", props)


class TestWiring(unittest.TestCase):
    def test_functions_are_prep_registered(self):
        prep = PREP.read_text(encoding="utf-8")
        for name in (
            "getGasProperties",
            "calculateDenseGasSlumping",
            "calculateGasMixtureDensity",
            "calculateDenseGasPooling",
            "calculatePoolEvaporation",
            "classifyToxicExposure",
            "calculateDenseGasDispersion",
        ):
            self.assertIn(f"PREPS(dispersion,{name})", prep, f"{name} not PREP'd")

    def test_setting_is_declared_and_read_with_the_same_case(self):
        # The slider macro takes the bare name (no literal QGVAR); the LIST
        # setting is the explicit form.  The driver must read the same case
        # the declaration produces (CBA names are case-sensitive).
        settings = SETTINGS.read_text(encoding="utf-8")
        driver = DRIVER.read_text(encoding="utf-8")
        self.assertIn("AEE_SETTING_SLIDER(denseGasCloudHeight,", settings)
        self.assertIn("QGVAR(denseGasCloudHeight)", driver)
        self.assertIn("AEE_SETTING_SLIDER(denseGasPoolDiameter,", settings)
        self.assertIn("QGVAR(denseGasPoolDiameter)", driver)
        self.assertIn("QGVAR(denseGasAgent)", settings)
        self.assertIn("QGVAR(denseGasAgent)", driver)

    def test_stringtable_has_the_setting_keys(self):
        table = STRINGTABLE.read_text(encoding="utf-8")
        for name in ("denseGasAgent", "denseGasCloudHeight", "denseGasPoolDiameter"):
            self.assertIn(f"STR_AEE_Weather_{name}_Name", table)
            self.assertIn(f"STR_AEE_Weather_{name}_Description", table)

    def test_environment_tick_calls_the_driver(self):
        self.assertIn(
            "[] call EFUNC(weather,calculateDenseGasDispersion)",
            ENV.read_text(encoding="utf-8"),
        )

    def test_suite_is_registered(self):
        self.assertIn(
            "tools/tests/test_dense_gas.py", RUNNER.read_text(encoding="utf-8")
        )


if __name__ == "__main__":
    unittest.main()
