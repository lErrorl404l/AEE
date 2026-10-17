#!/usr/bin/env python3
"""The screenshot differential contract (tools/validation/compare_screens.py).

Pins the metric the visual QA pass relies on: a baseline render and a candidate
render of the same pinned scene must differ by a known fraction of pixels, and
the change grid must localise the difference.  Synthetic images only, so the
suite runs with no captured screenshots.

Run: python3 -m unittest tools.tests.test_compare_screens
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    from PIL import Image

    _DEPS = True
except ImportError:  # pragma: no cover - exercised where numpy/Pillow are absent
    _DEPS = False

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "validation" / "compare_screens.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("compare_screens", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_png(path: Path, array) -> None:
    Image.fromarray(array.astype("uint8"), "RGB").save(path)


def run(module, argv):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = module.main(argv)
    return code, buffer.getvalue()


@unittest.skipUnless(_DEPS, "numpy and Pillow not installed (pip install numpy pillow)")
class TestCompareScreens(unittest.TestCase):
    def setUp(self):
        self.module = load_tool()
        self.dir = Path(tempfile.mkdtemp(prefix="aee_screens_"))

    def _pair(self, baseline, candidate, name="pair"):
        base_path = self.dir / f"{name}_base.png"
        cand_path = self.dir / f"{name}_cand.png"
        write_png(base_path, baseline)
        write_png(cand_path, candidate)
        return base_path, cand_path

    def test_identical_renders_report_zero_change(self):
        image = np.zeros((64, 64, 3))
        base, cand = self._pair(image, image.copy())
        code, out = run(
            self.module,
            ["--label", "map", "--baseline", str(base), "--candidate", str(cand)],
        )
        self.assertEqual(code, 0)
        self.assertIn("changed fraction=0.0000", out)

    def test_a_changed_block_is_measured_and_localised(self):
        baseline = np.zeros((64, 64, 3))
        candidate = baseline.copy()
        candidate[0:16, 0:16] = 255
        base, cand = self._pair(baseline, candidate)
        code, out = run(
            self.module,
            [
                "--label",
                "map",
                "--baseline",
                str(base),
                "--candidate",
                str(cand),
                "--grid",
                "4",
            ],
        )
        self.assertEqual(code, 0)
        # 16x16 of 64x64 is one sixteenth of the pixels.
        self.assertIn("changed fraction=0.0625", out)
        grid = [line for line in out.splitlines() if line.startswith("[map]   ")]
        self.assertEqual(len(grid), 4)
        self.assertTrue(grid[0].strip().endswith("9000"), grid)

    def test_the_expected_change_floor_fails_a_near_zero_delta(self):
        image = np.zeros((32, 32, 3))
        base, cand = self._pair(image, image.copy())
        code, out = run(
            self.module,
            [
                "--label",
                "lighting",
                "--baseline",
                str(base),
                "--candidate",
                str(cand),
                "--expect-change",
                "0.02",
            ],
        )
        self.assertEqual(code, 1)
        self.assertIn("[FAIL]", out)

    def test_the_expected_change_floor_passes_a_real_change(self):
        baseline = np.zeros((64, 64, 3))
        candidate = baseline.copy()
        candidate[0:32, :] = 128
        base, cand = self._pair(baseline, candidate)
        code, _ = run(
            self.module,
            [
                "--label",
                "map",
                "--baseline",
                str(base),
                "--candidate",
                str(cand),
                "--expect-change",
                "0.4",
            ],
        )
        self.assertEqual(code, 0)

    def test_a_size_mismatch_is_refused(self):
        base, _ = self._pair(np.zeros((32, 32, 3)), np.zeros((32, 32, 3)), "a")
        _, cand = self._pair(np.zeros((16, 16, 3)), np.zeros((16, 16, 3)), "b")
        code, _ = run(
            self.module,
            ["--label", "map", "--baseline", str(base), "--candidate", str(cand)],
        )
        self.assertEqual(code, 1)

    def test_the_crop_region_is_honoured(self):
        baseline = np.zeros((64, 64, 3))
        candidate = baseline.copy()
        candidate[0:8, 0:8] = 255
        base, cand = self._pair(baseline, candidate)
        code, out = run(
            self.module,
            [
                "--label",
                "map",
                "--baseline",
                str(base),
                "--candidate",
                str(cand),
                "--crop",
                "32,32,16,16",
            ],
        )
        self.assertEqual(code, 0)
        # The changed block is outside the crop, so nothing changed inside it.
        self.assertIn("changed fraction=0.0000", out)

    def test_the_dominant_colours_are_reported(self):
        image = np.zeros((32, 32, 3))
        image[:, :] = (200, 40, 30)
        base, cand = self._pair(image, image.copy())
        _, out = run(
            self.module,
            ["--label", "palette", "--baseline", str(base), "--candidate", str(cand)],
        )
        self.assertIn("#c82818:1.00", out)


if __name__ == "__main__":
    unittest.main()
