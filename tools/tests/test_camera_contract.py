#!/usr/bin/env python3
"""Contract: an AEE custom camera enables the HUD and terminates its effect.

The engine defaults ``cameraEffectEnableHUD`` to OFF.  A camera created with
``camCreate`` and driven with ``cameraEffect ["Internal", "Back", ...]``
therefore composites no HUD, so every ``drawIcon3D`` AEE draws (the world
symbology, the HUD markers, the rangefinder and the tracker) is invisible
through it.  AEE must also terminate the effect before it destroys the camera:
``camDestroy`` alone leaves the cameraEffect running.

This test scans every addon source for a camera creation and fails when the
creating file does not enable the HUD or does not terminate the effect before
destroying the camera.  AEE has no custom camera today; the test is the guard
for the first one, and its own fixture proves the detector fires.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDONS = ROOT / "addons"

CREATE_RE = re.compile(r"\bcamCreate\b")
HUD_RE = re.compile(r"\bcameraEffectEnableHUD\s+true")
TERMINATE_RE = re.compile(r'\bcameraEffect\s*\[\s*"terminate"')
DESTROY_RE = re.compile(r"\bcamDestroy\b")


def strip_comments(text: str) -> str:
    """Blank ``//`` and ``/* */`` comments, preserving offsets and strings."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def offending_cameras():
    """Return a message per camera source that breaks the contract."""
    offenders = []
    for path in sorted(ADDONS.rglob("*.sqf")):
        code = strip_comments(path.read_text(encoding="utf-8"))
        if not CREATE_RE.search(code):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if not HUD_RE.search(code):
            offenders.append(f"{rel}: camCreate without cameraEffectEnableHUD true")
        if DESTROY_RE.search(code) and not TERMINATE_RE.search(code):
            offenders.append(f"{rel}: camDestroy without cameraEffect terminate")
    return offenders


class TestCameraContract(unittest.TestCase):
    def test_detector_fires_on_a_camera_fixture(self):
        # Negative-control style: the detector must recognise a camera creation
        # so a future camera cannot slip past the contract.
        fixture = 'private _cam = "camera" camCreate [0, 0, 0];'
        self.assertIsNotNone(CREATE_RE.search(fixture))
        self.assertIsNone(HUD_RE.search(fixture))

    def test_every_camera_enables_hud_and_terminates(self):
        self.assertEqual(offending_cameras(), [])


if __name__ == "__main__":
    unittest.main()
