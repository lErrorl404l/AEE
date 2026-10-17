"""Round-trip tests for `calibrate`: render 'screenshots' with a known model, then check the fit recovers it.

This validates the fitting machinery, NOT the engine. Whether any candidate matches real Arma 3 output can
only be learned from real screenshots (see README, "Calibrating against the real game").
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arma_vqa import cli, sim  # noqa: E402

P1 = [1.2, 1.5, 0.0, [0, 0, 0, 0], [1, 1, 1, 0.6], [0.299, 0.587, 0.114, 0]]
P2 = [0.8, 0.7, 0.05, [0.1, 0.1, 0.3, 0.2], [1.2, 1, 0.9, 1], [0.299, 0.587, 0.114, 0]]


def sqf(p):
    return json.dumps(p)


class Calibrate(unittest.TestCase):
    def _shots(self, d, truth_cal, fx, params_list):
        scene, _ = sim.make_scene()
        before = os.path.join(d, "before.png")
        sim._pil(scene).save(before)
        pairs = []
        for i, p in enumerate(params_list):
            after = os.path.join(d, f"after{i}.png")
            sim._pil(fx(scene, p, truth_cal)).save(after)
            pairs += ["--pair", before, after, sqf(p)]
        return pairs

    def _run(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(argv)
        return rc, buf.getvalue()

    def test_recovers_colorcorrections_model(self):
        truth = dict(sim.DEFAULT_CAL, cc_model="desat_first", cc_pivot=0.5, cc_brightness="multiplicative")
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "cal.json")
            args = ["calibrate", "--effect", "ColorCorrections", "--out", out] + self._shots(d, truth, sim.fx_color_corrections, [P1, P2])
            rc, text = self._run(args)
            self.assertEqual(rc, 0, text)
            with open(out, encoding="utf-8") as f:
                cal = json.load(f)
            self.assertEqual(cal["cc_model"], "desat_first")
            self.assertEqual(cal["cc_pivot"], 0.5)
            self.assertEqual(cal["cc_brightness"], "multiplicative")
            self.assertLess(cal["_fit"]["ColorCorrections"]["mean_abs_error"], 0.01)
            self.assertNotIn("WARNING", text)

    def test_recovers_legacy_model(self):
        truth = dict(sim.DEFAULT_CAL, cc_model="legacy")
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "cal.json")
            args = ["calibrate", "--out", out] + self._shots(d, truth, sim.fx_color_corrections, [P1, P2])
            self._run(args)
            with open(out, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["cc_model"], "legacy")

    def test_recovers_blur_scale(self):
        truth = dict(sim.DEFAULT_CAL, blur_sigma_per_unit=4.0)
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "cal.json")
            args = ["calibrate", "--effect", "DynamicBlur", "--out", out] + self._shots(d, truth, sim.fx_dynamic_blur, [[0.8], [0.4]])
            self._run(args)
            with open(out, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["blur_sigma_per_unit"], 4.0)

    def test_warns_when_no_candidate_fits(self):
        # 'after' is an unrelated image: the tool must say so instead of reporting a confident fit
        import numpy as np
        with tempfile.TemporaryDirectory() as d:
            scene, _ = sim.make_scene()
            before = os.path.join(d, "b.png")
            after = os.path.join(d, "a.png")
            sim._pil(scene).save(before)
            sim._pil(1.0 - scene[::-1]).save(after)
            rc, text = self._run(["calibrate", "--pair", before, after, sqf(P1)])
            self.assertEqual(rc, 0)
            self.assertIn("WARNING", text)

    def test_default_model_does_not_blow_out_the_wiki_black_and_white_example(self):
        # BI's own 'Black & White' example from the ppEffectAdjust page. The old model rendered it ~92% white.
        bw = [1, 0.4, 0, [0, 0, 0, 0], [1, 1, 1, 0], [1, 1, 1, 0]]
        scene, regions = sim.make_scene()
        out = sim.fx_color_corrections(scene, bw, dict(sim.DEFAULT_CAL))
        m = sim.compute_metrics(scene, out, regions)
        self.assertLess(m["clip_high_pct"], 30)
        self.assertGreater(m["levels_remaining"], 200)
        self.assertLess(abs(m["mean_luma_shift"]), 0.2)

    def test_default_parameters_are_identity(self):
        scene, _ = sim.make_scene()
        ident = [1, 1, 0, [0, 0, 0, 0], [1, 1, 1, 1], [0.299, 0.587, 0.114, 0]]
        out = sim.fx_color_corrections(scene, ident, dict(sim.DEFAULT_CAL))
        self.assertLess(float(abs(out - scene).max()), 1e-5)


if __name__ == "__main__":
    unittest.main()
