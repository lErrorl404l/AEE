#!/usr/bin/env python3
"""The AEE APP-6 marker catalogue contract tests.

The catalogue is a generated legend, not hand-written data.  These tests pin it
to its two sources: data/symbology/nato_catalogue.json (every symbol has a row,
with the same affiliation and dimension) and addons/symbology/config_markers.hpp
(every used_for value names a real engine override).  The final test runs the
generator's own --check, the same gate CI runs, so a stale committed legend
fails here.

Run: python3 -m unittest tools.tests.test_app6_catalogue -v
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools import gen_app6_catalogue as gen  # noqa: E402
from tools import gen_symbology_catalogue as sym  # noqa: E402

SOURCE = json.loads(
    (REPO / "data" / "symbology" / "nato_catalogue.json").read_text(encoding="utf-8")
)
CATALOGUE = json.loads(
    (REPO / "data" / "symbology" / "app6_catalogue.json").read_text(encoding="utf-8")
)
ROWS = CATALOGUE["entries"]
BY_ID = {row["id"]: row for row in ROWS}


def source_symbols() -> list[dict]:
    return [e for e in SOURCE["entries"] if e.get("kind", "symbol") == "symbol"]


def marker_ids() -> list[str]:
    seen: set[str] = set()
    return [sym.marker_name(e, seen) for e in source_symbols()]


class TestCatalogueCoverage(unittest.TestCase):
    """Every catalogue symbol has exactly one row, and no extra row exists."""

    def test_the_count_equals_the_symbol_count(self):
        self.assertEqual(CATALOGUE["count"], len(source_symbols()))
        self.assertEqual(len(ROWS), len(source_symbols()))

    def test_every_symbol_has_a_row(self):
        for name in marker_ids():
            with self.subTest(marker=name):
                self.assertIn(name, BY_ID)

    def test_no_row_names_a_marker_outside_the_symbol_set(self):
        ids = set(marker_ids())
        for row in ROWS:
            with self.subTest(marker=row["id"]):
                self.assertIn(row["id"], ids)


class TestRowMatchesSource(unittest.TestCase):
    """Each row carries the affiliation and dimension of its source entry."""

    def test_affiliation_and_dimension_match_the_source(self):
        seen: set[str] = set()
        for entry in source_symbols():
            name = sym.marker_name(entry, seen)
            row = BY_ID[name]
            with self.subTest(marker=name):
                self.assertEqual(row["affiliation"], entry["affil"])
                self.assertEqual(row["dimension"], entry["dim"])

    def test_the_kind_is_always_symbol(self):
        for row in ROWS:
            with self.subTest(marker=row["id"]):
                self.assertEqual(row["kind"], "symbol")


class TestUsedFor(unittest.TestCase):
    """Each used_for value names a real engine override, and each preview exists."""

    def test_every_used_for_names_an_engine_override(self):
        overrides = gen.override_map()
        engine_classes = {c for classes in overrides.values() for c in classes}
        for row in ROWS:
            if row["used_for"] is None:
                continue
            with self.subTest(marker=row["id"]):
                for cls in row["used_for"].split(", "):
                    self.assertIn(cls, engine_classes)

    def test_used_for_engine_class_points_back_at_the_marker(self):
        overrides = gen.override_map()
        by_class = {
            cls: marker for marker, classes in overrides.items() for cls in classes
        }
        for row in ROWS:
            if row["used_for"] is None:
                continue
            for cls in row["used_for"].split(", "):
                with self.subTest(marker=row["id"], cls=cls):
                    self.assertEqual(by_class.get(cls), row["id"])

    def test_every_preview_texture_exists(self):
        for row in ROWS:
            with self.subTest(marker=row["id"]):
                self.assertTrue(
                    (REPO / row["preview"]).is_file(),
                    f"{row['id']} names a missing texture {row['preview']}",
                )


class TestCatalogueFreshness(unittest.TestCase):
    """The committed catalogue and markdown match a fresh generation.

    The generator is the only writer.  A stale committed legend passes the
    source-level tests above but ships the wrong data, so this runs the same
    --check gate CI runs.
    """

    def test_committed_catalogue_and_markdown_are_fresh(self):
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(REPO / "tools" / "gen_app6_catalogue.py"), "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
