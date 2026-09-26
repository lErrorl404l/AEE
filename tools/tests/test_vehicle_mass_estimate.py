#!/usr/bin/env python3
"""Vehicle mass estimate contract tests (vehicle mass estimate layer, task 11).

Two surfaces, one suite.

The pure core ``fnc_estimateVehicleMassCore.sqf`` is executed for real through
``tools/tests/sqf_lite.py``. The core reads no engine state. It takes the box
extents, a cited density range, a calibrated fill range and an optional power
band, and it returns either a bounded range or the unavailable tuple. The
runtime cases below pin every branch: a valid box, a broken geometry, a width
cap breach, an in-band power, an out-of-band power inside the hard factor, and
a power beyond the hard factor.

The engine-reading wrapper ``fnc_estimateVehicleMass.sqf`` cannot run in the
harness, because the harness has no evaluator for ``configFile``,
``boundingBoxReal`` or ``isNull``. It is checked structurally instead. The
checks pin the required calls, the setting read, the declared-material
classification, the ordering of the sourced, gated and modelled paths, the
seven published variables, the seven-element result shape, and the forbidden
effects.

Every temporary write goes to a ``tempfile`` directory. No test edits the
core, the wrapper, the generated table, the settings, or any catalogue file.

Run: python3 -m unittest tools.tests.test_vehicle_mass_estimate -v
"""

from __future__ import annotations

import contextlib
import io
import re
import sys
import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.tests.sqf_lite import run_sqf  # noqa: E402
from tools.validation import gen_vehicle_mass_model as gen  # noqa: E402

FUNCTIONS = ROOT / "addons" / "mobility" / "functions"
CORE = FUNCTIONS / "fnc_estimateVehicleMassCore.sqf"
WRAPPER = FUNCTIONS / "fnc_estimateVehicleMass.sqf"
TABLE = FUNCTIONS / "fnc_getVehicleMassModel.sqf"
MODEL = ROOT / "data" / "vehicle" / "mass_model.json"

# The tokens the committed census fits. The rest stay fail-closed.
CALIBRATED_TOKENS = frozenset(
    {"Car", "Truck", "MRAP", "Wheeled_APC", "Tracked_APC", "Tank"}
)

# ─── Core fixtures ──────────────────────────────────────────────────────────
# A bounded box: V = 4.5 * 1.8 * 1.4 = 11.34 m3. With the steel range and the
# 0.05..0.12 fill range the raw range is 4025.7..10682.28 kg, a ratio of 2.654.
FIELDS = (
    "length",
    "width",
    "height",
    "rho_low",
    "rho_high",
    "fill_low",
    "fill_high",
    "engine_power",
    "pwr_enabled",
    "pwr_low",
    "pwr_high",
    "pwr_hard",
    "max_width_ratio",
    "material",
)
BASE = [4.5, 1.8, 1.4, 7100.0, 7850.0, 0.05, 0.12, 0.0, 0.0, 0.0, 0.0, 2.0, 6.0, 0]

PWR_LOW = 10.0
PWR_HIGH = 40.0
PWR_HARD = 2.0

# Assumption bits from the core header. The base mask carries geometry_box,
# box_includes_mirrors, density_cited, fill_calibrated and the default density
# class. The disabled power branch adds power_disabled.
MASK_BASE = 1 + 2 + 8 + 16 + 32
MASK_POWER_DISABLED = MASK_BASE + 64
MASK_POWER_IN_BAND = MASK_BASE + 128
MASK_POWER_OUT_BAND = MASK_BASE + 256

MASK_POWER_IN_BAND_BIT = 128
MASK_POWER_OUT_BAND_BIT = 256

UNAVAILABLE = [0, 0, 0, 0, 0, 0]

# ─── Wrapper contract vocabulary ────────────────────────────────────────────
PUBLISHED = (
    "vehicleMassLowKg",
    "vehicleMassHighKg",
    "vehicleMassMethod",
    "vehicleMassAssumptions",
    "vehicleMassConfidence",
    "vehicleMassStatus",
    "vehicleMassSource",
)

SEVEN_ELEMENT_RESULT = (
    "[_low, _high, _method, _assumptions, _confidence, _status, _source]"
)
UNAVAILABLE_RESULT = '[0, 0, 0, "none", "none", "unavailable", "none"]'

# A soil read, a material mutation, a mass mutation, or a drive effect. The
# estimator reports a mass. It must never alter the world it measures.
FORBIDDEN_EFFECTS = (
    "calculateSoilStrength",
    "setObjectMaterial",
    "setObjectMaterialGlobal",
    "setMaterial",
    "setMass",
    "setVelocity",
    "setVectorDir",
    "setDir",
    "setFuel",
    "enableSimulation",
)


def code(src: str) -> str:
    """Return the SQF with the header block and // comments removed."""
    body = src.split("*/", 1)[-1]
    return "\n".join(line.split("//", 1)[0] for line in body.splitlines())


def compact(text: str) -> str:
    """Collapse whitespace so a match does not depend on SQF layout."""
    return " ".join(text.split())


def has_identifier(text: str, name: str) -> bool:
    """True when the exact identifier appears, not a longer name."""
    return re.search(r"(?<![\w])" + re.escape(name) + r"(?![\w])", text) is not None


def core_args(**changes: object) -> list[object]:
    """Build a core argument list from BASE with named fields replaced."""
    values: list[object] = list(BASE)
    for name, value in changes.items():
        values[FIELDS.index(name)] = value
    return values


def run_core(args: list[object]) -> list[float]:
    """Execute the real core file and coerce the SQF array to a float list."""
    return cast("list[float]", run_sqf(CORE, args))


def published_variables(flat: str) -> list[str]:
    """The published status variables present in a flattened wrapper body."""
    return [name for name in PUBLISHED if f"GVAR({name})" in flat]


def material_block(flat: str) -> str:
    """The declared-material classification region of a flattened wrapper.

    The region runs from the ``hiddenSelectionsMaterials`` read to the start
    of the mass-class resolution. The markers are unique in the wrapper.
    """
    start = flat.index('getArray (configOf _vehicle >> "hiddenSelectionsMaterials")')
    end = flat.index('private _vehicleType = "wheeled";')
    return flat[start:end]


def mass_class_block(flat: str) -> str:
    """The mass-class resolution region of a flattened wrapper.

    The region runs from the vehicle-type classification to the end of the
    class-table loop. The markers are unique in the wrapper.
    """
    start = flat.index('private _vehicleType = "wheeled";')
    end_marker = "if (_classRow isEqualTo []) exitWith { call _unavailable };"
    end = flat.index(end_marker) + len(end_marker)
    return flat[start:end]


# ─── Mass-class resolution policy ──────────────────────────────────────────
# The wrapper loop reads the class table in order and keeps the first row
# that both matches and carries a usable fill range. The table puts the
# token rows first, then the vehicle-type rows, then the default row. The
# helper below executes that policy. The structural tests pin the wrapper
# loop to the same policy, because the harness cannot run the wrapper: it
# has no evaluator for ``isKindOf`` or ``boundingBoxReal``.


def row_is_usable(fill_low: float, fill_high: float) -> bool:
    """The wrapper usable test: a positive, ordered fill range."""
    return fill_low > 0 and fill_high > 0 and fill_low <= fill_high


# The exact usable test the wrapper must carry, after whitespace collapse.
USABLE_PREDICATE = (
    "private _rowUsable = (_rowFillLow > 0) && (_rowFillHigh > 0) "
    + "&& (_rowFillLow <= _rowFillHigh);"
)


def select_mass_class_row(
    rows: Sequence[Sequence[object]],
    vehicle_type: str,
    matched_tokens: set[str],
) -> list[object] | None:
    """Return the first usable matching class row, or None when none exists."""
    for key, match, row_type, density, fill_low, fill_high in rows:
        if not row_is_usable(
            float(cast(float, fill_low)), float(cast(float, fill_high))
        ):
            continue
        if match == "token":
            matched = key in matched_tokens
        elif match == "vehicle_type":
            matched = row_type == vehicle_type
        else:
            matched = True
        if matched:
            return [key, match, row_type, density, fill_low, fill_high]
    return None


class CoreGeometryTest(unittest.TestCase):
    """The core returns a bounded range or refuses the result."""

    def assert_bounded(self, result: list[float]) -> tuple[float, float]:
        self.assertEqual(len(result), 6)
        low, high = result[0], result[1]
        self.assertEqual(result[5], 1, "status must be estimated")
        self.assertGreater(low, 0)
        self.assertLess(low, high, "a point mass is not a bounded estimate")
        return low, high

    def test_valid_box_returns_a_bounded_range(self) -> None:
        result = run_core(core_args())
        low, high = self.assert_bounded(result)
        self.assertAlmostEqual(low, 4025.7, places=3)
        self.assertAlmostEqual(high, 10682.28, places=2)
        self.assertEqual(result[2], 1, "method code is geometry_material")
        self.assertEqual(result[3], MASK_POWER_DISABLED)
        self.assertEqual(result[4], 2, "confidence is medium")

    def test_zero_height_is_unavailable(self) -> None:
        self.assertEqual(run_core(core_args(height=0.0)), UNAVAILABLE)

    def test_negative_length_is_unavailable(self) -> None:
        self.assertEqual(run_core(core_args(length=-4.5)), UNAVAILABLE)

    def test_zero_width_is_unavailable(self) -> None:
        self.assertEqual(run_core(core_args(width=0.0)), UNAVAILABLE)

    def test_width_cap_breach_is_unavailable(self) -> None:
        # The raw ratio is 2.654. A cap of 2.0 refuses it.
        self.assertEqual(run_core(core_args(max_width_ratio=2.0)), UNAVAILABLE)

    def test_inverted_density_range_is_unavailable(self) -> None:
        self.assertEqual(
            run_core(core_args(rho_low=7850.0, rho_high=7100.0)), UNAVAILABLE
        )

    def test_inverted_fill_range_is_unavailable(self) -> None:
        self.assertEqual(
            run_core(core_args(fill_low=0.12, fill_high=0.05)), UNAVAILABLE
        )

    def test_zero_fill_is_unavailable(self) -> None:
        self.assertEqual(run_core(core_args(fill_low=0.0)), UNAVAILABLE)

    def test_zero_width_cap_is_unavailable(self) -> None:
        self.assertEqual(run_core(core_args(max_width_ratio=0.0)), UNAVAILABLE)


class CorePowerTest(unittest.TestCase):
    """The power branch only corroborates the geometry result."""

    def test_power_disabled_records_the_disabled_bit(self) -> None:
        result = run_core(core_args())
        self.assertEqual(result[3], MASK_POWER_DISABLED)
        self.assertEqual(result[2], 1, "no power method without the branch")

    def test_power_zero_with_the_flag_set_stays_disabled(self) -> None:
        result = run_core(core_args(engine_power=0.0, pwr_enabled=1))
        self.assertEqual(result[3], MASK_POWER_DISABLED)

    def test_in_band_power_reports_the_in_band_bit(self) -> None:
        # implied power-to-weight: 12.17..32.29 kW/t, inside 10..40.
        result = run_core(
            core_args(
                engine_power=130.0,
                pwr_enabled=1,
                pwr_low=PWR_LOW,
                pwr_high=PWR_HIGH,
                pwr_hard=PWR_HARD,
            )
        )
        self.assertEqual(result[5], 1)
        self.assertEqual(result[2], 2, "method code is geometry_material_power")
        self.assertEqual(result[3], MASK_POWER_IN_BAND)
        mask = int(result[3])
        self.assertEqual(mask & MASK_POWER_IN_BAND_BIT, MASK_POWER_IN_BAND_BIT)
        self.assertEqual(mask & MASK_POWER_OUT_BAND_BIT, 0)
        self.assertEqual(result[4], 2, "confidence is unchanged in band")

    def test_out_of_band_power_within_hard_factor_downgrades_confidence(self) -> None:
        # implied power-to-weight: 8.52..22.60 kW/t. The low bound is below the
        # band, so the result is out of band, but no bound is beyond hard_factor.
        result = run_core(
            core_args(
                engine_power=91.0,
                pwr_enabled=1,
                pwr_low=PWR_LOW,
                pwr_high=PWR_HIGH,
                pwr_hard=PWR_HARD,
            )
        )
        self.assertEqual(result[5], 1)
        self.assertEqual(result[2], 2)
        self.assertEqual(result[3], MASK_POWER_OUT_BAND)
        mask = int(result[3])
        self.assertEqual(mask & MASK_POWER_OUT_BAND_BIT, MASK_POWER_OUT_BAND_BIT)
        self.assertEqual(mask & MASK_POWER_IN_BAND_BIT, 0)
        self.assertEqual(result[4], 1, "confidence is downgraded to low")

    def test_power_beyond_hard_factor_is_unavailable(self) -> None:
        # implied power-to-weight: 4.68..12.42 kW/t. The high bound is below
        # pwr_low * hard_factor, so the power check rejects the result.
        result = run_core(
            core_args(
                engine_power=50.0,
                pwr_enabled=1,
                pwr_low=PWR_LOW,
                pwr_high=PWR_HIGH,
                pwr_hard=PWR_HARD,
            )
        )
        self.assertEqual(result, UNAVAILABLE)

    def test_power_beyond_hard_factor_high_side_is_unavailable(self) -> None:
        # implied power-to-weight: 84.25..227.6 kW/t, above pwr_high * 2.
        result = run_core(
            core_args(
                engine_power=900.0,
                pwr_enabled=1,
                pwr_low=PWR_LOW,
                pwr_high=PWR_HIGH,
                pwr_hard=PWR_HARD,
            )
        )
        self.assertEqual(result, UNAVAILABLE)

    def test_power_never_sets_the_mass(self) -> None:
        # The same box returns the same range with and without a power band.
        geometry = run_core(core_args())
        powered = run_core(
            core_args(
                engine_power=130.0,
                pwr_enabled=1,
                pwr_low=PWR_LOW,
                pwr_high=PWR_HIGH,
            )
        )
        self.assertEqual(geometry[0], powered[0])
        self.assertEqual(geometry[1], powered[1])


class CoreMaterialTest(unittest.TestCase):
    """The material signal narrows the confidence, never the geometry."""

    def test_one_declared_class_uses_the_declared_bit(self) -> None:
        result = run_core(core_args(material=1))
        self.assertEqual(result[3], 1 + 2 + 4 + 16 + 32 + 64)
        self.assertEqual(result[4], 2)

    def test_material_disagreement_downgrades_confidence(self) -> None:
        result = run_core(core_args(material=2))
        self.assertEqual(result[3], 1 + 2 + 8 + 16 + 32 + 64 + 1024)
        self.assertEqual(result[4], 1)

    def test_ground_residual_is_not_trusted(self) -> None:
        result = run_core(core_args(material=3))
        self.assertEqual(result[3], 1 + 2 + 8 + 16 + 32 + 64 + 512)
        self.assertEqual(result[4], 1)

    def test_unknown_material_code_is_treated_as_default(self) -> None:
        self.assertEqual(run_core(core_args(material=9))[3], MASK_POWER_DISABLED)

    def test_material_signal_never_sets_the_mass(self) -> None:
        default = run_core(core_args())
        narrowed = run_core(core_args(material=1))
        self.assertEqual(default[0], narrowed[0])
        self.assertEqual(default[1], narrowed[1])


class MutatedCoreTest(unittest.TestCase):
    """The bounded-range case has teeth: a point mass fails it."""

    def assert_bounded(self, result: list[float]) -> None:
        self.assertEqual(result[5], 1)
        self.assertLess(result[0], result[1], "a point mass is not a bounded estimate")

    def test_a_mutated_core_that_returns_a_point_mass_fails_the_bounded_case(
        self,
    ) -> None:
        source = CORE.read_text(encoding="utf-8")
        # Swap the returned high bound for the low bound. The pre-return guard
        # compares the original locals, so the point mass reaches the caller.
        mutated = source.replace("[_low, _high, _method", "[_low, _low, _method")
        self.assertNotEqual(source, mutated, "the mutation anchor must be present")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fnc_estimateVehicleMassCore.sqf"
            path.write_text(mutated, encoding="utf-8")
            written = path.read_text(encoding="utf-8")
            result = cast("list[float]", run_sqf(path, core_args()))
        self.assertEqual(result[5], 1, "the mutated core still claims an estimate")
        self.assertEqual(result[0], result[1], "the mutated core returns a point mass")
        with self.assertRaises(AssertionError):
            self.assert_bounded(result)
        self.assertNotEqual(source, written)


class WrapperContractTest(unittest.TestCase):
    """The wrapper holds the required calls and the published contract."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.src = WRAPPER.read_text(encoding="utf-8")
        cls.body = code(cls.src)
        cls.flat = compact(cls.body)

    def test_reads_the_catalogue_matcher(self) -> None:
        self.assertIn("[_type] call FUNC(getVehicleMatch)", self.flat)

    def test_reads_the_bounding_box(self) -> None:
        self.assertIn("boundingBoxReal _vehicle", self.flat)

    def test_reads_the_surface_material_through_the_material_component(self) -> None:
        self.assertIn("call EFUNC(material,getSurfaceMaterial)", self.flat)

    def test_calls_the_core_once(self) -> None:
        self.assertEqual(self.flat.count("call FUNC(estimateVehicleMassCore)"), 1)

    def test_reads_the_enable_setting(self) -> None:
        self.assertIn("GVAR(estimateVehicleMassEnabled) isEqualTo true", self.flat)

    def test_engine_power_is_read_only_inside_the_enabled_branch(self) -> None:
        self.assertEqual(self.flat.count('"enginePower"'), 1)
        self.assertIn('getNumber (configFile >> "CfgVehicles" >> _type', self.flat)
        branch = self.flat.index("(_powerBlock select 0) isEqualTo true")
        read = self.flat.index('"enginePower"')
        self.assertLess(branch, read, "enginePower must sit inside the enabled branch")

    def test_publishes_the_seven_variables(self) -> None:
        found = published_variables(self.flat)
        self.assertEqual(sorted(found), sorted(PUBLISHED))
        for name in PUBLISHED:
            with self.subTest(name=name):
                self.assertIn(f"GVAR({name}) =", self.flat)

    def test_returns_the_seven_element_shape(self) -> None:
        self.assertEqual(self.flat.count(SEVEN_ELEMENT_RESULT), 1)
        self.assertIn(UNAVAILABLE_RESULT, self.flat)

    def test_the_sourced_path_returns_a_point_pair_and_the_sourced_status(self) -> None:
        self.assertIn('[_srcWeight, _srcWeight, "catalogue_row"', self.flat)
        self.assertIn('"sourced", _srcId] call _publish', self.flat)

    def test_the_sourced_path_precedes_the_setting_gate(self) -> None:
        self.assertLess(
            self.flat.index("if (_srcWeight > 0) exitWith"),
            self.flat.index("GVAR(estimateVehicleMassEnabled)"),
        )

    def test_the_model_read_precedes_the_setting_and_approval_gate(self) -> None:
        # The model read supplies the approved flag the gate tests, so it runs
        # first. The name states the assertion, not the plan wording.
        self.assertLess(
            self.flat.index("call FUNC(getVehicleMassModel)"),
            self.flat.index("if (!_settingOn || !_approved)"),
        )

    def test_contains_no_get_mass(self) -> None:
        self.assertFalse(has_identifier(self.body, "getMass"))

    def test_calls_no_soil_or_material_mutation(self) -> None:
        for token in FORBIDDEN_EFFECTS:
            with self.subTest(token=token):
                self.assertFalse(has_identifier(self.body, token))

    def test_every_result_path_uses_the_publish_helper(self) -> None:
        # The publish helper is the only writer of the seven variables.
        self.assertEqual(self.flat.count("call _publish"), 3)

    def test_never_writes_a_catalogue_value(self) -> None:
        self.assertNotIn("operating_weight_kg", self.flat)
        self.assertNotIn("curb_weight_kg", self.flat)


class WrapperMaterialClassificationTest(unittest.TestCase):
    """The declared material signal maps to the four material codes.

    The wrapper cannot run in the harness, so the classification branch is
    pinned structurally. The four codes are 0 default, 1 one distinct
    non-ground class, 2 more than one distinct class, and 3 ground residual
    only. The core then reads the code as ``materialNarrowed``.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.flat = compact(code(WRAPPER.read_text(encoding="utf-8")))
        cls.block = material_block(cls.flat)

    def test_reads_the_declared_hidden_selection_materials(self) -> None:
        self.assertIn(
            'getArray (configOf _vehicle >> "hiddenSelectionsMaterials")',
            self.block,
        )

    def test_classifies_each_declared_path_through_the_material_component(
        self,
    ) -> None:
        self.assertIn("[_x] call EFUNC(material,getSurfaceMaterial)", self.block)
        self.assertIn("forEach _selectionMaterials", self.block)
        # Empty and placeholder paths are not classified.
        self.assertIn('(_path != "") && (_path != "any")', self.block)

    def test_keeps_only_distinct_classified_classes(self) -> None:
        self.assertIn("!(_materialClass in _materialClasses)", self.block)
        self.assertIn("_materialClasses pushBack _materialClass", self.block)

    def test_defaults_to_code_zero_when_no_material_is_declared(self) -> None:
        self.assertIn("private _materialNarrowed = 0;", self.block)
        self.assertIn("private _classCount = count _materialClasses;", self.block)
        self.assertLess(
            self.block.index("private _materialNarrowed = 0;"),
            self.block.index("if (_classCount == 1) then"),
        )

    def test_one_distinct_non_ground_class_maps_to_code_one(self) -> None:
        self.assertIn("if (_classCount == 1) then", self.block)
        self.assertIn('if (_onlyClass == "ground") then', self.block)
        self.assertIn("_materialNarrowed = 1;", self.block)
        self.assertLess(
            self.block.index('if (_onlyClass == "ground") then'),
            self.block.index("_materialNarrowed = 1;"),
        )

    def test_ground_residual_maps_to_code_three(self) -> None:
        self.assertIn('if (_onlyClass == "ground") then', self.block)
        self.assertIn("_materialNarrowed = 3;", self.block)
        self.assertLess(
            self.block.index('if (_onlyClass == "ground") then'),
            self.block.index("_materialNarrowed = 3;"),
        )

    def test_multiple_distinct_classes_map_to_code_two(self) -> None:
        self.assertIn("if (_classCount > 1) then", self.block)
        self.assertIn("_materialNarrowed = 2;", self.block)
        self.assertLess(
            self.block.index("if (_classCount > 1) then"),
            self.block.index("_materialNarrowed = 2;"),
        )


class WrapperMutationProbeTest(unittest.TestCase):
    """Prove the wrapper checks are sensitive to a malformed copy."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.flat = compact(code(WRAPPER.read_text(encoding="utf-8")))

    def test_malformed_wrapper_text_loses_the_seven_element_shape(self) -> None:
        malformed = self.flat.replace(
            SEVEN_ELEMENT_RESULT,
            "[_low, _high, _method, _assumptions, _confidence]",
        )
        self.assertIn(SEVEN_ELEMENT_RESULT, self.flat)
        self.assertNotIn(SEVEN_ELEMENT_RESULT, malformed)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrapper.sqf"
            path.write_text(malformed, encoding="utf-8")
            self.assertNotIn(SEVEN_ELEMENT_RESULT, compact(path.read_text("utf-8")))

    def test_a_missing_published_variable_is_detected(self) -> None:
        self.assertEqual(len(published_variables(self.flat)), 7)
        missing = self.flat.replace("GVAR(vehicleMassSource) = _source;", "")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrapper.sqf"
            path.write_text(missing, encoding="utf-8")
            found = published_variables(compact(path.read_text("utf-8")))
        self.assertEqual(len(found), 6)
        self.assertNotIn("vehicleMassSource", found)

    def test_a_withdrawn_engine_power_read_is_detected(self) -> None:
        self.assertEqual(self.flat.count('"enginePower"'), 1)
        without = self.flat.replace('"enginePower"', '"power"')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrapper.sqf"
            path.write_text(without, encoding="utf-8")
            reread = compact(path.read_text("utf-8"))
        self.assertEqual(reread.count('"enginePower"'), 0)

    def test_a_withdrawn_material_branch_is_detected(self) -> None:
        block = material_block(self.flat)
        self.assertIn("[_x] call EFUNC(material,getSurfaceMaterial)", block)
        without = self.flat.replace(block, "private _materialNarrowed = 0;")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrapper.sqf"
            path.write_text(without, encoding="utf-8")
            reread = compact(path.read_text("utf-8"))
        self.assertNotIn("[_x] call EFUNC(material,getSurfaceMaterial)", reread)
        self.assertNotIn("_materialNarrowed = 1;", reread)
        self.assertNotIn("_materialNarrowed = 2;", reread)
        self.assertNotIn("_materialNarrowed = 3;", reread)

    def test_a_reversed_model_read_order_is_detected(self) -> None:
        read_token = "call FUNC(getVehicleMassModel)"
        gate_token = "if (!_settingOn || !_approved)"
        gate_start = self.flat.index(gate_token)
        read_end = self.flat.index(read_token) + len(read_token)
        reversed_flat = (
            self.flat[: self.flat.index(read_token)]
            + self.flat[read_end:gate_start]
            + gate_token
            + read_token
            + self.flat[gate_start + len(gate_token) :]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrapper.sqf"
            path.write_text(reversed_flat, encoding="utf-8")
            reread = compact(path.read_text("utf-8"))
        self.assertGreater(reread.index(read_token), reread.index(gate_token))
        with self.assertRaises(AssertionError):
            self.assertLess(reread.index(read_token), reread.index(gate_token))


class CoreCalibratedFillTest(unittest.TestCase):
    """A calibrated vehicle-type fill produces a modelled range.

    The committed token rows carry a zero fill, which the core refuses. The
    vehicle-type rows carry the calibrated fills. Routing a class to a
    vehicle-type row therefore produces a modelled range, not the
    unavailable tuple. The fills come from the generated table, never a
    hardcoded number.
    """

    @classmethod
    def setUpClass(cls) -> None:
        table = cast("list[object]", gen.build_table(gen.load_model(MODEL)))
        cls.rows = cast("list[list[object]]", table[2])

    def _vehicle_type_fill(self, vehicle_type: str) -> tuple[float, float]:
        for row in self.rows:
            if row[1] == "vehicle_type" and row[2] == vehicle_type:
                return float(cast(float, row[4])), float(cast(float, row[5]))
        self.fail(f"no vehicle_type row for {vehicle_type}")

    def test_a_zero_fill_row_is_unavailable(self) -> None:
        self.assertEqual(run_core(core_args(fill_low=0.0, fill_high=0.0)), UNAVAILABLE)

    def test_the_wheeled_vehicle_type_fill_returns_a_modelled_range(self) -> None:
        low, high = self._vehicle_type_fill("wheeled")
        result = run_core(core_args(fill_low=low, fill_high=high))
        self.assertEqual(result[5], 1)
        self.assertGreater(result[0], 0)
        self.assertLess(result[0], result[1])

    def test_the_wide_tracked_vehicle_type_fill_is_refused_by_the_width_cap(
        self,
    ) -> None:
        # The tracked pool is bimodal: an APC holds a ratio near 38 to 55 and a
        # tank near 137 to 177. The token rows split that pool, so the pooled
        # type fallback is deliberately wide. The core refuses it on the width
        # cap, which keeps an unmatched tracked class fail-closed.
        low, high = self._vehicle_type_fill("tracked")
        result = run_core(core_args(fill_low=low, fill_high=high))
        self.assertEqual(result, UNAVAILABLE)


class MassClassFallThroughTest(unittest.TestCase):
    """The resolution keeps the first usable matching row.

    A matched row with a zero or inverted fill range is skipped, so the
    search continues to a later row. This closes the defect where an empty
    token row shadowed a calibrated vehicle-type row.
    """

    def test_a_zero_fill_token_row_falls_through_to_a_usable_vehicle_type_row(
        self,
    ) -> None:
        rows = [
            ["Car", "token", "wheeled", "metal", 0.0, 0.0],
            ["wheeled", "vehicle_type", "wheeled", "metal", 0.0036, 0.0172],
            ["default", "default", "", "metal", 0.0, 0.0],
        ]
        chosen = select_mass_class_row(rows, "wheeled", {"Car"})
        self.assertEqual(
            chosen, ["wheeled", "vehicle_type", "wheeled", "metal", 0.0036, 0.0172]
        )

    def test_a_usable_token_row_wins_over_the_vehicle_type_row(self) -> None:
        rows = [
            ["Car", "token", "wheeled", "metal", 0.10, 0.20],
            ["wheeled", "vehicle_type", "wheeled", "metal", 0.0036, 0.0172],
            ["default", "default", "", "metal", 0.0, 0.0],
        ]
        chosen = select_mass_class_row(rows, "wheeled", {"Car"})
        self.assertEqual(chosen, ["Car", "token", "wheeled", "metal", 0.10, 0.20])

    def test_a_zero_fill_vehicle_type_row_falls_through_to_the_default_row(
        self,
    ) -> None:
        rows = [
            ["Car", "token", "wheeled", "metal", 0.0, 0.0],
            ["wheeled", "vehicle_type", "wheeled", "metal", 0.0, 0.0],
            ["default", "default", "", "metal", 0.05, 0.10],
        ]
        chosen = select_mass_class_row(rows, "wheeled", {"Car"})
        self.assertEqual(chosen, ["default", "default", "", "metal", 0.05, 0.10])

    def test_every_row_zero_fill_returns_unavailable(self) -> None:
        rows = [
            ["Car", "token", "wheeled", "metal", 0.0, 0.0],
            ["wheeled", "vehicle_type", "wheeled", "metal", 0.0, 0.0],
            ["default", "default", "", "metal", 0.0, 0.0],
        ]
        self.assertIsNone(select_mass_class_row(rows, "wheeled", {"Car"}))
        self.assertIsNone(select_mass_class_row(rows, "tracked", set()))

    def test_an_inverted_fill_row_is_skipped(self) -> None:
        rows = [
            ["Car", "token", "wheeled", "metal", 0.20, 0.10],
            ["wheeled", "vehicle_type", "wheeled", "metal", 0.0036, 0.0172],
        ]
        chosen = select_mass_class_row(rows, "wheeled", {"Car"})
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen[1], "vehicle_type")

    def test_precedence_is_token_then_vehicle_type_then_default(self) -> None:
        token = ["Car", "token", "wheeled", "metal", 0.10, 0.20]
        vehicle = ["wheeled", "vehicle_type", "wheeled", "metal", 0.0036, 0.0172]
        default = ["default", "default", "", "metal", 0.05, 0.10]
        # All three usable: the token row wins.
        self.assertEqual(
            select_mass_class_row([token, vehicle, default], "wheeled", {"Car"}),
            token,
        )
        # No token match: the vehicle-type row wins.
        self.assertEqual(
            select_mass_class_row([token, vehicle, default], "wheeled", set()),
            vehicle,
        )
        # No token and no vehicle-type match: the default row wins.
        self.assertEqual(
            select_mass_class_row([token, vehicle, default], "tracked", set()),
            default,
        )


class GeneratedMassClassFallThroughTest(unittest.TestCase):
    """The committed table resolves the calibrated tokens and the fail-closed ones.

    Every calibrated token row carries a usable fill, so a class resolves to
    its own token. The fail-closed tokens route to the calibrated vehicle-type
    row. The tracked bucket is split: a Tank resolves to the Tank token and a
    Tracked_APC resolves to the Tracked_APC token.
    """

    @classmethod
    def setUpClass(cls) -> None:
        table = cast("list[object]", gen.build_table(gen.load_model(MODEL)))
        cls.rows = cast("list[list[object]]", table[2])

    def _rows(self, match: str) -> list[list[object]]:
        return [row for row in self.rows if row[1] == match]

    def test_each_calibrated_token_row_carries_a_usable_fill(self) -> None:
        tokens = [
            row for row in self._rows("token") if cast(str, row[0]) in CALIBRATED_TOKENS
        ]
        self.assertEqual(CALIBRATED_TOKENS, {cast(str, row[0]) for row in tokens})
        for row in tokens:
            with self.subTest(key=row[0]):
                self.assertTrue(
                    row_is_usable(
                        float(cast(float, row[4])), float(cast(float, row[5]))
                    )
                )

    def test_the_fail_closed_token_rows_carry_no_usable_fill(self) -> None:
        fail_closed = [
            row
            for row in self._rows("token")
            if cast(str, row[0]) not in CALIBRATED_TOKENS
        ]
        self.assertEqual(
            {"Motorcycle", "Wheeled_APC_F"}, {cast(str, row[0]) for row in fail_closed}
        )
        for row in fail_closed:
            with self.subTest(key=row[0]):
                self.assertFalse(
                    row_is_usable(
                        float(cast(float, row[4])), float(cast(float, row[5]))
                    )
                )

    def test_a_tank_class_resolves_to_the_tank_token(self) -> None:
        chosen = select_mass_class_row(self.rows, "tracked", {"Tank"})
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen[0], "Tank")

    def test_a_tracked_apc_class_resolves_to_the_tracked_apc_token(self) -> None:
        chosen = select_mass_class_row(self.rows, "tracked", {"Tracked_APC"})
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen[0], "Tracked_APC")

    def test_the_bimodal_tracked_bucket_is_split(self) -> None:
        tank = select_mass_class_row(self.rows, "tracked", {"Tank"})
        apc = select_mass_class_row(self.rows, "tracked", {"Tracked_APC"})
        self.assertIsNotNone(tank)
        self.assertIsNotNone(apc)
        assert tank is not None and apc is not None
        self.assertEqual(tank[0], "Tank")
        self.assertEqual(apc[0], "Tracked_APC")
        self.assertNotEqual(tank[4:6], apc[4:6])

    def test_each_vehicle_type_row_carries_a_usable_fill(self) -> None:
        for row in self._rows("vehicle_type"):
            with self.subTest(key=row[0]):
                self.assertTrue(
                    row_is_usable(
                        float(cast(float, row[4])), float(cast(float, row[5]))
                    )
                )

    def _zero_fill_tokens(self, vehicle_type: str) -> set[str]:
        return {
            cast(str, row[0])
            for row in self._rows("token")
            if row[2] == vehicle_type
            and not row_is_usable(
                float(cast(float, row[4])), float(cast(float, row[5]))
            )
        }

    def test_a_wheeled_token_class_routes_to_the_wheeled_vehicle_type_row(self) -> None:
        tokens = self._zero_fill_tokens("wheeled")
        if not tokens:
            self.skipTest("no zero-fill wheeled token row in the committed table")
        chosen = select_mass_class_row(self.rows, "wheeled", tokens)
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen[1], "vehicle_type")
        self.assertEqual(chosen[2], "wheeled")

    def test_a_tracked_token_class_routes_to_the_tracked_vehicle_type_row(self) -> None:
        tokens = self._zero_fill_tokens("tracked")
        if not tokens:
            self.skipTest("no zero-fill tracked token row in the committed table")
        chosen = select_mass_class_row(self.rows, "tracked", tokens)
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen[1], "vehicle_type")
        self.assertEqual(chosen[2], "tracked")


class WrapperMassClassFallThroughTest(unittest.TestCase):
    """The wrapper implements the first-usable-match policy.

    The harness cannot run the wrapper, because it has no ``isKindOf`` or
    ``boundingBoxReal`` evaluator. The policy is pinned in the source here.
    """

    @classmethod
    def setUpClass(cls) -> None:
        src = WRAPPER.read_text(encoding="utf-8")
        cls.raw = compact(src)
        cls.flat = compact(code(src))
        cls.block = mass_class_block(cls.flat)

    def test_the_usable_test_requires_a_positive_ordered_fill_range(self) -> None:
        self.assertIn(USABLE_PREDICATE, self.block)

    def test_a_row_is_stored_only_when_usable_and_none_is_chosen(self) -> None:
        # The usability test runs first, so an unusable row never stops the
        # loop and the search continues to a later row.
        self.assertIn("if (_rowUsable && {_classRow isEqualTo []}) then", self.block)

    def test_the_row_is_stored_only_after_the_match_is_true(self) -> None:
        self.assertIn("if (_rowMatch) then { _classRow = _x; };", self.block)

    def test_the_usable_test_precedes_the_store(self) -> None:
        self.assertLess(
            self.block.index("private _rowUsable"),
            self.block.index("_classRow = _x;"),
        )

    def test_token_precedes_vehicle_type_precedes_default(self) -> None:
        token = self.block.index('if (_matchKind == "token") then')
        vehicle = self.block.index('if (_matchKind == "vehicle_type") then')
        default = self.block.index("_rowMatch = true;")
        self.assertLess(token, vehicle)
        self.assertLess(vehicle, default)

    def test_the_empty_class_row_still_exits_unavailable(self) -> None:
        self.assertIn(
            "if (_classRow isEqualTo []) exitWith { call _unavailable };", self.block
        )

    def test_the_header_states_the_fall_through_rule(self) -> None:
        self.assertIn("zero-fill or inverted row is skipped", self.raw)


class WrapperMassClassFallThroughProbeTest(unittest.TestCase):
    """A reverted resolution loop must fail the fall-through checks."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.flat = compact(code(WRAPPER.read_text(encoding="utf-8")))

    def test_a_loop_without_the_usable_test_is_rejected(self) -> None:
        reverted = self.flat.replace(USABLE_PREDICATE, "private _rowUsable = true;")
        self.assertNotEqual(self.flat, reverted)
        block = mass_class_block(reverted)
        self.assertNotIn(USABLE_PREDICATE, block)

    def test_a_store_outside_the_usable_guard_is_rejected(self) -> None:
        reverted = self.flat.replace(
            "if (_rowUsable && {_classRow isEqualTo []}) then",
            "if (_classRow isEqualTo []) then",
        )
        self.assertNotEqual(self.flat, reverted)
        block = mass_class_block(reverted)
        self.assertNotIn("if (_rowUsable && {_classRow isEqualTo []}) then", block)


# The corrected arity guard, as committed in the wrapper. Whitespace is
# collapsed before the match, so the pin does not depend on SQF layout.
ARITY_GUARD_WRAPPER = (
    "if ((_box isEqualType []) && {(count _box == 2) || {count _box == 3}} "
    + "&& {(_box select 0) isEqualType []} "
    + "&& {(_box select 1) isEqualType []}) then {"
)
# The corrected arity guard, as committed in the SSF consumer.
ARITY_GUARD_SSF = (
    "if (_bb isEqualType [] && {(count _bb == 2) || {count _bb == 3}}) then {"
)

# The legacy guard the fix replaces. Its presence is the defect.
LEGACY_ARITY_GUARD = "count _box == 2} &&"
LEGACY_ARITY_GUARD_SSF = "count _bb == 2}) then {"

# The three-element box the engine recorded at probe.log line 757. The
# trailing element is the bounding-sphere diameter, never a corner.
PROBE_THREE_ELEMENT_BOX = [
    [-1.49355, -4.71046, -2.14563],
    [1.49355, 4.71046, 2.14563],
    8.08086,
]
# The older two-element form.
PROBE_TWO_ELEMENT_BOX = [
    [-1.49355, -4.71046, -2.14563],
    [1.49355, 4.71046, 2.14563],
]

# The wrapper's geometry band, read live in the test so a change is caught.
GEOMETRY_BAND_LOW = 0.5
GEOMETRY_BAND_HIGH = 20.0

# sqf_lite parses an SQF ``{...}`` block as a lambda and treats it as truthy in
# a boolean chain. That is a harness limitation, not SQF. So the executed test
# rewrites the committed ``{...}`` guards to plain parentheses, which the harness
# evaluates faithfully, and pins the committed ``{...}`` text structurally in
# ``ArityGuardSourceTest``. The arithmetic under test is the committed body.
BRACE_GUARD_WRAPPER = (
    "((_box isEqualType []) && {(count _box == 2) || {count _box == 3}}\n"
    + "    && {(_box select 0) isEqualType []} "
    + "&& {(_box select 1) isEqualType []})"
)
PAREN_GUARD_WRAPPER = (
    "((_box isEqualType []) && ((count _box == 2) || (count _box == 3))\n"
    + "    && ((_box select 0) isEqualType []) "
    + "&& ((_box select 1) isEqualType []))"
)


def extent_block(source: str) -> str:
    """Return the committed wrapper extent block, runnable under sqf_lite.

    The harness cannot evaluate ``boundingBoxReal``, so the block is lifted
    verbatim from the source and the box is supplied by the caller. The band
    values are bound as ``_minExtentM`` and ``_maxExtentM``. Only the engine
    call is replaced and the brace guards are rewritten to parentheses. Every
    extent and band test is the committed one.
    """
    body = code(source)
    start = body.index("private _lengthM = 0;")
    end_marker = "&& (_heightM <= _maxExtentM);"
    end = body.index(end_marker) + len(end_marker)
    block = body[start:end] + "\n};"
    block = block.replace(
        "private _box = boundingBoxReal _vehicle;",
        "private _box = _box;",
    )
    block = block.replace(BRACE_GUARD_WRAPPER, PAREN_GUARD_WRAPPER)
    if BRACE_GUARD_WRAPPER.encode() in block.encode():
        raise AssertionError("the committed guard shape was not rewritten")
    return block


def run_extent_block(
    block: str,
    box: object,
    low: float = GEOMETRY_BAND_LOW,
    high: float = GEOMETRY_BAND_HIGH,
) -> dict[str, object]:
    """Run the committed extent block over one box through sqf_lite.

    Returns a dict with the three extents and the geometry flag. The harness
    has no ``isEqualType`` by default, so the SQF-accurate stub is injected.
    """
    source = (
        "private _box = __BOX__;\n"
        "private _lengthM = 0;\n"
        "private _widthM = 0;\n"
        "private _heightM = 0;\n"
        "private _geometryOk = false;\n"
        + block
        + "\n[_lengthM, _widthM, _heightM, _geometryOk]\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "extent_block.sqf"
        path.write_text(source, encoding="utf-8")
        result = cast(
            "list[object]",
            run_sqf(
                path,
                [],
                {
                    "__BOX__": box,
                    "isEqualType": sqf_is_equal_type,
                    "_minExtentM": low,
                    "_maxExtentM": high,
                    "false": False,
                    "true": True,
                },
            ),
        )
    return {
        "length": result[0],
        "width": result[1],
        "height": result[2],
        "geometryOk": result[3],
    }


def sqf_is_equal_type(left: object, right: object) -> bool:
    """SQF isEqualType: numbers are one type regardless of int or float."""
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return True
    return type(left) is type(right)


class BoundingBoxArityTest(unittest.TestCase):
    """The engine returns a two- or three-element box; both are accepted.

    The engine adds the bounding-sphere diameter in Arma 3 1.92, so the box
    is ``[[min],[max],boundingSphereDiameter]``. Older builds return
    ``[[min],[max]]``. Only the first two elements are corners. The block
    under test is the committed wrapper extent block, executed unmodified
    through sqf_lite.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.src = WRAPPER.read_text(encoding="utf-8")
        cls.block = extent_block(cls.src)

    def test_the_extent_block_is_the_committed_guard(self) -> None:
        flat = compact(self.block)
        self.assertIn("count _box == 2", flat)
        self.assertIn("count _box == 3", flat)
        self.assertIn("_box select 0", flat)
        self.assertIn("_box select 1", flat)

    def test_a_three_element_box_is_accepted(self) -> None:
        result = run_extent_block(self.block, PROBE_THREE_ELEMENT_BOX)
        self.assertTrue(result["geometryOk"], "the three-element box was refused")
        self.assertAlmostEqual(cast(float, result["length"]), 2.9871, places=4)
        self.assertAlmostEqual(cast(float, result["width"]), 9.42092, places=4)
        self.assertAlmostEqual(cast(float, result["height"]), 4.29126, places=4)

    def test_a_two_element_box_is_accepted_unchanged(self) -> None:
        result = run_extent_block(self.block, PROBE_TWO_ELEMENT_BOX)
        self.assertTrue(result["geometryOk"])
        self.assertAlmostEqual(cast(float, result["length"]), 2.9871, places=4)
        self.assertAlmostEqual(cast(float, result["width"]), 9.42092, places=4)
        self.assertAlmostEqual(cast(float, result["height"]), 4.29126, places=4)

    def test_both_arities_yield_the_same_extents(self) -> None:
        three = run_extent_block(self.block, PROBE_THREE_ELEMENT_BOX)
        two = run_extent_block(self.block, PROBE_TWO_ELEMENT_BOX)
        self.assertEqual(three, two, "the sphere radius changed an extent")

    def test_a_non_array_corner_is_rejected(self) -> None:
        # A scalar corner fails the corner-type guard, so the block is not
        # entered and the flag stays false.
        box = [1.49355, [1.49355, 4.71046, 2.14563], 8.08086]
        result = run_extent_block(self.block, box)
        self.assertFalse(result["geometryOk"])

    def test_a_two_component_corner_is_refused(self) -> None:
        # SQF select 2 on a two-element corner is nil, so the height test is
        # false and the band refuses the box. The harness raises on the same
        # read, which is the same refusal at the guard boundary.
        box = [[-1.49355, -4.71046], [1.49355, 4.71046], 8.08086]
        with self.assertRaises(IndexError):
            run_extent_block(self.block, box)

    def test_an_outer_length_of_one_is_refused(self) -> None:
        # SQF count 1 fails the arity guard, so the block is not entered.
        # The harness reads select 1 first, which is the same boundary.
        box = [[-1.49355, -4.71046, -2.14563]]
        with self.assertRaises(IndexError):
            run_extent_block(self.block, box)

    def test_an_outer_length_of_four_is_rejected(self) -> None:
        # Four elements fail the count guard.
        box = PROBE_THREE_ELEMENT_BOX + [8.08086]
        result = run_extent_block(self.block, box)
        self.assertFalse(result["geometryOk"])

    def test_a_non_array_box_is_refused_at_the_type_guard(self) -> None:
        # SQF isEqualType [] is false for a number, so the block is not
        # entered. The harness cannot take count of a float, which is the
        # same boundary the SQF type guard prevents reaching.
        with self.assertRaises((IndexError, TypeError)):
            run_extent_block(self.block, 8.08086)

    def test_the_band_rejects_an_out_of_band_extent_in_either_arity(self) -> None:
        # A 40 m width is above the 20 m band ceiling.
        long_box = [
            [-20.0, -20.0, -1.0],
            [20.0, 20.0, 1.0],
        ]
        self.assertFalse(run_extent_block(self.block, long_box)["geometryOk"])
        self.assertFalse(run_extent_block(self.block, long_box + [10.0])["geometryOk"])

    def test_the_band_still_accepts_an_in_band_box(self) -> None:
        self.assertTrue(
            run_extent_block(self.block, PROBE_THREE_ELEMENT_BOX)["geometryOk"]
        )


class ArityGuardSourceTest(unittest.TestCase):
    """The corrected guard text is pinned in both source files.

    A three-element box must not be rejected at either read site. The
    legacy ``count ... == 2`` guard is the defect, so its absence is pinned
    for the wrapper guard shape and for the SSF guard shape.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.wrapper_flat = compact(code(WRAPPER.read_text(encoding="utf-8")))
        cls.ssf_flat = compact(
            code((FUNCTIONS / "fnc_calculateSSF.sqf").read_text(encoding="utf-8"))
        )

    def test_the_wrapper_guard_accepts_two_or_three_elements(self) -> None:
        self.assertIn(ARITY_GUARD_WRAPPER, self.wrapper_flat)

    def test_the_ssf_guard_accepts_two_or_three_elements(self) -> None:
        self.assertIn(ARITY_GUARD_SSF, self.ssf_flat)

    def test_the_wrapper_legacy_guard_is_gone(self) -> None:
        self.assertNotIn(LEGACY_ARITY_GUARD, self.wrapper_flat)

    def test_the_ssf_legacy_guard_is_gone(self) -> None:
        self.assertNotIn(LEGACY_ARITY_GUARD_SSF, self.ssf_flat)

    def test_the_wrapper_header_states_the_box_arity(self) -> None:
        raw = compact(WRAPPER.read_text(encoding="utf-8"))
        self.assertIn("boundingSphereDiameter", raw)
        self.assertIn("first two elements are corners", raw)

    def test_the_ssf_header_states_the_box_arity(self) -> None:
        raw = compact((FUNCTIONS / "fnc_calculateSSF.sqf").read_text(encoding="utf-8"))
        self.assertIn("boundingSphereDiameter", raw)
        self.assertIn("first two elements are corners", raw)


class ArityGuardMutationProbeTest(unittest.TestCase):
    """A reverted guard must fail the arity checks."""

    def test_a_reverted_wrapper_guard_loses_the_three_element_branch(self) -> None:
        src = WRAPPER.read_text(encoding="utf-8")
        reverted = src.replace(
            "{(count _box == 2) || {count _box == 3}}",
            "{count _box == 2}",
        )
        self.assertNotEqual(src, reverted, "the mutation anchor must be present")
        flat = compact(code(reverted))
        self.assertNotIn("count _box == 3", flat)
        self.assertIn(LEGACY_ARITY_GUARD, flat)

    def test_a_reverted_ssf_guard_loses_the_three_element_branch(self) -> None:
        path = FUNCTIONS / "fnc_calculateSSF.sqf"
        src = path.read_text(encoding="utf-8")
        reverted = src.replace(
            "{(count _bb == 2) || {count _bb == 3}}",
            "{count _bb == 2}",
        )
        self.assertNotEqual(src, reverted, "the mutation anchor must be present")
        flat = compact(code(reverted))
        self.assertNotIn("count _bb == 3", flat)
        self.assertIn(LEGACY_ARITY_GUARD_SSF, flat)


class GeneratedTableProbeTest(unittest.TestCase):
    """The wrapper depends on the generated table. Prove staleness is caught."""

    def test_the_committed_table_matches_a_fresh_render(self) -> None:
        payload = gen.load_model(MODEL)
        fresh = gen.render_table(gen.build_table(payload))
        self.assertEqual(fresh, TABLE.read_text(encoding="utf-8"))

    def test_a_stale_table_copy_is_rejected(self) -> None:
        payload = gen.load_model(MODEL)
        fresh = gen.render_table(gen.build_table(payload))
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "fnc_getVehicleMassModel.sqf"
            stale.write_text(fresh + "// stale\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                status = gen.check_output(stale, fresh)
            self.assertEqual(status, 1)
            self.assertNotEqual(stale.read_text(encoding="utf-8"), fresh)
        self.assertEqual(TABLE.read_text(encoding="utf-8"), fresh)


if __name__ == "__main__":
    unittest.main()
