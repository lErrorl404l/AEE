#!/usr/bin/env python3
"""Vendored Arma 3 visual QA (arma_vqa) as a repository gate.

Runs the static analyser over addons/: post-process effect names, parameter
arities and ranges, priority collisions, commit and enable lifecycle, night
vision and thermal commands, PiP and camera commands, and the optics config.

The tool and its rule database are vendored under tools/arma_vqa/. The
offline renderer is off: it needs a calibration against real screenshots and
its findings are model-based, so it stays a manual tool.

Exits non-zero on any finding of severity `error`. Warnings and info print
but do not fail the gate.

Run: python3 tools/validation/validate_visual_stack.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "arma_vqa"
ADDONS = REPO / "addons"


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "arma_vqa",
        "scan",
        str(ADDONS),
        "--no-sim",
        "--format",
        "md",
        "--min-severity",
        "warning",
        "--fail-on",
        "error",
    ]
    return subprocess.run(command, cwd=TOOL, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
