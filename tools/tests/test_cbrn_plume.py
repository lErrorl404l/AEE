#!/usr/bin/env python3
"""CBRN agent plume dispersion tests (issue #105).

Runs the REAL SQF kernels through the sqf_lite interpreter (issue #204) and
checks the issue's test vectors, so a constant change in the SQF fails here.

Sources (see each kernel header):
  Gaussian plume / puff   Turner, Workbook of Atmospheric Dispersion
                          Estimates, EPA AP-26 (1970).
  Dispersion coefficients Briggs (1973), Diffusion Estimation for Small
                          Emissions, ATDL.
  Stability class         Pasquill-Gifford: EPA SRDT (EPA-454/R-99-005
                          Table 6-7) by day, Turner AP-26 by night.
  Agent parameters        FM 3-11.9 / MCRP 3-37.1B / NTRP 3-11.32 / AFTTP(I)
                          3-2.55, Potential Military Chemical/Biological
                          Agents and Compounds, January 2005: Chapter II
                          agent tables and Appendix G.
  Persistence band        JP 1-02 / FM 3-11.9 Table G-6.

Run: python3 -m unittest tools.tests.test_cbrn_plume -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

R_GAS = 8.314462618  # J/(mol*K), CODATA 2018 (molar gas constant)

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))

from sqf_lite import run_sqf  # noqa: E402

ADDON = REPO / "addons" / "weather"
DISP = ADDON / "functions" / "dispersion"

STABILITY = DISP / "fnc_getStabilityClass.sqf"
COEFF = DISP / "fnc_getDispersionCoefficients.sqf"
PLUME = DISP / "fnc_calculatePlumeConcentration.sqf"
PUFF = DISP / "fnc_calculatePuffConcentration.sqf"
DECAY = DISP / "fnc_calculateCbrnDecay.sqf"
AGENT = DISP / "fnc_getCbrnAgent.sqf"
DOSE = DISP / "fnc_calculateCbrnDose.sqf"

UPDATE_ENV = REPO / "addons" / "core" / "functions" / "fnc_updateEnvironment.sqf"
PREP = ADDON / "XEH_PREP.hpp"
INIT_SETTINGS = ADDON / "initSettings.inc.sqf"
STRINGTABLE = ADDON / "stringtable.xml"
DRIVER = DISP / "fnc_updateCbrnPlume.sqf"


class TestStabilityClass(unittest.TestCase):
    def test_day_strong_low_wind_is_A(self):
        # Issue vector: day strong insolation, 1 m/s -> A.
        self.assertEqual(run_sqf(STABILITY, [1.0, 800, 0, True, 999]), "A")

    def test_night_overcast_moderate_wind_is_D(self):
        # Issue vector: night overcast, 4 m/s -> D.
        self.assertEqual(run_sqf(STABILITY, [4.0, 0, 6, False, 999]), "D")

    def test_day_low_radiation_is_neutral(self):
        # EPA SRDT: solar radiation < 175 W/m2 is D at every wind speed.
        self.assertEqual(run_sqf(STABILITY, [1.0, 100, 0, True, 999]), "D")

    def test_epa_srdt_day_key(self):
        # EPA-454/R-99-005 Table 6-7, every cell.
        key = {
            1.0: "AABD",
            2.5: "ABCD",
            4.0: "BBCD",
            5.5: "CCDD",
            7.0: "CDDD",
        }
        for wind, row in key.items():
            for rad, cls in zip((950, 800, 400, 100), row):
                with self.subTest(wind=wind, rad=rad):
                    self.assertEqual(run_sqf(STABILITY, [wind, rad, 0, True, 999]), cls)

    def test_night_clear_calm_is_F(self):
        self.assertEqual(run_sqf(STABILITY, [1.0, 0, 0, False, 999]), "F")

    def test_gradient_method_takes_precedence(self):
        # A measured superadiabatic gradient is class A regardless of wind.
        self.assertEqual(run_sqf(STABILITY, [10.0, 0, 8, False, -2.5]), "A")
        # A strong inversion is class F.
        self.assertEqual(run_sqf(STABILITY, [10.0, 0, 8, False, 2.0]), "F")

    def test_class_always_in_range(self):
        for wind in (0.5, 2.5, 4.0, 5.5, 7.0):
            for solar in (0, 400, 900):
                cls = run_sqf(STABILITY, [wind, solar, 0, True, 999])
                self.assertIn(cls, "ABCDEF")


class TestBriggsCoefficients(unittest.TestCase):
    def test_issue_vector_class_D(self):
        # Issue vector: Briggs rural D, x = 1 km -> sigma_y 76.3, sigma_z 37.9.
        sy, sz = run_sqf(COEFF, [1000, "D", False])
        self.assertAlmostEqual(sy, 76.3, places=1)
        self.assertAlmostEqual(sz, 37.9, places=1)

    def test_sigma_grows_with_distance(self):
        sy1, sz1 = run_sqf(COEFF, [500, "D", False])
        sy2, sz2 = run_sqf(COEFF, [2000, "D", False])
        self.assertLess(sy1, sy2)
        self.assertLess(sz1, sz2)

    def test_urban_doubles_sigma_y(self):
        rural_y, _ = run_sqf(COEFF, [1000, "D", False])
        urban_y, _ = run_sqf(COEFF, [1000, "D", True])
        self.assertAlmostEqual(urban_y, rural_y * 2, places=4)

    def test_class_A_spreads_more_than_F(self):
        # The unstable class has the larger crosswind spread at short range.
        ay, _ = run_sqf(COEFF, [500, "A", False])
        fy, _ = run_sqf(COEFF, [500, "F", False])
        self.assertGreater(ay, fy)


class TestPlumeConcentration(unittest.TestCase):
    def test_issue_vector_ground_source(self):
        # Issue vector: Q=100000, U=5, rural D at 1 km, ground source
        # -> C = 2.20 mg/m3.
        sy, sz = run_sqf(COEFF, [1000, "D", False])
        c = run_sqf(PLUME, [100000, 5, sy, sz, 0, 0, 0])
        self.assertAlmostEqual(c, 2.20, places=1)

    def test_issue_vector_elevated_height(self):
        # Issue vector: H = 50 m -> C = 0.92 mg/m3.
        sy, sz = run_sqf(COEFF, [1000, "D", False])
        c = run_sqf(PLUME, [100000, 5, sy, sz, 50, 0, 0])
        self.assertAlmostEqual(c, 0.92, places=1)

    def test_ground_source_matches_closed_form(self):
        # Ground source, ground level: C = Q/(pi U sigma_y sigma_z).
        import math

        sy, sz = 20.0, 10.0
        c = run_sqf(PLUME, [1000, 3, sy, sz, 0, 0, 0])
        self.assertAlmostEqual(c, 1000 / (math.pi * 3 * sy * sz), places=6)

    def test_crosswind_decays(self):
        sy, sz = 20.0, 10.0
        centre = run_sqf(PLUME, [1000, 3, sy, sz, 0, 0, 0])
        off = run_sqf(PLUME, [1000, 3, sy, sz, 0, 30, 0])
        self.assertLess(off, centre)


class TestPuffConcentration(unittest.TestCase):
    def test_centre_matches_closed_form(self):
        import math

        c = run_sqf(PUFF, [1000, 20, 20, 10, 0, 0])
        self.assertAlmostEqual(
            c, 1000 / ((2 * math.pi) ** 1.5 * 20 * 20 * 10), places=6
        )

    def test_off_centre_decays(self):
        centre = run_sqf(PUFF, [1000, 20, 20, 10, 0, 0])
        off = run_sqf(PUFF, [1000, 20, 20, 10, 40, 0])
        self.assertLess(off, centre)


class TestDecay(unittest.TestCase):
    """The point half-life path: a caller that holds a measured point value
    still gets the single first-order decayed number."""

    def test_exactly_half_after_one_half_life(self):
        # Issue vector: exactly 0.5 * C0 after one half-life.
        c = run_sqf(DECAY, [100.0, 36.0, 36.0])
        self.assertAlmostEqual(c, 50.0, places=6)

    def test_point_half_life_is_still_supported(self):
        self.assertAlmostEqual(run_sqf(DECAY, [1.0, 36.0, 36.0]), 0.5, places=6)

    def test_quarter_after_two_half_lives(self):
        self.assertAlmostEqual(run_sqf(DECAY, [1.0, 2.0, 1.0]), 0.25, places=6)


class TestDecayEnvelope(unittest.TestCase):
    """No point half-life is published for any agent, so the row carries the
    JP 1-02 / FM 3-11.9 Table G-6 persistence band and the kernel returns the
    decay envelope between the band limits."""

    def test_zero_time_envelope_is_the_initial_concentration(self):
        self.assertEqual(run_sqf(DECAY, [2.0, 0.0, [24, 336]]), [2.0, 2.0])

    def test_envelope_brackets_the_band(self):
        fast, slow = run_sqf(DECAY, [1.0, 24.0, [24, 336]])
        # The fast edge is one half-life at the 24 h band limit.
        self.assertAlmostEqual(fast, 0.5, places=6)
        # The slow edge decays on the 336 h band limit.
        self.assertAlmostEqual(slow, math.exp(-24.0 / (336.0 / math.log(2))), places=6)
        self.assertLess(fast, slow)

    def test_envelope_never_inverts(self):
        for band in ([24, 336], [336, 24], [10 / 60, 15 / 60], [0.5, 0.5]):
            with self.subTest(band=band):
                fast, slow = run_sqf(DECAY, [1.0, 1.0, band])
                self.assertLessEqual(fast, slow)

    def test_both_edges_decay_with_time(self):
        f1, s1 = run_sqf(DECAY, [1.0, 1.0, [24, 336]])
        f2, s2 = run_sqf(DECAY, [1.0, 2.0, [24, 336]])
        self.assertLess(f2, f1)
        self.assertLess(s2, s1)

    def test_reversed_band_is_the_same_band(self):
        self.assertEqual(
            run_sqf(DECAY, [1.0, 3.0, [24, 336]]),
            run_sqf(DECAY, [1.0, 3.0, [336, 24]]),
        )

    def test_temperature_scales_the_band_per_agent(self):
        # Clausius-Clapeyron on the agent's latent heat (FM 3-11.9 Appendix G):
        # VX (80.3 kJ/mol) slows from 25 to 15 C far more than CG (24.8).
        vx = run_sqf(DECAY, [1.0, 24.0, [24, 336], 288.15, 80.3e3])[0]
        cg = run_sqf(DECAY, [1.0, 24.0, [24, 336], 288.15, 24.8e3])[0]
        warm = run_sqf(DECAY, [1.0, 24.0, [24, 336], 298.15, 80.3e3])[0]
        self.assertGreater(vx, warm)
        self.assertGreater(vx, cg)

    def test_no_agent_no_temperature_term(self):
        # No deltaHvap means no source for a temperature term.
        cold, _ = run_sqf(DECAY, [1.0, 24.0, [24, 336], 288.15, 0])
        warm, _ = run_sqf(DECAY, [1.0, 24.0, [24, 336], 298.15, 0])
        self.assertAlmostEqual(cold, warm, places=9)

    def test_implied_q10_matches_the_source(self):
        # The report's deltaHvap-implied Q10 over 15-25 C per agent.
        for dh_kjmol, q10 in (
            (24.8, 1.42),
            (48.5, 1.97),
            (55.2, 2.17),
            (62.8, 2.42),
            (80.3, 3.09),
        ):
            with self.subTest(dh_kjmol=dh_kjmol):
                got = math.exp(dh_kjmol * 1000 / R_GAS * 10 / (288 * 298))
                self.assertAlmostEqual(got, q10, places=1)


def decay_slow_edge(c0, elapsed_h, band, temp_k, dh_jmol, ea_jmol=0.0):
    """Mirror of the slow edge of fnc_calculateCbrnDecay.

    The slope is the published hydrolysis activation energy where the agent
    has one, else the latent heat.  tau_hi = band_hi * factor / ln 2.
    """
    slope = ea_jmol if ea_jmol != 0 else dh_jmol
    factor = 1.0
    if slope != 0:
        factor = math.exp((slope / R_GAS) * (1 / temp_k - 1 / 298.15))
    tau_hi = (band[1] * factor) / math.log(2)
    return c0 * math.exp(-elapsed_h / tau_hi)


class TestDecayActivationEnergy(unittest.TestCase):
    """A published hydrolysis activation energy outranks the latent heat.

    GD 64.25 kJ/mol (Wu et al. 2021, E3S Web Conf 267:02060) and HD
    108.8 kJ/mol (Herriott 1947, J Gen Physiol 30(6):457-464, the H.2TDG
    sulfonium salt, a related species).  GB, VX and CG keep the deltaHvap
    interim slope, because no activation energy was found for them.
    """

    BAND = [24, 336]
    GD_DHVAP = 55.2e3
    GD_EA = 64.25e3
    HD_DHVAP = 62.8e3
    HD_EA = 108.8e3
    # Long enough that the half-life difference shows in the concentration.
    ELAPSED = 2000.0

    def _slow(self, temp_k, dh, ea=0.0):
        return run_sqf(DECAY, [1.0, self.ELAPSED, self.BAND, temp_k, dh, ea])[1]

    def test_the_ea_is_preferred_when_both_are_supplied(self):
        # At the 25 C reference the factor is 1 either way, so the two agree
        # only there; a temperature away from it separates them.
        self.assertAlmostEqual(
            self._slow(298.15, self.HD_DHVAP, self.HD_EA),
            self._slow(298.15, self.HD_DHVAP),
        )
        self.assertNotAlmostEqual(
            self._slow(303.15, self.HD_DHVAP, self.HD_EA),
            self._slow(303.15, self.HD_DHVAP),
            places=4,
        )

    def test_the_temperature_factor_changes_by_the_known_ratio(self):
        # At 30 C the published HD Ea shortens the half-life by the ratio
        # exp((Ea - dhvap)/R * (1/T - 1/Tref)) = 0.736, i.e. 36 percent.
        ea = self._slow(303.15, self.HD_DHVAP, self.HD_EA)
        dh = self._slow(303.15, self.HD_DHVAP)
        self.assertLess(ea, dh)
        self.assertAlmostEqual(
            ea,
            decay_slow_edge(
                1.0, self.ELAPSED, self.BAND, 303.15, self.HD_DHVAP, self.HD_EA
            ),
            places=9,
        )
        self.assertAlmostEqual(
            dh,
            decay_slow_edge(1.0, self.ELAPSED, self.BAND, 303.15, self.HD_DHVAP),
            places=9,
        )
        half_life_ratio = math.exp(
            ((self.HD_EA - self.HD_DHVAP) / R_GAS) * (1 / 303.15 - 1 / 298.15)
        )
        self.assertAlmostEqual(half_life_ratio, 0.736, places=3)

    def test_the_ea_slows_the_cold_band(self):
        # Below the reference the larger slope is the longer half-life.
        self.assertGreater(
            self._slow(293.15, self.HD_DHVAP, self.HD_EA),
            self._slow(293.15, self.HD_DHVAP),
        )

    def test_gd_moves_the_same_way(self):
        # The published GD Ea is a 6 percent change at 30 C.
        self.assertLess(
            self._slow(303.15, self.GD_DHVAP, self.GD_EA),
            self._slow(303.15, self.GD_DHVAP),
        )
        self.assertAlmostEqual(
            math.exp(
                ((self.GD_EA - self.GD_DHVAP) / R_GAS) * (1 / 303.15 - 1 / 298.15)
            ),
            0.942,
            places=3,
        )

    def test_agents_without_an_ea_are_unchanged(self):
        # GB 48.5, VX 80.3 and CG 24.8 kJ/mol carry 0 in row 5, so the
        # five-argument and six-argument forms must agree for them.
        for agent in ("GB", "VX", "CG"):
            with self.subTest(agent=agent):
                row = run_sqf(AGENT, [agent])
                self.assertEqual(row[5], 0)
                dh = row[3] * 1000
                self.assertAlmostEqual(
                    run_sqf(
                        DECAY, [1.0, self.ELAPSED, row[4], 288.15, dh, row[5] * 1000]
                    )[1],
                    run_sqf(DECAY, [1.0, self.ELAPSED, row[4], 288.15, dh])[1],
                    places=9,
                )

    def test_gd_and_hd_carry_the_published_ea(self):
        self.assertEqual(run_sqf(AGENT, ["GD"])[5] * 1000, self.GD_EA)
        self.assertAlmostEqual(run_sqf(AGENT, ["H"])[5] * 1000, self.HD_EA)

    def test_the_plume_kernel_passes_the_ea(self):
        # The plume must feed row 5 as well, or it scales temperature
        # differently from the persistence kernel for GD and HD.
        driver = DRIVER.read_text(encoding="utf-8")
        self.assertIn("_agentRow select 5", driver)
        self.assertIn("_deltaHvapJmol, _eaJmol] call FUNC(calculateCbrnDecay)", driver)


class TestAgentTable(unittest.TestCase):
    """The FM 3-11.9 (January 2005) rows: LCt50, vapour pressure, volatility,
    latent heat of vaporisation and the JP 1-02 persistence band."""

    def test_vx_row(self):
        row = run_sqf(AGENT, ["VX"])
        self.assertEqual(row[0], 15)  # LCt50, Table II-15
        self.assertAlmostEqual(row[1], 8.78e-4)  # VP torr at 25 C
        self.assertAlmostEqual(row[2], 12.6)  # volatility mg/m3
        self.assertAlmostEqual(row[3], 80.3)  # dHvap kJ/mol
        self.assertEqual(row[4], [24, 336])  # JP 1-02 persistent

    def test_gb_row(self):
        row = run_sqf(AGENT, ["GB"])
        self.assertEqual(row[0], 35)  # Table II-9
        self.assertAlmostEqual(row[1], 2.48)
        self.assertAlmostEqual(row[2], 18700)
        self.assertAlmostEqual(row[3], 48.5)
        self.assertAlmostEqual(row[4][0], 10 / 60)
        self.assertAlmostEqual(row[4][1], 15 / 60)

    def test_gd_row(self):
        row = run_sqf(AGENT, ["GD"])
        self.assertEqual(row[0], 35)  # Table II-11
        self.assertAlmostEqual(row[1], 0.401)
        self.assertAlmostEqual(row[2], 3930)
        self.assertAlmostEqual(row[3], 55.2)

    def test_cg_row(self):
        row = run_sqf(AGENT, ["CG"])
        self.assertEqual(row[0], 1500)  # Table II-3
        self.assertAlmostEqual(row[1], 1400)
        self.assertAlmostEqual(row[2], 7.46e6)
        self.assertAlmostEqual(row[3], 24.8)

    def test_h_row_is_the_default(self):
        row = run_sqf(AGENT, ["H"])
        self.assertEqual(row[0], 1000)  # Table II-25
        self.assertAlmostEqual(row[1], 0.106)
        self.assertAlmostEqual(row[2], 906)
        self.assertAlmostEqual(row[3], 62.8)
        self.assertEqual(row[4], [24, 336])

    def test_case_insensitive(self):
        self.assertEqual(run_sqf(AGENT, ["vx"]), run_sqf(AGENT, ["VX"]))

    def test_unknown_defaults_to_H(self):
        self.assertEqual(run_sqf(AGENT, ["XX"]), run_sqf(AGENT, ["H"]))

    def test_every_row_carries_a_band_not_a_point(self):
        for agent in ("VX", "GB", "GD", "H", "CG"):
            with self.subTest(agent=agent):
                band = run_sqf(AGENT, [agent])[4]
                self.assertIsInstance(band, list)
                self.assertEqual(len(band), 2)
                self.assertLess(band[0], band[1])


class TestDose(unittest.TestCase):
    def test_issue_vector_vx_lethal_in_4_5_min(self):
        # Issue vector: LCt50 10 (the vector's own value; VX's FM 3-11.9
        # value is 15, and the kernel takes LCt50 as an argument) at
        # 2.20 mg/m3 is lethal in ~4.5 min (10 / 2.20 = 4.545 min).
        dt = 4.55 * 60
        _, lethal, _ = run_sqf(DOSE, [0, 2.20, dt, 10, 0])
        self.assertTrue(lethal)
        # At 4.4 min (9.68 mg*min/m3) it has not yet reached LCt50.
        _, below, _ = run_sqf(DOSE, [0, 2.20, 4.4 * 60, 10, 0])
        self.assertFalse(below)

    def test_not_lethal_below_lct50(self):
        _, lethal, _ = run_sqf(DOSE, [0, 2.20, 60, 10, 0])
        self.assertFalse(lethal)

    def test_incapacitated_at_one_tenth_lct50(self):
        # 0.1 * LCt50 = 1.0 -> 2.20 mg/m3 for 1 min gives 2.2 -> incapacitated.
        _, _, inc = run_sqf(DOSE, [0, 2.20, 60, 10, 0])
        self.assertTrue(inc)

    def test_protection_scales_the_dose(self):
        full, _, _ = run_sqf(DOSE, [0, 2.20, 60, 10, 0])
        blocked, _, _ = run_sqf(DOSE, [0, 2.20, 60, 10, 0.95])
        self.assertLess(blocked, full)

    def test_dose_accumulates(self):
        new, _, _ = run_sqf(DOSE, [5.0, 2.20, 60, 10, 0])
        self.assertAlmostEqual(new, 5.0 + 2.20, places=6)


class TestWiring(unittest.TestCase):
    """Source locks: the kernels are PREP'd, scheduled and configured."""

    def test_kernels_are_prepared(self):
        prep = PREP.read_text(encoding="utf-8")
        for name in (
            "getStabilityClass",
            "getDispersionCoefficients",
            "calculatePlumeConcentration",
            "calculatePuffConcentration",
            "calculateCbrnDecay",
            "getCbrnAgent",
            "calculateCbrnDose",
            "startCbrnRelease",
            "updateCbrnPlume",
        ):
            self.assertIn(f"PREPS(dispersion,{name})", prep)

    def test_tick_calls_the_driver(self):
        env = UPDATE_ENV.read_text(encoding="utf-8")
        self.assertIn("EFUNC(weather,updateCbrnPlume)", env)

    def test_setting_registered_and_read(self):
        self.assertIn("CbrnPlumeEnabled", INIT_SETTINGS.read_text(encoding="utf-8"))
        self.assertIn("GVAR(CbrnPlumeEnabled)", DRIVER.read_text(encoding="utf-8"))

    def test_stringtable_has_the_setting_strings(self):
        st = STRINGTABLE.read_text(encoding="utf-8")
        self.assertIn("STR_AEE_Weather_CbrnPlumeEnabled_Name", st)
        self.assertIn("STR_AEE_Weather_CbrnPlumeEnabled_Description", st)

    def test_driver_reuses_the_existing_wind_and_protection(self):
        driver = DRIVER.read_text(encoding="utf-8")
        self.assertIn("EGVAR(core,currentWind)", driver)
        self.assertIn("EFUNC(persistence,getCbrnProtection)", driver)

    def test_driver_decays_the_band_envelope(self):
        # The driver must pass the band, the air temperature and the agent's
        # latent heat to the decay kernel, and take the slow (casualty
        # conservative) edge of the envelope.
        driver = DRIVER.read_text(encoding="utf-8")
        self.assertIn("_agentRow select 4", driver)
        self.assertIn("_envelope select 1", driver)
        self.assertIn("QEGVAR(core,currentTemperature)", driver)
        self.assertIn("KELVIN_OFFSET", driver)
        self.assertIn("_agentRow select 3) * 1000", driver)

    def test_core_tick_supplies_the_agent_delta_hvap(self):
        # The persistence kernel cannot resolve an agent, so the tick passes
        # the active agent's dHvap and its published hydrolysis Ea.
        env = UPDATE_ENV.read_text(encoding="utf-8")
        self.assertIn("EFUNC(weather,getCbrnAgent)", env)
        self.assertIn("_cbrnRow select 3", env)
        self.assertIn("_cbrnRow select 5", env)
        self.assertIn(
            "[_cbrnDeltaHvapJmol, _cbrnEaJmol] call EFUNC(persistence,calculateCBRNPersistence)",
            env,
        )


if __name__ == "__main__":
    unittest.main()
