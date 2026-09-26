#!/usr/bin/env python3
"""Vehicle mass model contract tests (vehicle mass estimate layer, task 10).

The model artefact ``data/vehicle/mass_model.json`` is a model, not a
catalogue capture. The calibration gate
``tools/validation/validate_vehicle_mass_model.py`` proves it against the
held catalogue weights. The generator
``tools/validation/gen_vehicle_mass_model.py`` renders it into the runtime
parameter table. This module owns the contract between those three:

  * the model schema, the eight classifier density classes and the citations;
  * the disabled power block and the approved calibration state;
  * the metric functions on a known fixture;
  * the generator freshness and its rejection of a malformed model;
  * the separation from the catalogue and from every driving consumer.

The tests read the working tree. The only writes go to a ``tempfile`` copy.
No test edits product data or runs the runtime estimate. The negative tests
set the approval flag only on an in-memory or shadow-copied model.

Run: python3 -m unittest tools.tests.test_vehicle_mass_model -v
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Callable, Iterator, cast

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_vehicle_mass_model as gen  # noqa: E402
from tools.validation import validate_vehicle_mass_model as gate  # noqa: E402
from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

DATA = REPO / "data" / "vehicle"
MODEL_PATH = DATA / "mass_model.json"
CALIBRATION_PATH = DATA / "mass_model_calibration.json"
GENERATED = REPO / "addons" / "mobility" / "functions" / "fnc_getVehicleMassModel.sqf"
VALIDATOR = REPO / "tools" / "validation" / "validate_vehicle_mass_model.py"
GENERATOR = REPO / "tools" / "validation" / "gen_vehicle_mass_model.py"

JsonObject = dict[str, object]
Mutator = Callable[[JsonObject], None]

# The eight classifier classes, exactly those in fnc_getSurfaceMaterial.sqf.
DENSITY_CLASSES = (
    "metal",
    "rock",
    "wood",
    "concrete",
    "glass",
    "water",
    "vegetation",
    "ground",
)
# The mass classes, most specific first, default last.
MASS_CLASS_KEYS = (
    "Motorcycle",
    "Car",
    "Truck",
    "MRAP",
    "Wheeled_APC",
    "Wheeled_APC_F",
    "Tank",
    "Tracked_APC",
    "wheeled",
    "tracked",
    "default",
)
# The committed census refit, margin 0.15. Every key with rows is listed here.
EXPECTED_FILLS = {
    "Car": (0.0046, 0.0068, 2),
    "Truck": (0.0036, 0.0078, 3),
    "MRAP": (0.0081, 0.0172, 3),
    "Wheeled_APC": (0.0047, 0.0106, 4),
    "Tank": (0.0149, 0.0287, 3),
    "Tracked_APC": (0.0041, 0.009, 3),
    "wheeled": (0.0036, 0.0172, 12),
    "tracked": (0.0041, 0.0287, 6),
}
# The fail-closed classes: no census row resolves to them.
ZERO_FILL_KEYS = ("Motorcycle", "Wheeled_APC_F", "default")
# A modelled value is never labelled with a sourced-corpus grade.
GRADE_TOKENS = ("documented", "claimed", "standard")
# Catalogue weight field names. The model must hold none of them.
CATALOGUE_MASS_FIELDS = (
    "operating_weight_kg",
    "curb_weight_kg",
    "gross_weight_kg",
    "estimated_mass_kg",
    "catalogue_weight_kg",
)
# The mobility functions that consume the estimate if it is wired wrongly.
DRIVING_FUNCTIONS = (
    "fnc_calculateSoilStrength.sqf",
    "fnc_calculateTraction.sqf",
    "fnc_calculateWetTraction.sqf",
    "fnc_calculateTerrainLimits.sqf",
    "fnc_calculateRouteDegradation.sqf",
    "fnc_getVehicleData.sqf",
    "fnc_getVehicleMatch.sqf",
)
# References to the parameter table are allowed only in these files.
ALLOWED_TABLE_REFERENCE = {
    "addons/mobility/functions/fnc_getVehicleMassModel.sqf",
    "addons/mobility/functions/fnc_estimateVehicleMass.sqf",
    "addons/mobility/XEH_PREP.hpp",
}


def _obj(value: object, label: str = "value") -> JsonObject:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return cast("JsonObject", value)


def _arr(value: object, label: str = "value") -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be an array")
    return value


def _num(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"expected a number, got {type(value).__name__}")
    return float(value)


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"expected an integer, got {type(value).__name__}")
    return value


def _str(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"expected a string, got {type(value).__name__}")
    return value


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> JsonObject:
    loaded: object = json.loads(_text(path))
    if not isinstance(loaded, dict):
        raise TypeError(f"{path} does not hold a JSON object")
    return cast("JsonObject", loaded)


def _base_model() -> JsonObject:
    return _json(MODEL_PATH)


def _generated_text() -> str:
    return _text(GENERATED)


def _density(model: JsonObject) -> JsonObject:
    return _obj(model["material_density"], "material_density")


def _density_entry(model: JsonObject, name: str) -> JsonObject:
    return _obj(_density(model)[name], f"material_density.{name}")


def _classes(model: JsonObject) -> list[JsonObject]:
    return [_obj(item, "mass_classes[]") for item in _arr(model["mass_classes"])]


def _class_at(model: JsonObject, index: int) -> JsonObject:
    return _classes(model)[index]


def _calibration(model: JsonObject) -> JsonObject:
    return _obj(model["calibration"], "calibration")


def _unapproved_copy() -> JsonObject:
    """Return the committed model with the approval flag reverted to false."""
    model = copy.deepcopy(_base_model())
    _calibration(model)["approved"] = False
    return model


def _approved_zero_fill_copy() -> JsonObject:
    """Return an approved model with every fill range collapsed to zero.

    The committed model is calibrated. This probe rebuilds the pre-calibration
    fill state so the approval gate must reject it.
    """
    model = copy.deepcopy(_base_model())
    _calibration(model)["approved"] = True
    for row in _classes(model):
        row["fill_low"] = 0.0
        row["fill_high"] = 0.0
        row["n"] = 0
    return model


def _geometry(model: JsonObject) -> JsonObject:
    return _obj(model["geometry_bands"], "geometry_bands")


def _power(model: JsonObject) -> JsonObject:
    return _obj(model["power_to_weight"], "power_to_weight")


def _walk_strings(value: object) -> Iterator[tuple[str, str]]:
    """Yield every dict key and string value, tagged by kind."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield ("key", str(key))
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif isinstance(value, str):
        yield ("value", value)


def _addon_text_files() -> Iterator[Path]:
    for path in (REPO / "addons").rglob("*"):
        if path.is_file() and path.suffix in {".sqf", ".hpp"}:
            yield path


def _shadow_data_dir(tmp: str, payload: JsonObject) -> Path:
    """Link the real corpus into a temp dir and write one model copy."""
    root = Path(tmp) / "vehicle"
    root.mkdir()
    for child in DATA.iterdir():
        (root / child.name).symlink_to(child.resolve())
    model_path = root / "mass_model.json"
    if model_path.is_symlink():
        model_path.unlink()
    _ = model_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return root


# The known metric fixture. The densities are arbitrary and private to this
# test. The model shape mirrors the committed artefact.
def _fixture_model() -> JsonObject:
    return {
        "schema": gate.MODEL_SCHEMA,
        "material_density": {
            "metal": {
                "low": 1000,
                "high": 2000,
                "unit": "kg/m3",
                "source": "fixture",
                "locator": "fixture",
            }
        },
        "mass_classes": [
            {
                "key": "wheeled",
                "match": "vehicle_type",
                "vehicle_type": "wheeled",
                "density_class": "metal",
                "fill_low": 0.0,
                "fill_high": 0.0,
                "n": 0,
            },
            {
                "key": "default",
                "match": "default",
                "vehicle_type": "",
                "density_class": "metal",
                "fill_low": 0.0,
                "fill_high": 0.0,
                "n": 0,
            },
        ],
        "geometry_bands": {
            "min_extent_m": 0.5,
            "max_extent_m": 20.0,
            "max_width_ratio": 6.0,
        },
        "power_to_weight": {
            "enabled": False,
            "unit": "enginePower/tonne",
            "bands": {},
        },
        "calibration": {
            "approved": False,
            "n_entries": 0,
            "mdape": None,
            "fraction_in_band": None,
            "report": "fixture",
        },
    }


def _fixture_with_fills(fill_low: float, fill_high: float) -> JsonObject:
    model = _fixture_model()
    for row in _classes(model):
        if row["key"] == "wheeled":
            row["fill_low"] = fill_low
            row["fill_high"] = fill_high
    return model


def _dim(value: float) -> JsonObject:
    return {
        "value": value,
        "unit": "mm",
        "source": "fixture",
        "locator": "fixture",
        "state": "fixture",
        "grade": "documented",
    }


def _kg(value: float) -> JsonObject:
    return {
        "value": value,
        "unit": "kg",
        "source": "fixture",
        "locator": "fixture",
        "state": "fixture",
        "grade": "documented",
    }


def _entry(
    catalogue_id: str,
    *,
    mass: float | None = None,
    gross: float | None = None,
    vehicle_type: str = "wheeled",
    length_mm: float | None = 1000.0,
    width_mm: float | None = 1000.0,
    height_mm: float | None = 1000.0,
) -> catalogue.CatalogueEntry:
    values: JsonObject = {}
    for field, value in (
        ("length_mm", length_mm),
        ("width_mm", width_mm),
        ("height_mm", height_mm),
    ):
        if value is not None:
            values[field] = _dim(value)
    if mass is not None:
        values["curb_weight_kg"] = _kg(mass)
    if gross is not None:
        values["gross_weight_kg"] = _kg(gross)
    return catalogue.CatalogueEntry(
        catalogue_id=catalogue_id,
        canonical_name="",
        maker="",
        model="",
        variant="",
        variant_id=catalogue_id,
        vehicle_type=vehicle_type,
        class_token="",
        country="",
        era="",
        aliases=(),
        keywords=(),
        runtime_ready=False,
        values=values,
        source_file="fixture",
    )


class ModelSchemaTest(unittest.TestCase):
    """The committed model satisfies the schema the plan names."""

    def test_the_model_is_a_json_object_with_the_plan_schema(self) -> None:
        self.assertEqual(gen.SCHEMA, _str(_base_model()["schema"]))

    def test_the_density_keys_are_exactly_the_eight_classifier_classes(
        self,
    ) -> None:
        density = _density(_base_model())
        self.assertEqual(set(DENSITY_CLASSES), set(density))
        self.assertEqual(len(DENSITY_CLASSES), len(density))

    def test_every_density_entry_carries_a_source_and_a_locator(self) -> None:
        model = _base_model()
        for name in DENSITY_CLASSES:
            entry = _density_entry(model, name)
            with self.subTest(class_name=name):
                self.assertTrue(_str(entry["source"]).strip())
                self.assertTrue(_str(entry["locator"]).strip())

    def test_every_density_entry_has_an_ordered_positive_range(self) -> None:
        model = _base_model()
        for name in DENSITY_CLASSES:
            entry = _density_entry(model, name)
            with self.subTest(class_name=name):
                self.assertGreater(_num(entry["low"]), 0)
                self.assertLess(_num(entry["low"]), _num(entry["high"]))
                self.assertEqual("kg/m3", _str(entry["unit"]))

    def test_the_wide_density_buckets_are_labelled(self) -> None:
        model = _base_model()
        self.assertEqual(
            "proxy", _str(_density_entry(model, "vegetation")["confidence"])
        )
        self.assertEqual(
            "residual", _str(_density_entry(model, "ground")["confidence"])
        )

    def test_the_mass_classes_are_ordered_and_named(self) -> None:
        keys = [_str(row["key"]) for row in _classes(_base_model())]
        self.assertEqual(list(MASS_CLASS_KEYS), keys)

    def test_there_is_exactly_one_default_and_it_is_last(self) -> None:
        classes = _classes(_base_model())
        matches = [_str(row["match"]) for row in classes]
        self.assertEqual(1, matches.count("default"))
        self.assertEqual("default", matches[-1])
        self.assertEqual("default", _str(classes[-1]["key"]))

    def test_every_mass_class_names_a_declared_density_class(self) -> None:
        model = _base_model()
        density = _density(model)
        for row in _classes(model):
            with self.subTest(key=_str(row["key"])):
                self.assertIn(_str(row["density_class"]), density)
                self.assertIn(_str(row["match"]), ("token", "vehicle_type", "default"))

    def test_every_fill_range_is_ordered_and_non_negative(self) -> None:
        for row in _classes(_base_model()):
            with self.subTest(key=_str(row["key"])):
                low = _num(row["fill_low"])
                high = _num(row["fill_high"])
                self.assertGreaterEqual(low, 0)
                self.assertLessEqual(low, high)
                self.assertGreaterEqual(_integer(row["n"]), 0)

    def test_the_geometry_bands_are_ordered(self) -> None:
        bands = _geometry(_base_model())
        self.assertLess(_num(bands["min_extent_m"]), _num(bands["max_extent_m"]))
        self.assertGreater(_num(bands["max_width_ratio"]), 0)

    def test_the_validator_finds_no_structural_error(self) -> None:
        self.assertEqual([], gate.model_errors(_base_model()))


class GradeTokenTest(unittest.TestCase):
    """A modelled value never carries a sourced-corpus grade token."""

    def test_the_model_text_holds_no_documented_or_claimed_token(self) -> None:
        lowered = _text(MODEL_PATH).lower()
        self.assertNotIn("documented", lowered)
        self.assertNotIn("claimed", lowered)

    def test_no_model_string_is_a_bare_grade_token(self) -> None:
        # The word "standard" appears inside a vegetation locator sentence.
        # A bare grade value would be a token on its own, which this checks.
        for kind, value in _walk_strings(_base_model()):
            with self.subTest(kind=kind, value=value):
                if kind == "key":
                    self.assertNotEqual("grade", value)
                else:
                    self.assertNotIn(value, GRADE_TOKENS)

    def test_the_generated_table_holds_no_grade_token(self) -> None:
        lowered = _generated_text().lower()
        for token in GRADE_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, lowered)


class CalibrationStateTest(unittest.TestCase):
    """The committed model is approved and the gate accepts that state."""

    def test_the_committed_model_is_approved_with_the_calibration_metrics(self) -> None:
        calibration = _calibration(_base_model())
        self.assertIs(calibration["approved"], True)
        self.assertEqual(18, _integer(calibration["n_entries"]))
        self.assertEqual(0.8889, _num(calibration["fraction_in_band"]))
        self.assertEqual(0.1869, _num(calibration["mdape"]))
        self.assertTrue(_str(calibration["report"]).strip())

    def test_the_calibrated_classes_carry_non_zero_fills(self) -> None:
        rows = {_str(row["key"]): row for row in _classes(_base_model())}
        for key, (low, high, n) in EXPECTED_FILLS.items():
            with self.subTest(key=key):
                self.assertEqual(low, _num(rows[key]["fill_low"]))
                self.assertEqual(high, _num(rows[key]["fill_high"]))
                self.assertEqual(n, _integer(rows[key]["n"]))
        for key in ZERO_FILL_KEYS:
            with self.subTest(key=key):
                self.assertEqual(0.0, _num(rows[key]["fill_low"]))
                self.assertEqual(0.0, _num(rows[key]["fill_high"]))
                self.assertEqual(0, _integer(rows[key]["n"]))

    def test_the_power_block_is_disabled_with_a_reason(self) -> None:
        power = _power(_base_model())
        self.assertIs(power["enabled"], False)
        self.assertEqual("enginePower/tonne", _str(power["unit"]))
        self.assertEqual(2.0, _num(power["hard_factor"]))
        self.assertEqual({}, _obj(power["bands"]))
        reason = _str(power["reason"])
        self.assertIn("enginePower", reason)
        self.assertIn("probe", reason)

    def test_the_generated_approval_flag_and_fills_are_calibrated(self) -> None:
        table = gen.build_table(_base_model())
        self.assertIs(table[0], True)
        classes = {_str(_arr(row)[0]): _arr(row) for row in _arr(table[2])}
        self.assertEqual(0.0036, _num(classes["wheeled"][4]))
        self.assertEqual(0.0172, _num(classes["wheeled"][5]))
        self.assertEqual(0.0041, _num(classes["tracked"][4]))
        self.assertEqual(0.0287, _num(classes["tracked"][5]))

    def test_the_generated_power_block_is_disabled(self) -> None:
        table = gen.build_table(_base_model())
        power_block = _arr(table[4], "powerBlock")
        self.assertIs(power_block[0], False)
        self.assertEqual("enginePower/tonne", _str(power_block[1]))
        self.assertEqual({}, _obj(power_block[3]))
        # The render turns the empty band map into the SQF empty array.
        self.assertIn("\n        []", _generated_text())

    def test_the_default_gate_passes_on_the_committed_model(self) -> None:
        load = gate.load_calibration(CALIBRATION_PATH)
        self.assertEqual([], load.errors)
        model = _base_model()
        metrics = gate.evaluate(model, load.entries)
        self.assertEqual([], gate.approval_failures(model, metrics))

    def test_the_default_gate_cli_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            capture_output=True,
            text=True,
            cwd=str(REPO),
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("vehicle mass model gate: PASS", result.stdout)

    def test_the_self_check_reports_no_failures(self) -> None:
        self.assertEqual([], gate.self_check())

    def test_the_self_check_cli_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--self-check"],
            capture_output=True,
            text=True,
            cwd=str(REPO),
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("self-check", result.stdout)

    def test_an_injected_approval_with_zero_fills_fails_the_gate(self) -> None:
        model = _approved_zero_fill_copy()
        load = gate.load_calibration(CALIBRATION_PATH)
        metrics = gate.evaluate(model, load.entries)
        failures = gate.approval_failures(model, metrics)
        self.assertTrue(any("fraction_in_band" in item for item in failures))
        self.assertTrue(any("mdape" in item for item in failures))

    def test_the_shadow_corpus_probes_the_approved_and_reverted_states(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _shadow_data_dir(tmp, _approved_zero_fill_copy())
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = gate.main(["--data-dir", str(root)])
            output = buffer.getvalue()
        self.assertEqual(1, code, output)
        self.assertIn("FAIL (approved True)", output)
        with tempfile.TemporaryDirectory() as tmp:
            root = _shadow_data_dir(tmp, _unapproved_copy())
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = gate.main(["--data-dir", str(root)])
            output = buffer.getvalue()
        self.assertEqual(0, code, output)
        self.assertIn("PASS (approved False)", output)


class CensusCoverageTest(unittest.TestCase):
    """The census is the gate basis and it covers every filled token."""

    def test_the_census_loads_without_an_error(self) -> None:
        load = gate.load_calibration(CALIBRATION_PATH)
        self.assertEqual([], load.errors)
        self.assertEqual(18, len(load.entries))

    def test_the_census_covers_every_filled_token_the_table_declares(self) -> None:
        model = _base_model()
        filled = {
            _str(row["key"])
            for row in _classes(model)
            if row["match"] == "token" and _num(row["fill_low"]) > 0
        }
        load = gate.load_calibration(CALIBRATION_PATH)
        covered = {entry.class_token for entry in load.entries}
        self.assertEqual(filled, covered)

    def test_the_fail_closed_tokens_carry_no_census_row(self) -> None:
        load = gate.load_calibration(CALIBRATION_PATH)
        covered = {entry.class_token for entry in load.entries}
        self.assertFalse(covered & set(ZERO_FILL_KEYS))

    def test_the_recorded_metrics_are_the_census_leave_one_out(self) -> None:
        model = _base_model()
        load = gate.load_calibration(CALIBRATION_PATH)
        out_of_sample = gate.leave_one_out(model, load.entries)
        calibration = _calibration(model)
        self.assertEqual(
            round(out_of_sample.fraction_in_band, 4),
            _num(calibration["fraction_in_band"]),
        )
        self.assertEqual(round(out_of_sample.mdape, 4), _num(calibration["mdape"]))

    def test_the_census_pairings_are_all_class_only(self) -> None:
        census = _json(CALIBRATION_PATH)
        rows = _arr(census["rows"])
        self.assertTrue(rows)
        for raw in rows:
            row = _obj(raw, "census row")
            with self.subTest(identifier=row["id"]):
                self.assertEqual("class_only", _str(row["mapping_basis"]))


class MetricFixtureTest(unittest.TestCase):
    """The metric functions reproduce a fixture with known answers."""

    def test_the_in_band_fraction_and_mdape_match_the_fixture(self) -> None:
        model = _fixture_with_fills(0.05, 0.10)
        entries = [
            _entry("fix_in", mass=100.0),
            _entry("fix_out", mass=400.0),
        ]
        metrics = gate.evaluate(model, entries)
        self.assertEqual(2, metrics.n_entries)
        self.assertEqual(1, metrics.in_band)
        self.assertAlmostEqual(0.5, metrics.fraction_in_band)
        self.assertAlmostEqual(0.375, metrics.mdape)

    def test_a_zero_fill_band_scores_nothing_in_band(self) -> None:
        metrics = gate.evaluate(
            _fixture_with_fills(0.0, 0.0), [_entry("fix", mass=100.0)]
        )
        self.assertEqual(1, metrics.n_entries)
        self.assertEqual(0, metrics.in_band)
        self.assertAlmostEqual(1.0, metrics.mdape)

    def test_the_width_ratio_is_high_over_low(self) -> None:
        metric = gate.ClassMetric(
            key="fixture",
            n=1,
            fill_low=0.05,
            fill_high=0.10,
            rho_low=1000.0,
            rho_high=2000.0,
        )
        self.assertAlmostEqual(4.0, metric.width_ratio())

    def test_a_zero_fill_low_gives_an_infinite_width_ratio(self) -> None:
        metric = gate.ClassMetric(
            key="fixture",
            n=1,
            fill_low=0.0,
            fill_high=0.10,
            rho_low=1000.0,
            rho_high=2000.0,
        )
        self.assertEqual(float("inf"), metric.width_ratio())

    def test_calibration_reproduces_the_known_proposal(self) -> None:
        entries = [
            _entry("fix_a", mass=100.0),
            _entry("fix_b", mass=150.0, height_mm=2000.0),
        ]
        proposals, calibrated = gate.calibrate(_fixture_model(), entries)
        by_key = {proposal.key: proposal for proposal in proposals}
        self.assertIn("wheeled", by_key)
        wheeled = by_key["wheeled"]
        self.assertAlmostEqual(0.0375, wheeled.f_lo_raw)
        self.assertAlmostEqual(0.1000, wheeled.f_hi_raw)
        self.assertAlmostEqual(0.0319, wheeled.fill_low)
        self.assertAlmostEqual(0.1150, wheeled.fill_high)
        self.assertAlmostEqual(1.0, calibrated.fraction_in_band)
        metric = next(item for item in calibrated.classes if item.key == "wheeled")
        self.assertAlmostEqual(7.2100, metric.width_ratio(), places=3)

    def test_a_weight_is_picked_in_order_and_never_averaged(self) -> None:
        entry = _entry("fix_conflict", mass=100.0, gross=200.0)
        self.assertEqual(("curb_weight_kg", 100.0), gate.documented_mass(entry))

    def test_a_degenerate_box_is_skipped(self) -> None:
        zero = _entry("fix_zero", mass=100.0, length_mm=0.0)
        missing = _entry("fix_missing", mass=100.0, length_mm=None)
        self.assertEqual("non-positive dimension (zero volume)", gate.skip_reason(zero))
        self.assertEqual(
            "missing length_mm, width_mm or height_mm",
            gate.skip_reason(missing),
        )


class GeneratorFreshnessTest(unittest.TestCase):
    """The generated table matches a fresh render of the model."""

    def test_the_committed_table_matches_the_render(self) -> None:
        rendered = gen.render_table(gen.build_table(_base_model()))
        self.assertEqual(rendered, _generated_text())

    def test_the_generated_table_holds_five_blocks(self) -> None:
        table = gen.build_table(_base_model())
        self.assertEqual(5, len(table))
        self.assertEqual(len(DENSITY_CLASSES), len(_arr(table[1], "densityTable")))
        classes = _arr(table[2], "massClasses")
        self.assertEqual(len(MASS_CLASS_KEYS), len(classes))
        self.assertEqual("default", _str(_arr(classes[-1])[0]))
        self.assertEqual(3, len(_arr(table[3], "geometryBands")))

    def test_the_check_mode_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GENERATOR), "--check"],
            capture_output=True,
            text=True,
            cwd=str(REPO),
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("fresh", result.stdout)

    def test_a_stale_copy_is_rejected_and_not_rewritten(self) -> None:
        rendered = gen.render_table(gen.build_table(_base_model()))
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "stale.sqf"
            _ = stale.write_text(rendered + "// stale\n", encoding="utf-8")
            before = stale.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                code = gen.check_output(stale, rendered)
            after = stale.read_bytes()
        self.assertEqual(1, code)
        self.assertEqual(before, after)

    def test_a_missing_output_is_rejected(self) -> None:
        rendered = gen.render_table(gen.build_table(_base_model()))
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stderr(io.StringIO()):
                code = gen.check_output(Path(tmp) / "missing.sqf", rendered)
        self.assertEqual(1, code)

    def test_a_missing_model_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(gen.ModelError):
                gen.load_model(Path(tmp) / "missing.json")

    def test_a_malformed_model_is_rejected(self) -> None:
        def set_schema(model: JsonObject) -> None:
            model["schema"] = "wrong"

        def invert_density(model: JsonObject) -> None:
            _density_entry(model, "metal")["low"] = 9000

        def string_density(model: JsonObject) -> None:
            _density_entry(model, "metal")["low"] = "high"

        def unknown_density_class(model: JsonObject) -> None:
            _class_at(model, 0)["density_class"] = "ghost"

        def inverted_fill(model: JsonObject) -> None:
            _class_at(model, 0)["fill_low"] = 0.5
            _class_at(model, 0)["fill_high"] = 0.1

        def no_default(model: JsonObject) -> None:
            _class_at(model, -1)["match"] = "token"

        def non_bool_approved(model: JsonObject) -> None:
            _calibration(model)["approved"] = "yes"

        def bad_bands(model: JsonObject) -> None:
            _geometry(model)["min_extent_m"] = 21.0

        def bad_width_ratio(model: JsonObject) -> None:
            _geometry(model)["max_width_ratio"] = 0.0

        def non_bool_power(model: JsonObject) -> None:
            _power(model)["enabled"] = 1

        mutations: dict[str, Mutator] = {
            "schema": set_schema,
            "inverted_density": invert_density,
            "string_density": string_density,
            "unknown_density_class": unknown_density_class,
            "inverted_fill": inverted_fill,
            "no_default": no_default,
            "non_bool_approved": non_bool_approved,
            "bad_bands": bad_bands,
            "bad_width_ratio": bad_width_ratio,
            "non_bool_power": non_bool_power,
        }
        for name, mutate in mutations.items():
            payload = copy.deepcopy(_base_model())
            mutate(payload)
            with self.subTest(case=name):
                with self.assertRaises(gen.ModelError):
                    gen.build_table(payload)

    def test_the_generator_writes_nothing_on_a_model_error(self) -> None:
        payload = copy.deepcopy(_base_model())
        payload["schema"] = "wrong"
        with tempfile.TemporaryDirectory() as tmp:
            bad_model = Path(tmp) / "bad.json"
            out = Path(tmp) / "out.sqf"
            _ = bad_model.write_text(json.dumps(payload), encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                code = gen.main(["--model", str(bad_model), "--out", str(out)])
            self.assertEqual(2, code)
            self.assertFalse(out.exists())


class MalformedModelGateTest(unittest.TestCase):
    """The gate refuses a malformed model with a named error."""

    def test_a_non_object_top_level_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.json"
            _ = path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                _ = gate.load_model(path)

    def test_a_missing_model_raises_an_os_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(OSError):
                _ = gate.load_model(Path(tmp) / "missing.json")

    def test_the_missing_model_cli_exits_non_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = gate.main(["--data-dir", tmp])
            output = buffer.getvalue()
        self.assertEqual(1, code)
        self.assertIn("cannot read", output)

    def test_each_structural_fault_gets_a_named_error(self) -> None:
        def set_schema(model: JsonObject) -> None:
            model["schema"] = "wrong"

        def empty_density(model: JsonObject) -> None:
            model["material_density"] = {}

        def missing_citation(model: JsonObject) -> None:
            _ = _density_entry(model, "metal").pop("source")

        def inverted_density(model: JsonObject) -> None:
            _density_entry(model, "metal")["high"] = 10

        def unknown_density_class(model: JsonObject) -> None:
            _class_at(model, 0)["density_class"] = "ghost"

        def inverted_fill(model: JsonObject) -> None:
            _class_at(model, 0)["fill_low"] = 0.5

        def calibration_shape(model: JsonObject) -> None:
            model["calibration"] = "no"

        def approved_shape(model: JsonObject) -> None:
            _calibration(model)["approved"] = "yes"

        def bands_shape(model: JsonObject) -> None:
            model["geometry_bands"] = "no"

        def classes_shape(model: JsonObject) -> None:
            model["mass_classes"] = []

        cases: dict[str, tuple[Mutator, str]] = {
            "schema": (set_schema, "schema must be"),
            "empty_density": (
                empty_density,
                "material_density must be a non-empty object",
            ),
            "missing_citation": (missing_citation, "needs a source and a locator"),
            "inverted_density": (inverted_density, "0 < low < high"),
            "unknown_density_class": (unknown_density_class, "is undefined"),
            "inverted_fill": (inverted_fill, "0 <= fill_low <= fill_high"),
            "calibration_shape": (
                calibration_shape,
                "calibration must be an object",
            ),
            "approved_shape": (
                approved_shape,
                "approved must be true or false",
            ),
            "bands_shape": (bands_shape, "geometry_bands must be an object"),
            "classes_shape": (
                classes_shape,
                "mass_classes must be a non-empty array",
            ),
        }
        for name, (mutate, needle) in cases.items():
            model = copy.deepcopy(_base_model())
            mutate(model)
            with self.subTest(case=name):
                errors = gate.model_errors(model)
                self.assertTrue(
                    any(needle in error for error in errors),
                    f"{needle!r} not in {errors}",
                )


class SeparationTest(unittest.TestCase):
    """The model and the table stay clear of the catalogue and the consumers."""

    def test_the_model_holds_no_catalogue_weight_field(self) -> None:
        for kind, value in _walk_strings(_base_model()):
            if kind == "key":
                with self.subTest(key=value):
                    self.assertNotIn(value, CATALOGUE_MASS_FIELDS)

    def test_the_generated_table_holds_no_catalogue_weight_field(self) -> None:
        text = _generated_text()
        for field in CATALOGUE_MASS_FIELDS:
            with self.subTest(field=field):
                self.assertNotIn(field, text)

    def test_neither_artefact_holds_a_catalogue_identity(self) -> None:
        load = catalogue.load(DATA)
        self.assertEqual([], load.errors)
        identities = {entry.catalogue_id for entry in load.entries}
        identities |= {entry.variant_id for entry in load.entries}
        identities.discard("")
        model_text = _text(MODEL_PATH)
        generated_text = _generated_text()
        for identity in identities:
            with self.subTest(identity=identity):
                self.assertNotIn(identity, model_text)
                self.assertNotIn(identity, generated_text)

    def test_no_catalogue_file_mentions_the_model(self) -> None:
        candidates = sorted((DATA / "catalogue").glob("*.json"))
        candidates += [DATA / "class_map.json", DATA / "coverage.json"]
        for path in candidates:
            with self.subTest(path=path.name):
                text = _text(path)
                self.assertNotIn("mass_model", text)
                self.assertNotIn("estimated_mass_kg", text)

    def test_the_generated_table_is_a_data_table_only(self) -> None:
        text = _generated_text()
        forbidden = (
            "configFile",
            "boundingBoxReal",
            "getMass",
            "setObjectMaterial",
            "calculateSoilStrength",
            "getSurfaceMaterial",
            "getVehicleMatch",
            "createHashMap",
            "params",
            "PREP(",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, text)
        self.assertIsNone(re.search(r"\bcall\b", text))

    def test_the_parameter_table_has_no_unexpected_reference(self) -> None:
        referenced: set[str] = set()
        for path in _addon_text_files():
            if "getVehicleMassModel" in _text(path):
                referenced.add(path.relative_to(REPO).as_posix())
        self.assertTrue(
            referenced.issubset(ALLOWED_TABLE_REFERENCE),
            f"unexpected reference: {sorted(referenced - ALLOWED_TABLE_REFERENCE)}",
        )

    def test_no_driving_function_reads_the_estimate(self) -> None:
        functions = REPO / "addons" / "mobility" / "functions"
        for name in DRIVING_FUNCTIONS:
            path = functions / name
            self.assertTrue(path.is_file(), path)
            text = _text(path)
            with self.subTest(function=name):
                self.assertNotIn("estimateVehicleMass", text)
                self.assertNotIn("getVehicleMassModel", text)

    def test_the_soil_strength_nrmm_path_is_quarantined(self) -> None:
        soil = (
            REPO / "addons" / "mobility" / "functions" / "fnc_calculateSoilStrength.sqf"
        )
        text = _text(soil)
        self.assertNotIn("mass_model", text)
        self.assertNotIn("estimateVehicleMass", text)


if __name__ == "__main__":
    unittest.main()
