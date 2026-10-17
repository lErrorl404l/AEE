"""Map preview, layers / grid / map / map-pp commands."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arma_vqa import cli, mapview, sim  # noqa: E402
from arma_vqa.analyze import Analyzer  # noqa: E402
from arma_vqa.rules import load_rules  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.main(argv)
    return rc, buf.getvalue()


class Contrast(unittest.TestCase):
    def test_wcag_extremes(self):
        self.assertAlmostEqual(mapview.contrast(np.array([0, 0, 0.]), np.array([1, 1, 1.])), 21.0, places=3)
        self.assertAlmostEqual(mapview.contrast(np.array([.5, .5, .5]), np.array([.5, .5, .5])), 1.0, places=6)


class Preview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = load_rules()
        cls.res = Analyzer(cls.rules).scan(os.path.join(FIX, "map_preview"))

    def _findings(self, cal_over=None, out=None):
        cal = sim.load_calibration(None)
        cal.update(cal_over or {})
        return mapview.preview_scenarios(self.res, self.rules, cal, out)

    def test_normal_grid_is_fine_pale_grid_is_flagged(self):
        _, f = self._findings()
        sim1 = [x for x in f if x[0] == "MAPSIM001"]
        self.assertTrue(any("PaleGrid" in x[2] and x[1] == "warning" for x in sim1), sim1)
        # the default-style RscMapControl (ACE-like colours) must not produce a warning
        self.assertFalse(any("[RscMapControl]" in x[2] and x[1] == "warning" for x in sim1), sim1)

    def test_post_process_findings_depend_on_whether_pp_reaches_the_map(self):
        sev = lambda cal: sorted({x[1] for x in self._findings(cal)[1] if x[0] == "MAPSIM002"})
        self.assertEqual(sev({"pp_on_map": None}), ["info"])        # unknown: never more than info
        self.assertEqual(sev({"pp_on_map": True}), ["warning"])
        self.assertEqual(sev({"pp_on_map": False}), [])             # screenshots said the map is untouched

    def test_preview_images_are_written(self):
        with tempfile.TemporaryDirectory() as d:
            self._findings(out=d)
            pngs = sorted(os.listdir(d))
            self.assertTrue(any(p.endswith("_pp_0.png") for p in pngs), pngs)
            self.assertTrue(any(p.startswith("map_01") for p in pngs), pngs)

    def test_grid_labels_come_from_the_terrain_config(self):
        gm = self.res.grid_models[0]
        labels, note = mapview.grid_label_funcs(gm, mapview.pick_zoom(gm, None))
        self.assertIn("preview_world", note)
        self.assertEqual(labels["x"](0), "025")    # map centre 2560 m / 100 m
        self.assertEqual(labels["y"](3), "025")    # row 3 is the centre row
        self.assertEqual(labels["y"](0), "028")    # numbers rise to the north: the top row is the highest


class Commands(unittest.TestCase):
    def test_layers_json(self):
        rc, out = run(["layers", os.path.join(FIX, "ui_layers"), "--format", "json"])
        self.assertEqual(rc, 0)
        rows = json.loads(out)
        self.assertTrue(any(r["layer"] == "layer 135471" for r in rows))

    def test_layers_text_mentions_the_map(self):
        rc, out = run(["layers", os.path.join(FIX, "ui_layers")])
        self.assertIn("stay visible when the map is opened", out)

    def test_grid_json_and_text(self):
        rc, out = run(["grid", os.path.join(FIX, "map_grid_ok"), "--world", "abc_sample", "--format", "json"])
        g = json.loads(out)[0]
        self.assertEqual(g["zooms"][0]["corners"]["NE"], "051 051")
        rc, out = run(["grid", os.path.join(FIX, "map_grid_ok"), "--world", "pmc_40k"])
        self.assertIn("409 409", out)

    def test_map_command_runs(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run(["map", os.path.join(FIX, "map_preview"), "--out", d])
            self.assertEqual(rc, 0)
            self.assertIn("unknown", out)
            self.assertIn("PaleGrid", out)

    @staticmethod
    def _read(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    def test_map_pp_decides_from_two_screenshots(self):
        from PIL import Image
        scene, _ = sim.make_scene()
        with tempfile.TemporaryDirectory() as d:
            a, b, c = (os.path.join(d, n) for n in ("a.png", "b.png", "c.png"))
            sim._pil(scene).save(a)
            sim._pil(scene).save(b)
            sim._pil(np.clip(scene * 0.5, 0, 1)).save(c)
            cal = os.path.join(d, "cal.json")
            rc, out = run(["map-pp", "--before", a, "--after", b, "--out", cal])
            self.assertIn("does NOT appear", out)
            self.assertFalse(self._read(cal)["pp_on_map"])
            rc, out = run(["map-pp", "--before", a, "--after", c, "--out", cal])
            self.assertIn("IS applied", out)
            self.assertTrue(self._read(cal)["pp_on_map"])

    def test_scan_text_mentions_layers_and_grids(self):
        rc, out = run(["scan", os.path.join(FIX, "ui_layers"), "--no-sim", "--fail-on", "none"])
        self.assertIn("UI layer(s) in use", out)
        rc, out = run(["scan", os.path.join(FIX, "map_grid_ok"), "--no-sim", "--fail-on", "none"])
        self.assertIn("terrain grid(s)", out)


class ExampleMod(unittest.TestCase):
    """examples/bad_mod is the demo for every rule family; keep it honest."""

    @classmethod
    def setUpClass(cls):
        cls.res = Analyzer(load_rules()).scan(os.path.join(ROOT, "examples", "bad_mod"))
        cls.rules = {f.rule for f in cls.res.findings}

    def test_every_new_family_is_demonstrated(self):
        for want in ("UI001", "UI003", "UI005", "UI006", "UI009", "UI014", "UI016",
                     "MAP001", "MAP002", "MAP003", "MAP006", "MAPUI001", "MAPUI003"):
            self.assertIn(want, self.rules)

    def test_layer_collision_is_the_cross_addon_one(self):
        hits = [f for f in self.res.findings if f.rule == "UI001"]
        self.assertEqual(len(hits), 1, hits)
        self.assertEqual(hits[0].sev, "warning")
        self.assertIn("layer 1", hits[0].message)

    def test_layer_and_grid_tables_are_filled(self):
        self.assertGreaterEqual(len(self.res.layers), 5)
        self.assertEqual(len(self.res.grids), 1)

    def test_map_preview_adds_findings_through_scan(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run(["scan", os.path.join(ROOT, "examples", "bad_mod"), "--fail-on", "none",
                           "--format", "json", "--sim-out", d])
        rules = {f["rule"] for f in json.loads(out)["findings"]}
        self.assertIn("MAPSIM001", rules)


if __name__ == "__main__":
    unittest.main()
