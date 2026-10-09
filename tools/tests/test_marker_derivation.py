#!/usr/bin/env python3
"""Marker derivation tests: the engine parent, the category and the texture.

The engine marker mapping is DERIVED from the engine's own CfgMarkers and the
committed APP-6 catalogue, never hand-written.  These tests fail when:

  * an engine class is re-declared without restating its REAL parent (a bare
    reopen makes the engine log "Updating base class <p>->''" and strip the
    inherited scope, size, colour and markerClass);
  * an emitted markerClass disagrees with the catalogue row's affiliation and
    dimension (the defect that put the Friendly markers under Unknown);
  * a marker texture is not a real .paa under addons/optics/data/markers.

Run: python3 -m unittest tools.tests.test_marker_derivation -v
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO / "tools"))

import gen_symbology_catalogue as gen  # noqa: E402
from symbology_categories import marker_category  # noqa: E402

OPTICS = REPO / "addons" / "symbology"
CONFIG = (OPTICS / "config.cpp").read_text(encoding="utf-8")
MARKERS = (OPTICS / "config_markers.hpp").read_text(encoding="utf-8")
FAMILY = (OPTICS / "config_family.hpp").read_text(encoding="utf-8")
CACHE = json.loads(
    (REPO / "data" / "symbology" / "engine_markers.json").read_text(encoding="utf-8")
)

ENGINE = {row["game_class"]: row for row in CACHE["rows"]}
PAIRS = gen.entries()
ENGINE_BANNER = "Overwrite the engine's own NATO marker families"
CLASS_RE = re.compile(r"^\s*class ([A-Za-z0-9_]+)(?::\s*([A-Za-z0-9_]+))?\s*\{", re.M)
CATALOGUE_CLASS_RE = re.compile(r"class (\w+): AEE_MarkerBase \{(.*?)\};", re.S)
MARKER_CLASS_RE = re.compile(r'markerClass = "([^"]+)"')
TEXTURE_RE = re.compile(
    r"\\z\\aee\\addons\\symbology\\data\\markers\\([A-Za-z0-9_]+)\.paa"
)
ENGINE_TEXTURE = "\\A3\\ui_f\\data\\map\\markers"


def engine_override_block() -> str:
    """The tail of config_markers.hpp holding the engine re-declarations."""
    return MARKERS[MARKERS.index(ENGINE_BANNER) :]


def emitted_marker_classes() -> dict[str, str]:
    """Every catalogue marker class and the markerClass it carries."""
    out: dict[str, str] = {}
    for name, body in CATALOGUE_CLASS_RE.findall(MARKERS):
        match = MARKER_CLASS_RE.search(body)
        if match is not None:
            out[name] = match.group(1)
    return out


class TestEngineParent(unittest.TestCase):
    """Every re-declared engine class restates its real engine parent."""

    def test_the_block_holds_only_engine_classes(self):
        for cls, _parent in CLASS_RE.findall(engine_override_block()):
            with self.subTest(engine_class=cls):
                self.assertIn(
                    cls, ENGINE, f"{cls} is re-declared but is not an engine class"
                )

    def test_every_class_restates_its_real_parent(self):
        block = engine_override_block()
        classes = CLASS_RE.findall(block)
        self.assertTrue(classes)
        for cls, parent in classes:
            parent = parent or None
            real = ENGINE[cls]["parent_class"]
            with self.subTest(engine_class=cls):
                if real:
                    self.assertEqual(
                        parent, real, f"{cls} must restate its real parent {real}"
                    )
                else:
                    self.assertIsNone(
                        parent, f"{cls} has no engine parent and must be emitted bare"
                    )

    def test_no_bare_reopen_of_an_inherited_engine_class(self):
        # A class whose engine parent is non-empty MUST name that parent.
        for cls, parent in CLASS_RE.findall(engine_override_block()):
            if ENGINE[cls]["parent_class"]:
                with self.subTest(engine_class=cls):
                    self.assertTrue(
                        parent,
                        f"{cls} is a bare reopen; restate {ENGINE[cls]['parent_class']}",
                    )

    def test_the_cache_holds_the_vanilla_scope(self):
        # The live probe proves the scope survives; the cache must hold a value
        # for it, so a re-declaration cannot silently drop it.
        for cls in ("b_inf", "o_armor", "n_unknown"):
            with self.subTest(engine_class=cls):
                self.assertIsNotNone(ENGINE[cls]["scope"])


class TestMarkerCategory(unittest.TestCase):
    """Every emitted markerClass is the catalogue row's real affiliation+role."""

    def test_every_catalogue_marker_carries_its_catalogue_category(self):
        emitted = emitted_marker_classes()
        self.assertEqual(len(emitted), len(PAIRS))
        for name, entry in PAIRS:
            expected = marker_category(
                str(entry.get("affil", "")), str(entry.get("dim", ""))
            )
            with self.subTest(marker=name):
                self.assertEqual(emitted[name], expected)

    def test_the_friendly_markers_carry_a_friend_category(self):
        emitted = emitted_marker_classes()
        for name, entry in PAIRS:
            if entry.get("affil") not in ("Friend", "Friendly"):
                continue
            with self.subTest(marker=name):
                self.assertTrue(emitted[name].startswith("AEE_Friend_"), emitted[name])


class TestMarkerTexture(unittest.TestCase):
    """Every AEE marker texture is a real .paa under data/markers."""

    def test_every_referenced_texture_is_a_real_data_markers_file(self):
        found: set[str] = set()
        for source in (CONFIG, MARKERS, FAMILY):
            for name in TEXTURE_RE.findall(source):
                found.add(name)
                with self.subTest(texture=name):
                    self.assertTrue(
                        (OPTICS / "data" / "markers" / f"{name}.paa").is_file(), name
                    )
        self.assertTrue(found)

    def test_no_marker_points_at_an_engine_texture(self):
        for label, source in (
            ("config.cpp", CONFIG),
            ("config_markers.hpp", MARKERS),
            ("config_family.hpp", FAMILY),
        ):
            with self.subTest(source=label):
                self.assertNotIn(ENGINE_TEXTURE, source)


if __name__ == "__main__":
    unittest.main()
