#!/usr/bin/env python3
"""Separation guard for the vehicle mass estimate layer (task 12).

The estimate is a model. It must not touch the sourced corpus and it must not
touch the NRMM soil path. This module is the hard guard between the two.

Cases:

  * the NRMM file digest equals one pinned value;
  * the generated matcher and lookup equal a fresh render;
  * no catalogue file names the model or an estimated mass;
  * the class map holds no estimated-mass field;
  * the model JSON is the only new top-level JSON under ``data/vehicle/``;
  * the estimator mutates no material, no cache and no NRMM result;
  * the generated table holds no sourced grade token.

The suite pins only the NRMM file. It never pins the catalogue directory,
because the corpus changes on purpose. Every write goes to a ``tempfile``
copy. The suite edits no product file.

Run: python3 -m unittest tools.tests.test_vehicle_mass_separation -v
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Iterator, cast

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.validation import gen_vehicle_data as corpus_gen  # noqa: E402
from tools.validation import gen_vehicle_mass_model as model_gen  # noqa: E402

DATA = ROOT / "data" / "vehicle"
CATALOGUE = DATA / "catalogue"
CLASS_MAP = DATA / "class_map.json"
MODEL = DATA / "mass_model.json"

FUNCTIONS = ROOT / "addons" / "mobility" / "functions"
NRMM = FUNCTIONS / "fnc_calculateSoilStrength.sqf"
MATCH = FUNCTIONS / "fnc_getVehicleMatch.sqf"
LOOKUP = FUNCTIONS / "fnc_getVehicleData.sqf"
TABLE = FUNCTIONS / "fnc_getVehicleMassModel.sqf"
WRAPPER = FUNCTIONS / "fnc_estimateVehicleMass.sqf"
CORE = FUNCTIONS / "fnc_estimateVehicleMassCore.sqf"

# The NRMM soil path is fail-closed and quarantined (issue #117). It publishes
# no numeric result until sourced records exist. This digest pins the file, so
# no change to the estimate layer can alter the soil path without notice. Only
# this file is pinned. The catalogue directory is never pinned, because the
# sourced corpus changes on purpose.
NRMM_SHA256 = "135d6a3e6bf2e797d256887a27a76bdffa47bcb11bc092bcbe8b45b5e3f1050a"
NRMM_QUARANTINE_NOTE = (
    "the NRMM soil path is quarantined and fail-closed; this digest pins it"
)

# The mass model artefact and the committed in-game census are the two files
# this work adds at the data root. A new top-level JSON outside this list
# breaks the separation guard.
TOP_LEVEL_JSON_BASELINE = frozenset(
    {"classes.json", "class_map.json", "coverage.json", "sources.json"}
)
TOP_LEVEL_JSON_NEW = frozenset({"mass_model.json", "mass_model_calibration.json"})

# The estimator reports a mass. It must not write the material cache, the class
# cache, the object material, or the soil result.
FORBIDDEN_ESTIMATOR_TOKENS = (
    "setObjectMaterial",
    "setObjectMaterialGlobal",
    "setMaterial",
    "classCache",
    "materialCache",
    "calculateSoilStrength",
)
# A modelled value is never labelled with a sourced-corpus grade.
GRADE_TOKENS = ("documented", "claimed")
# The catalogue weight field this layer must never add.
ESTIMATED_MASS_FIELD = "estimated_mass_kg"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(path: Path) -> str:
    """Return a UTF-8 file as text."""
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> object:
    """Parse a JSON file to a plain tree."""
    return cast("object", json.loads(text(path)))


def tree_keys(value: object) -> Iterator[str]:
    """Yield every object key in a parsed JSON tree."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from tree_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from tree_keys(item)


class NrmmQuarantineTest(unittest.TestCase):
    """The soil path stays byte-for-byte as approved and stays quarantined."""

    def assert_pinned_digest(self, path: Path) -> None:
        self.assertEqual(sha256_file(path), NRMM_SHA256, NRMM_QUARANTINE_NOTE)

    def test_the_nrmm_file_digest_is_pinned(self) -> None:
        self.assertTrue(NRMM.is_file(), NRMM)
        self.assert_pinned_digest(NRMM)

    def test_the_nrmm_file_is_still_fail_closed(self) -> None:
        body = text(NRMM)
        self.assertIn("QUARANTINED", body)
        self.assertIn(
            "missionNamespace setVariable [QGVAR(currentSoilStrengthKnown), false]",
            body,
        )
        self.assertIn("[false, _reason]", body)

    def test_a_one_character_mutation_fails_the_pinned_digest(self) -> None:
        source = text(NRMM)
        # One character changes: the final "s" becomes "x". The anchor is the
        # unique code assignment, not the comment.
        mutated = source.replace(
            '_reason = "unverifiedInputs";',
            '_reason = "unverifiedInputx";',
            1,
        )
        self.assertNotEqual(source, mutated, "the mutation anchor must be present")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / NRMM.name
            path.write_text(mutated, encoding="utf-8")
            self.assertNotEqual(sha256_file(path), NRMM_SHA256)
            with self.assertRaises(AssertionError):
                self.assert_pinned_digest(path)
        self.assert_pinned_digest(NRMM)


class GeneratedCorpusFreshnessTest(unittest.TestCase):
    """The matcher and the lookup are projections of the catalogue."""

    def test_the_generated_matcher_and_lookup_are_fresh(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            status = corpus_gen.check_outputs(DATA)
        self.assertEqual(status, 0)

    def test_the_committed_matcher_equals_a_fresh_render(self) -> None:
        rows = corpus_gen.load_rows(DATA)
        self.assertEqual(
            text(MATCH), corpus_gen.render_match(rows), "fnc_getVehicleMatch is stale"
        )

    def test_the_committed_lookup_equals_a_fresh_render(self) -> None:
        self.assertEqual(
            text(LOOKUP), corpus_gen.render_data(), "fnc_getVehicleData is stale"
        )

    def test_a_stale_matcher_copy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / MATCH.name
            stale.write_text(text(MATCH) + "// stale\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                status = corpus_gen.check_outputs(DATA, stale, LOOKUP)
            self.assertEqual(status, 1)
        self.assertNotEqual(text(MATCH), text(MATCH) + "// stale\n")

    def test_a_stale_lookup_copy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / LOOKUP.name
            stale.write_text(corpus_gen.render_data() + "// stale\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                status = corpus_gen.check_outputs(DATA, MATCH, stale)
            self.assertEqual(status, 1)

    def test_a_missing_matcher_copy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / MATCH.name
            with contextlib.redirect_stdout(io.StringIO()):
                status = corpus_gen.check_outputs(DATA, missing, LOOKUP)
            self.assertEqual(status, 1)

    def test_a_stale_mass_model_table_copy_is_rejected(self) -> None:
        payload = model_gen.load_model(MODEL)
        fresh = model_gen.render_table(model_gen.build_table(payload))
        self.assertEqual(text(TABLE), fresh, "fnc_getVehicleMassModel is stale")
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / TABLE.name
            stale.write_text(fresh + "// stale\n", encoding="utf-8")
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                status = model_gen.check_output(stale, fresh)
            self.assertEqual(status, 1)


class CatalogueSeparationTest(unittest.TestCase):
    """The sourced corpus holds no model key and no estimated mass."""

    def test_the_catalogue_directory_is_not_empty(self) -> None:
        self.assertTrue(sorted(CATALOGUE.glob("*.json")))

    def test_no_catalogue_file_names_the_model_or_an_estimate(self) -> None:
        for path in sorted(CATALOGUE.glob("*.json")):
            with self.subTest(path=path.name):
                body = text(path)
                self.assertNotIn("mass_model", body)
                self.assertNotIn("estimated", body)

    def test_the_class_map_holds_no_estimated_mass_field(self) -> None:
        keys = list(tree_keys(load_json(CLASS_MAP)))
        self.assertNotIn(ESTIMATED_MASS_FIELD, keys)
        self.assertFalse([key for key in keys if key.startswith("estimated")])

    def test_the_class_map_still_uses_the_sourced_grade(self) -> None:
        # The class map is untouched by this work. Its sourced grade remains.
        keys = set(tree_keys(load_json(CLASS_MAP)))
        self.assertIn("catalogue_id", keys)
        self.assertIn("grade", keys)

    def test_the_mass_model_is_the_only_new_top_level_json(self) -> None:
        found = {path.name for path in DATA.glob("*.json")}
        self.assertTrue(
            TOP_LEVEL_JSON_NEW.issubset(found),
            f"missing: {sorted(TOP_LEVEL_JSON_NEW - found)}",
        )
        self.assertEqual(
            found,
            TOP_LEVEL_JSON_BASELINE | TOP_LEVEL_JSON_NEW,
            "an unexpected top-level JSON appeared under data/vehicle/",
        )


class EstimatorSeparationTest(unittest.TestCase):
    """The estimator is separate from the corpus and from the NRMM path."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wrapper = text(WRAPPER)
        cls.core = text(CORE)
        cls.table = text(TABLE)
        cls.nrmm = text(NRMM)

    def test_the_estimator_holds_no_forbidden_effect(self) -> None:
        for name, body in (("wrapper", self.wrapper), ("core", self.core)):
            for token in FORBIDDEN_ESTIMATOR_TOKENS:
                with self.subTest(file=name, token=token):
                    self.assertNotIn(token, body)

    def test_the_estimator_never_references_the_soil_strength_call(self) -> None:
        self.assertNotIn("calculateSoilStrength", self.wrapper)
        self.assertNotIn("calculateSoilStrength", self.core)
        self.assertNotIn("calculateSoilStrength", self.table)

    def test_the_estimator_does_not_write_a_material_cache(self) -> None:
        for body in (self.wrapper, self.core, self.table):
            self.assertNotIn("classCache", body)
            self.assertNotIn("materialCache", body)
            self.assertNotIn("setObjectMaterial", body)

    def test_the_nrmm_file_never_names_the_estimator(self) -> None:
        self.assertNotIn("estimateVehicleMass", self.nrmm)
        self.assertNotIn("getVehicleMassModel", self.nrmm)
        self.assertNotIn("mass_model", self.nrmm)

    def test_the_generated_table_holds_no_grade_token(self) -> None:
        lowered = self.table.casefold()
        for token in GRADE_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, lowered)

    def test_the_wrapper_and_core_are_separate_from_the_nrmm_path(self) -> None:
        # The core reads no engine state at all, and the wrapper reads only the
        # material component. Neither reads a soil or NRMM value.
        for token in ("calculateSoilStrength", "currentSoilStrengthKnown", "VCI"):
            with self.subTest(token=token):
                self.assertNotIn(token, self.core)
                self.assertNotIn(token, self.wrapper)


if __name__ == "__main__":
    unittest.main()
