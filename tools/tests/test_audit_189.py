"""Issue #189 audit drift-locks.

Locks the two outcomes of the calculation audit:

1.  SAFE-READ PATTERN: every consumer of shared core state must read
    via `missionNamespace getVariable [QEGVAR(...)/QGVAR(...), default]`.
    A bare `EGVAR(core,currentX)` reference throws "Undefined variable
    in expression" when called before the producer runs (the #124
    state-read bug class).  The hardened pattern is the convention.

2.  SOURCED CONSTANTS: the verified physics constants must stay pinned
    to their published sources.  A future edit that changes a constant
    without updating the citation breaks these tests.
"""

import re
import unittest
from pathlib import Path

# Files hardened in the #189 Phase 1 sweep.  No bare EGVAR reads allowed.
HARDENED_FILES = [
    "addons/thermal/functions/environment/fnc_calculateFreezingRain.sqf",
    "addons/thermal/functions/environment/fnc_calculateHeatIndex.sqf",
    "addons/thermal/functions/environment/fnc_calculateWBGT.sqf",
    "addons/environmental/functions/warnings/fnc_calculateBiologicalAmbient.sqf",
    "addons/environmental/functions/warnings/fnc_calculateCBRNPersistence.sqf",
    "addons/environmental/functions/warnings/fnc_calculateFireSpreadRisk.sqf",
    "addons/environmental/functions/warnings/fnc_calculateSevereWeather.sqf",
    "addons/environmental/functions/terrain/fnc_calculateSnowAccumulation.sqf",
    "addons/optics/functions/sensor/fnc_calculateAttenuation.sqf",
    "addons/optics/functions/sensor/fnc_calculateMirageIntensity.sqf",
    "addons/optics/functions/sensor/fnc_calculateSmokePersistence.sqf",
]

# A bare read looks like `EGVAR(core,currentTemperature)` or
# `GVAR(thermalState)` as an expression, NOT inside a getVariable call.
BARE_READ = re.compile(r"(?<!getVariable \[)(?<!setVariable \[)\b[EG]?VAR\([^)]+\)")


class TestSafeReadPattern(unittest.TestCase):
    """Every shared-state read uses the getVariable-with-default pattern."""

    def test_no_bare_reads_in_hardened_files(self):
        for rel in HARDENED_FILES:
            text = Path(rel).read_text(encoding="utf-8")
            # Strip comments: both // and /* */ blocks.
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
            text = re.sub(r"//[^\n]*", "", text)
            # QGVAR/QEGVAR inside getVariable is the safe form; flag any
            # remaining bare [EQ]?VAR( usage that is not a setVariable
            # target.
            bare = [
                m.group(0)
                for m in BARE_READ.finditer(text)
                if "getVariable" not in text[max(0, m.start() - 30) : m.start()]
                and "setVariable" not in text[max(0, m.start() - 30) : m.start()]
            ]
            self.assertEqual(
                bare,
                [],
                f"{rel}: bare shared-state reads remain: {bare[:5]}",
            )

    def test_hardened_reads_carry_defaults(self):
        # Spot-check that the converted sites have a default argument.
        wbgt = Path(
            "addons/thermal/functions/environment/fnc_calculateWBGT.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "missionNamespace getVariable [QEGVAR(core,currentTemperature), 15]", wbgt
        )
        self.assertIn(
            "missionNamespace getVariable [QEGVAR(core,currentHumidity), 50]", wbgt
        )


class TestSourcedConstants(unittest.TestCase):
    """Physics constants stay pinned to their published sources."""

    def test_heat_index_noaa_steadman(self):
        # NOAA/NWS heat index equation (Rothfusz 1990), all coefficients.
        text = Path(
            "addons/thermal/functions/environment/fnc_calculateHeatIndex.sqf"
        ).read_text(encoding="utf-8")
        for coeff in (
            "42.379",
            "2.04901523",
            "10.14333127",
            "0.22475541",
            "6.83783e-3",
            "5.481717e-2",
            "1.22874e-3",
            "8.5282e-4",
            "1.99e-6",
        ):
            self.assertIn(coeff, text, f"HeatIndex missing {coeff}")

    def test_wbgt_stull_2011(self):
        # Stull 2011 wet-bulb constants + ISO 7243 weighting.
        text = Path(
            "addons/thermal/functions/environment/fnc_calculateWBGT.sqf"
        ).read_text(encoding="utf-8")
        for const in (
            "0.151977",
            "8.313659",
            "1.676331",
            "0.00391838",
            "0.023101",
            "4.686035",
        ):
            self.assertIn(const, text, f"WBGT missing Stull const {const}")
        self.assertIn("0.7 * _Tw + 0.2 * _Tg + 0.1 * _T_C", text)

    def test_fire_spread_rothermel_1972(self):
        text = Path(
            "addons/environmental/functions/warnings/fnc_calculateFireSpreadRisk.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("Rothermel (1972)", text)
        self.assertIn("0.03 * _fuelFactor", text)

    def test_cbrn_q10_scaling(self):
        text = Path(
            "addons/environmental/functions/warnings/fnc_calculateCBRNPersistence.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("Q10", text)
        self.assertIn("per +10", text)

    def test_thermal_contrast_flir_fom(self):
        text = Path(
            "addons/thermal/functions/sensor/fnc_calculateThermalContrast.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("8 °C", text)  # delta-T full-contrast figure of merit
        self.assertIn("0.05", text)  # microbolometer NETD

    def test_smoke_taylor_and_kohler(self):
        text = Path(
            "addons/optics/functions/sensor/fnc_calculateSmokePersistence.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("Taylor", text)
        self.assertIn("Köhler", text)


class TestTwoNodeSolver(unittest.TestCase):
    """Drift-locks for the #191 two-node SQF solver: the sourced Gagge
    physiology constants must survive porting from the Python mirror."""

    def test_two_node_file_exists_and_registered(self):
        from pathlib import Path

        fn = Path("addons/thermal/functions/solver/fnc_solveTwoNodeSelection.sqf")
        self.assertTrue(fn.exists())
        prep = Path("addons/thermal/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("solveTwoNodeSelection", prep)

    def test_gagge_physiology_constants(self):
        text = Path(
            "addons/thermal/functions/solver/fnc_solveTwoNodeSelection.sqf"
        ).read_text(encoding="utf-8")
        # Blood-flow coupling: K_min 5.28, blood cp 4186.
        self.assertIn("5.28", text)
        self.assertIn("4186", text)
        # Vasodilation/constriction signals at the neutral skin 33.7.
        self.assertIn("33.7", text)
        # Blood flow capped at 14.4 (240 ml/min/m2 max vasodilation).
        self.assertIn("14.4", text)
        # Shivering gain 19.4 with core/skin cold signals.
        self.assertIn("19.4", text)
        self.assertIn("36.8", text)
        # Gagge convection correlation (not the McAdams inert form).
        self.assertIn("8.6", text)

    def test_two_node_physics_patterns(self):
        text = Path(
            "addons/thermal/functions/solver/fnc_solveTwoNodeSelection.sqf"
        ).read_text(encoding="utf-8")
        # Analytic core solve (linear residual) - the damped 2x2 Newton
        # oscillated (traced to 1363 C).
        self.assertIn("Analytic core solution", text)
        self.assertIn("_qGen + _qShiv * _area", text)
        # Shivering uses the PERSISTENT core, never the iterating value.
        self.assertIn("_tCore0", text)
        # Bolton 1980 saturation pressure.
        self.assertIn("17.67", text)
        self.assertIn("611.2", text)
        # Lewis relation for the evaporative path.
        self.assertIn("16.5", text)
        # Asymmetric transient: wet skin cools slower (x1.5).
        self.assertIn("1.5", text)

    def test_inert_conduction_not_l_char(self):
        text = Path(
            "addons/thermal/functions/solver/fnc_solveTwoNodeSelection.sqf"
        ).read_text(encoding="utf-8")
        # The #124 audit bug: conduction must use L_cond (wall thickness),
        # not L_char (convection plate dim).
        self.assertIn("_lCond", text)
        self.assertIn("_lChar", text)
        self.assertIn("Fourier", text)


class TestWaterThermal(unittest.TestCase):
    """Drift-locks for the #193 water interaction branch: the measured
    Boutelier water coefficients and the immersion wiring must survive
    porting from the Python mirror (test_water_thermal.py)."""

    def test_boutelier_water_coefficients(self):
        from pathlib import Path

        text = Path(
            "addons/thermal/functions/solver/fnc_solveTwoNodeSelection.sqf"
        ).read_text(encoding="utf-8")
        # Boutelier, Bougues & Timbal 1977 (partitional calorimetry):
        # still water 43 (neutral) / 54 (cold+shivering) W/m2K; stirred
        # water 272.9*v^0.5 / 497.1*v^0.65.
        self.assertIn("43.0", text)
        self.assertIn("54.0", text)
        self.assertIn("272.9", text)
        self.assertIn("497.1", text)
        self.assertIn("Boutelier", text)

    def test_immersion_exchange_target_is_water(self):
        from pathlib import Path

        text = Path(
            "addons/thermal/functions/solver/fnc_solveTwoNodeSelection.sqf"
        ).read_text(encoding="utf-8")
        # An immersed surface exchanges against the WATER temperature,
        # not air or the air-side MRT.
        self.assertIn("_exchK", text)
        self.assertIn("_exchMrtK", text)
        self.assertIn("_tWater", text)

    def test_rain_forces_wettedness(self):
        from pathlib import Path

        text = Path(
            "addons/thermal/functions/solver/fnc_solveTwoNodeSelection.sqf"
        ).read_text(encoding="utf-8")
        # Rain is EXTERNAL water (not regulated sweat): drives the wet
        # state up, saturating at high rates.
        self.assertIn("_rain", text)
        self.assertIn("_rain / 0.3", text)

    def test_immersion_detected_native(self):
        from pathlib import Path

        text = Path(
            "addons/thermal/functions/display/fnc_applySelectionThermal.sqf"
        ).read_text(encoding="utf-8")
        # Immersion via native engine state: getPosASL z < 0 (submerged)
        # + surfaceIsWater - no fabricated water-speed state.
        self.assertIn("getPosASL _obj", text)
        self.assertIn("surfaceIsWater", text)
        self.assertIn("currentWaterTemperature", text)
        self.assertNotIn("currentWaterSpeed", text)


class TestWetGroundThermal(unittest.TestCase):
    """Issue #194 - wet-ground physics: moisture-dependent conductivity
    (Johansen 1975), evaporative draw (FAO-56 Penman-Monteith, Manabe
    bucket), and the [material, moisture] cache axis."""

    def test_wet_ground_solver_wired(self):
        from pathlib import Path

        text = Path(
            "addons/thermal/functions/ground/fnc_calculateGroundTemperature.sqf"
        ).read_text(encoding="utf-8")
        # The wrapper delegates to the node stack (issue #198) - the
        # stack is the ground model now.
        self.assertIn("calculateGroundNodeStack", text)
        self.assertIn("_stack select 0", text)  # surface node = layer 1
        # Material classification still happens here (never fabricates).
        self.assertIn("classifyBySurfaceType", text)
        # The moisture/evaporative physics moved to the node stack.
        stack = Path(
            "addons/thermal/functions/ground/fnc_calculateGroundNodeStack.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("QEGVAR(core,soilMoisture)", stack)
        self.assertIn("_kSat", stack)
        self.assertIn("_kDry + (_ke * (_kSat - _kDry))", stack)
        self.assertIn("_qEvap", stack)
        self.assertIn("_rs", stack)
        self.assertIn("0.75 * 0.25", stack)

    def test_wet_cache_keyed_by_moisture(self):
        from pathlib import Path

        text = Path(
            "addons/thermal/functions/ground/fnc_calculateGroundNodeStack.sqf"
        ).read_text(encoding="utf-8")
        # The node-stack cell state carries the moisture axis: keyed by
        # position grid cell + material (a wet road and a dry road are
        # different states).
        self.assertIn("_cell", text)
        self.assertIn("_material", text)
        self.assertIn("QGVAR(groundNodeStack)", text)
        # The old single-node cache is gone from the wrapper.
        wrapper = Path(
            "addons/thermal/functions/ground/fnc_calculateGroundTemperature.sqf"
        ).read_text(encoding="utf-8")
        self.assertNotIn("groundTempCache", wrapper)
        self.assertNotIn("_cacheKey = [_material, _moisture]", wrapper)

    def test_wet_ground_mirror_exists(self):
        from pathlib import Path

        text = Path("tools/tests/test_wet_ground.py").read_text(encoding="utf-8")
        # Sourced constants present.
        self.assertIn("K_DRY", text)
        self.assertIn("K_SAT", text)
        self.assertIn("RS_WET", text)
        self.assertIn("RS_DRY", text)
        self.assertIn("FC = 0.25", text)
        # The wet-bulb anchor is the primary Stull 2011 formula.
        self.assertIn("0.151977", text)
        # Johansen Kersten interpolation.
        self.assertIn("K_DRY + m * (K_SAT - K_DRY)", text)


class TestGroundNodeStack(unittest.TestCase):
    """Issue #198 - full-depth ground node-stack: the 4-layer vertical
    diffusion solve (Noah LSM geometry, Crank-Nicolson tridiagonal)
    replacing the single-node equilibrium with a persistent soil
    temperature profile."""

    def test_node_stack_solver_wired(self):
        from pathlib import Path

        text = Path(
            "addons/thermal/functions/ground/fnc_calculateGroundNodeStack.sqf"
        ).read_text(encoding="utf-8")
        # PREP registered (PREPS(ground,...) since the #203 subfolder split).
        prep = Path("addons/thermal/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREPS(ground,calculateGroundNodeStack)", prep)
        # Noah 4-layer geometry: dz 0.10/0.30/0.60/1.00 (Mitchell 2005).
        self.assertIn("[0.10, 0.30, 0.60, 1.00]", text)
        # Crank-Nicolson (unconditionally stable - Noah/CLM scheme).
        self.assertIn("Crank-Nicolson", text)
        # Persistence: per-position node temperatures.
        self.assertIn("QGVAR(groundNodeStack)", text)
        self.assertIn("_cell", text)
        # Fixed-temperature bottom boundary (Noah TBOT) as a native
        # slow EMA of air (30-day tau), never a fabricated state read.
        self.assertIn("_dt / 2592000", text)
        self.assertIn("_tBot", text)
        self.assertNotIn("annualMeanAirTemp", text)

    def test_node_stack_physics_patterns(self):
        from pathlib import Path

        text = Path(
            "addons/thermal/functions/ground/fnc_calculateGroundNodeStack.sqf"
        ).read_text(encoding="utf-8")
        # Johansen 1975 LOGARITHMIC Kersten (not the linear frozen form).
        self.assertIn("0.7 * (log _sr)", text)
        self.assertIn("Kersten", text)
        # van de Griend & Owe surface resistance: 10 s/m wet.
        self.assertIn("10 + (1990", text)
        # FAO-56 evaporative draw present.
        self.assertIn("_qEvap", text)
        # Surface half-cell transient: finite-volume dT = q*dt*2/(rho*cp*dz),
        # NOT the steady-state gradient (the mirror caught this as a 100x bug).
        self.assertIn("_dt * 2 / (_rho * _cp", text)

    def test_node_stack_mirror_exists(self):
        from pathlib import Path

        text = Path("tools/tests/test_ground_node_stack.py").read_text(encoding="utf-8")
        # Sourced constants.
        self.assertIn("ALPHA_DRY", text)
        self.assertIn("ALPHA_SAT", text)
        self.assertIn("surface_resistance", text)
        self.assertIn("10.0", text)  # RS wet (van de Griend & Owe)
        self.assertIn("2000.0", text)  # RS dry (Fuchs & Tanner)
        self.assertIn("FC = 0.25", text)
        # Noah geometry.
        self.assertIn("0.10, 0.30, 0.60, 1.00", text)
        # Crank-Nicolson tridiagonal.
        self.assertIn("Crank-Nicolson", text)
        # Campbell & Norman amplitude attenuation anchors (skin depth).
        self.assertIn("0.425", text)  # 10 cm -> 42.5%
        self.assertIn("0.014", text)  # 50 cm -> 1.4%


class TestFrostThermal(unittest.TestCase):
    """Issue #195 - frost/ice phase-change: 0C pin with latent-heat
    release (334 kJ/kg), frost deposition (Magnus over ice frost point),
    and frost emissivity (near-blackbody) feeding the FLIR contrast."""

    def test_frost_state_wired(self):
        from pathlib import Path

        # The ground wrapper applies the frost tier on the node-stack
        # surface temp.
        wrapper = Path(
            "addons/thermal/functions/ground/fnc_calculateGroundTemperature.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("calculateFrostState", wrapper)
        self.assertIn("_frost select 0", wrapper)

        # The frost function is PREP-registered.
        prep = Path("addons/thermal/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("calculateFrostState", prep)

    def test_frost_physics_patterns(self):
        from pathlib import Path

        text = Path(
            "addons/thermal/functions/ground/fnc_calculateFrostState.sqf"
        ).read_text(encoding="utf-8")
        # Latent heat of fusion (IAPWS-95 / Incropera).
        self.assertIn("334e3", text)
        # Magnus over ICE (frost point, not Bolton water).
        self.assertIn("22.46", text)
        self.assertIn("272.62", text)
        # The pin holds at 0C while film releases latent heat.
        self.assertIn("_tSurfAdjusted = 0", text)
        self.assertIn("_dm", text)
        # Frost emissivity near-blackbody.
        self.assertIn("0.97", text)
        # Film mass state persisted per grid cell.
        self.assertIn("GVAR(frostState)", text)
        self.assertIn("_filmMass", text)

    def test_frost_mirror_exists(self):
        from pathlib import Path

        text = Path("tools/tests/test_frost.py").read_text(encoding="utf-8")
        # Sourced constants.
        self.assertIn("L_FUS", text)
        self.assertIn("334e3", text)
        self.assertIn("22.46", text)  # Magnus over ice
        self.assertIn("272.62", text)
        # Hayashi 1977 density curve.
        self.assertIn("650.0", text)
        self.assertIn("0.277", text)
        # Leoni 2016 growth cap (0.1..3 mm/h).
        self.assertIn("0.1", text)
        self.assertIn("3.0", text)
        # Emissivity anchors.
        self.assertIn("0.97", text)


if __name__ == "__main__":
    unittest.main()
