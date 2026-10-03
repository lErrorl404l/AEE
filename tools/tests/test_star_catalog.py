#!/usr/bin/env python3
"""Full star catalogue data and wiring (issue #122).

The 9,050-star catalogue is generated from BSC5 (catalog.dat) by
tools/validation/gen_star_catalog.py.  This suite locks the data contract
(count, uniqueness, sort order, anchors) and the wiring contract (the
catalog function loads the generated data, the PREP entry exists, and the
light-emitter render is capped at a bright-magnitude ceiling).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "validation"))

from gen_star_catalog import parse_all, V_CUTOFF  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SENSOR = ROOT / "addons" / "optics" / "functions" / "sensor"


def near(a, b, tol):
    return abs(a - b) < tol


class TestCatalogData(unittest.TestCase):
    """The generated catalogue is complete, unique, and sorted."""

    def test_count_is_9050(self):
        self.assertEqual(len(parse_all()), 9050)

    def test_no_duplicate_names(self):
        names = [r[0] for r in parse_all()]
        self.assertEqual(len(names), len(set(names)))

    def test_sorted_by_magnitude(self):
        vmags = [r[3] for r in parse_all()]
        self.assertTrue(all(vmags[i] <= vmags[i + 1] for i in range(len(vmags) - 1)))

    def test_all_within_cutoff(self):
        self.assertTrue(all(r[3] <= V_CUTOFF for r in parse_all()))

    def test_anchors(self):
        # [name, raDeg, decDeg, vmag]; BSC5 values, matched by position.
        anchors = [
            ("Sirius", 101.287, -16.716, -1.46),
            ("Canopus", 95.988, -52.696, -0.72),
            ("Vega", 279.235, 38.784, 0.03),
            ("Capella", 79.172, 45.998, 0.08),
            ("Polaris", 37.953, 89.264, 2.02),
        ]
        rows = parse_all()
        for name, ra, dec, vmag in anchors:
            hit = [r for r in rows if near(r[1], ra, 0.2) and near(r[2], dec, 0.2)]
            self.assertTrue(hit, name)
            self.assertAlmostEqual(hit[0][3], vmag, places=2, msg=name)


class TestCatalogWiring(unittest.TestCase):
    """The sensor pipeline loads the generated data and caps the render."""

    def test_catalog_function_loads_generated_data(self):
        text = (SENSOR / "fnc_getStarCatalog.sqf").read_text(encoding="utf-8")
        self.assertIn("call FUNC(starCatalogData)", text)

    def test_prep_entry_exists(self):
        prep = (ROOT / "addons" / "optics" / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREPS(sensor,starCatalogData)", prep)

    def test_render_is_bright_capped(self):
        comp = (ROOT / "addons" / "optics" / "script_component.hpp").read_text(
            encoding="utf-8"
        )
        sync = (SENSOR / "fnc_starLightsSync.sqf").read_text(encoding="utf-8")
        self.assertIn("#define STAR_LIGHT_MAX_MAG", comp)
        self.assertIn("STAR_LIGHT_MAX_MAG", sync)

    def test_catalog_header_mentions_full_catalogue(self):
        text = (SENSOR / "fnc_getStarCatalog.sqf").read_text(encoding="utf-8")
        self.assertIn("Full star catalogue", text)


if __name__ == "__main__":
    unittest.main()
