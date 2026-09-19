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
    "addons/thermal/functions/fnc_calculateFreezingRain.sqf",
    "addons/thermal/functions/fnc_calculateHeatIndex.sqf",
    "addons/thermal/functions/fnc_calculateWBGT.sqf",
    "addons/environmental/functions/fnc_calculateBiologicalAmbient.sqf",
    "addons/environmental/functions/fnc_calculateCBRNPersistence.sqf",
    "addons/environmental/functions/fnc_calculateFireSpreadRisk.sqf",
    "addons/environmental/functions/fnc_calculateSevereWeather.sqf",
    "addons/environmental/functions/fnc_calculateSnowAccumulation.sqf",
    "addons/optics/functions/fnc_calculateAttenuation.sqf",
    "addons/optics/functions/fnc_calculateMirageIntensity.sqf",
    "addons/optics/functions/fnc_calculateSmokePersistence.sqf",
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
        wbgt = Path("addons/thermal/functions/fnc_calculateWBGT.sqf").read_text(
            encoding="utf-8"
        )
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
        text = Path("addons/thermal/functions/fnc_calculateHeatIndex.sqf").read_text(
            encoding="utf-8"
        )
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
        text = Path("addons/thermal/functions/fnc_calculateWBGT.sqf").read_text(
            encoding="utf-8"
        )
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
            "addons/environmental/functions/fnc_calculateFireSpreadRisk.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("Rothermel (1972)", text)
        self.assertIn("0.03 * _fuelFactor", text)

    def test_cbrn_q10_scaling(self):
        text = Path(
            "addons/environmental/functions/fnc_calculateCBRNPersistence.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("Q10", text)
        self.assertIn("per +10", text)

    def test_thermal_contrast_flir_fom(self):
        text = Path(
            "addons/optics/functions/fnc_calculateThermalContrast.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("8 °C", text)  # delta-T full-contrast figure of merit
        self.assertIn("0.05", text)  # microbolometer NETD

    def test_smoke_taylor_and_kohler(self):
        text = Path(
            "addons/optics/functions/fnc_calculateSmokePersistence.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("Taylor", text)
        self.assertIn("Köhler", text)


if __name__ == "__main__":
    unittest.main()
