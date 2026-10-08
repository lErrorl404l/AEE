#!/usr/bin/env python3
"""The AEE terrain symbol catalogue contract tests.

The DGIWG Symbol Register publishes which concepts each SO_#### symbol
depicts.  These tests pin the AEE terrain mapping to that published index, so
a symbol that merely "seems right" cannot ship.  They fail when:

  * a feature maps to a register symbol that does not publish the feature's
    concept (a "seems right" mapping);
  * two different features resolve to the same source SVG and are not
    allow-listed with a recorded reason;
  * the catalogue is missing a row, or a row disagrees with the manifest;
  * the committed catalogue is stale.

Run: python3 -m unittest tools.tests.test_terrain_catalogue -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
REGISTER = REPO / "data" / "symbology" / "dgiwg_concepts.json"
SOURCES = REPO / "data" / "symbology" / "terrain_sources.json"
SYMBOLS = REPO / "data" / "symbology" / "terrain_symbols.json"
CATALOGUE = REPO / "data" / "symbology" / "terrain_catalogue.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def register_concepts() -> dict[str, set[str]]:
    return {e["id"]: set(e["concepts"]) for e in _load(REGISTER)}


def manifest_entries() -> list[dict]:
    return _load(SOURCES)["entries"]


def referenced_symbols() -> list[str]:
    doc = _load(SYMBOLS)
    out: list[str] = []
    for section in ("locations", "objects"):
        for row in doc.get(section, []):
            symbol = row.get("symbol")
            if symbol and symbol not in out:
                out.append(symbol)
    return out


class TestPublishedConcept(unittest.TestCase):
    """A feature's concept must be published by the register symbol it uses."""

    def test_every_glyph_concept_is_published_by_its_register_symbol(self):
        concepts = register_concepts()
        for entry in manifest_entries():
            if not entry.get("dgiwg") or not entry.get("glyph_concept"):
                # A substitution with no register concept for the feature (wave)
                # carries a null glyph concept and is gated by the recorded
                # substitution test instead.
                continue
            with self.subTest(symbol=entry["id"]):
                self.assertIn(
                    entry["glyph_concept"],
                    concepts[entry["dgiwg"]],
                    f"{entry['id']} uses {entry['dgiwg']} but that symbol does "
                    f"not publish {entry['glyph_concept']}",
                )

    def test_every_specific_concept_is_published_by_its_register_symbol(self):
        concepts = register_concepts()
        for entry in manifest_entries():
            if entry.get("grade") == "substituted" or not entry.get("concept"):
                continue
            with self.subTest(symbol=entry["id"]):
                self.assertIn(
                    entry["concept"],
                    concepts[entry["dgiwg"]],
                    f"{entry['id']} needs {entry['concept']} but {entry['dgiwg']} "
                    "does not publish it",
                )

    def test_every_substitution_is_recorded_with_a_reason(self):
        recorded = {s["id"]: s for s in _load(SOURCES).get("substituted", [])}
        for entry in manifest_entries():
            if entry.get("grade") != "substituted":
                continue
            with self.subTest(symbol=entry["id"]):
                self.assertIn(entry["id"], recorded)
                reason = recorded[entry["id"]].get("reason", "")
                self.assertTrue(reason, f"{entry['id']} has no recorded reason")
                self.assertIn(recorded[entry["id"]]["dgiwg"], (entry["dgiwg"],))


class TestSharedSources(unittest.TestCase):
    """Two features may share a drawing only when it is allow-listed."""

    def test_no_unlisted_shared_source_svg(self):
        allowed: dict[str, set[str]] = {}
        for group in _load(SOURCES).get("shared_symbols", []):
            allowed.setdefault(group["dgiwg"], set()).update(group["ids"])
        by_svg: dict[str, list[str]] = {}
        for entry in manifest_entries():
            if entry.get("svg"):
                by_svg.setdefault(entry["svg"], []).append(entry["id"])
        for svg, ids in by_svg.items():
            if len(ids) < 2:
                continue
            register_id = next(
                e["dgiwg"] for e in manifest_entries() if e["id"] == ids[0]
            )
            with self.subTest(svg=svg):
                self.assertIn(
                    register_id,
                    allowed,
                    f"{ids} share {svg} but are not allow-listed",
                )
                self.assertEqual(
                    set(ids),
                    allowed[register_id],
                    f"{ids} share {svg}; the allow-list records "
                    f"{sorted(allowed[register_id])}",
                )

    def test_every_shared_group_has_a_recorded_reason(self):
        for group in _load(SOURCES).get("shared_symbols", []):
            with self.subTest(dgiwg=group["dgiwg"]):
                self.assertTrue(group.get("reason"), "no recorded reason")
                self.assertGreaterEqual(len(group["ids"]), 2)


class TestCatalogueRows(unittest.TestCase):
    """Every manifest entry has one catalogue row, and the rows agree."""

    def test_catalogue_row_count_matches_the_manifest(self):
        rows = _load(CATALOGUE)["entries"]
        self.assertEqual(len(rows), len(manifest_entries()))

    def test_every_manifest_entry_has_a_matching_row(self):
        rows = {r["id"]: r for r in _load(CATALOGUE)["entries"]}
        for entry in manifest_entries():
            with self.subTest(symbol=entry["id"]):
                self.assertIn(entry["id"], rows)
                row = rows[entry["id"]]
                self.assertEqual(row["register_id"], entry.get("dgiwg"))
                self.assertEqual(row["glyph_concept"], entry.get("glyph_concept"))
                self.assertEqual(row["grade"], entry.get("grade"))
                self.assertTrue(row["depicts"], "row has no depiction")
                self.assertTrue(row["source"], "row has no source")
                self.assertTrue(row["licence"], "row has no licence")

    def test_every_referenced_symbol_has_a_manifest_entry(self):
        ids = {e["id"] for e in manifest_entries()}
        for symbol in referenced_symbols():
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, ids)

    def test_every_manifest_entry_is_referenced_or_recorded(self):
        refs = set(referenced_symbols())
        for entry in manifest_entries():
            with self.subTest(symbol=entry["id"]):
                self.assertIn(entry["id"], refs)


class TestCatalogueFreshness(unittest.TestCase):
    """The committed catalogue must match a fresh generation."""

    def test_committed_catalogue_is_fresh(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO / "tools" / "gen_terrain_catalogue.py"),
                "--check",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
