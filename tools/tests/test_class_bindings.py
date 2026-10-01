#!/usr/bin/env python3
"""Concrete class-binding gate tests.

The binding layer binds one concrete AEE game class to one held catalogue
entry. The validator is the gate. These tests prove a clean file passes, a
duplicate game class fails and an unresolved catalogue id fails. The good
records come from the committed layer. The bad records are copies held in
this test only.

Run: python3 -m unittest tools.tests.test_class_bindings -v
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import validate_class_bindings as v  # noqa: E402

DATA = REPO / "data" / "vehicle"
BINDINGS = DATA / "class_bindings.json"


class ClassBindingsTest(unittest.TestCase):
    """The committed layer is valid and the gate rejects a broken layer."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.records = v.load_bindings(BINDINGS)
        cls.ids = v.catalogue_ids(DATA)
        cls.sources = v.sources_by_id(DATA)

    def test_the_committed_file_is_clean(self) -> None:
        self.assertEqual(v.validate_bindings(self.records, self.ids, self.sources), [])

    def test_the_cli_passes(self) -> None:
        self.assertEqual(v.main([]), 0)

    def test_a_duplicate_game_class_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records.append(copy.deepcopy(records[0]))
        errors = v.validate_bindings(records, self.ids, self.sources)
        self.assertTrue(any("duplicate game_class" in e for e in errors), errors)

    def test_an_unresolvable_catalogue_id_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["catalogue_id"] = "no_such_catalogue_entry"
        errors = v.validate_bindings(records, self.ids, self.sources)
        self.assertTrue(any("unknown catalogue_id" in e for e in errors), errors)

    def test_every_catalogue_id_resolves(self) -> None:
        for record in self.records:
            with self.subTest(game_class=record["game_class"]):
                self.assertIn(record["catalogue_id"], self.ids)

    def test_every_game_class_is_unique(self) -> None:
        classes = [record["game_class"] for record in self.records]
        self.assertEqual(len(classes), len(set(classes)))

    def test_every_grade_is_the_schema_vocabulary(self) -> None:
        for record in self.records:
            with self.subTest(game_class=record["game_class"]):
                self.assertIn(record["grade"], v.GRADES)

    def test_no_required_field_is_empty(self) -> None:
        for record in self.records:
            for field in v.REQUIRED_FIELDS:
                with self.subTest(game_class=record["game_class"], field=field):
                    self.assertTrue(str(record.get(field)).strip())

    def test_an_unknown_identity_source_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["identity_source"] = "no_such_source"
        errors = v.validate_bindings(records, self.ids, self.sources)
        self.assertTrue(any("unknown identity_source" in e for e in errors), errors)

    def test_a_claimed_engine_binding_names_the_token(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["identity_evidence"] = "no token named here"
        errors = v.validate_bindings(records, self.ids, self.sources)
        self.assertTrue(
            any("must name the concrete class token" in e for e in errors), errors
        )

    def test_a_non_array_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / v.BINDINGS_NAME
            path.write_text(json.dumps({"game_class": "x"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                v.load_bindings(path)


if __name__ == "__main__":
    unittest.main()
