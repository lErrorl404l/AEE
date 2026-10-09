#!/usr/bin/env python3
"""Generate the native kernel parity vectors from the SQF reference kernels.

The SQF kernel is the reference.  This generator evaluates each reference
kernel on a fixed set of vectors with the suite's SQF interpreter
(`tools/tests/sqf_lite.py`) and writes the expected values to a JSON file the
Rust `#[test]` reads.  The expectations are therefore generated from the SQF
reference, never typed by hand.

The per-kernel tolerance is recorded here and justified in ADR-034.  The engine
runs SQF numbers in 32-bit, so a single f32 rounding is about 6e-8 relative;
the default bound is 1e-6 relative.  A kernel whose output is rounded to an
integer carries an absolute bound of one rounding step (0.5).

Run:
    python3 tools/gen_kernel_vectors.py           # write the vectors
    python3 tools/gen_kernel_vectors.py --check   # fail on drift
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools" / "tests"))

from sqf_lite import run_sqf  # noqa: E402

OUT = (
    ROOT / "tools" / "dev-harness" / "extension" / "tests" / "vectors" / "kernels.json"
)

# The relative bound is the f32 default.  The absolute bound covers a kernel
# whose output is rounded to an integer: 0.5 is one rounding step and is the
# smallest meaningful bound for that kernel.  Justified in ADR-034.
KERNELS: tuple[dict, ...] = (
    {
        "name": "stationPressure",
        "command": "kernel.calculateStationPressure",
        "path": "addons/atmos/functions/physics/fnc_calculateStationPressure.sqf",
        "tolerance_rel": 1e-6,
        "tolerance_abs": 0.0,
        "vectors": [
            [1013.25, 0.0, 6.5],
            [1013.25, 1000.0, 6.5],
            [1013.25, 3000.0, 6.5],
            [1020.0, 500.0, 5.0],
            [900.0, 5000.0, 8.0],
            [1013.25, 20000.0, 6.5],
        ],
    },
    {
        "name": "relativeHumidity",
        "command": "kernel.calculateRelativeHumidity",
        "path": "addons/atmos/functions/physics/fnc_calculateRelativeHumidity.sqf",
        "tolerance_rel": 1e-6,
        "tolerance_abs": 0.5,
        "vectors": [
            [50.0, 0.0, 15.0, 15.0, 0.0, 0.0],
            [50.0, 0.0, 20.0, 10.0, 0.0, 0.0],
            [80.0, -15.0, 5.0, 25.0, 0.0, 0.0],
            [70.0, 10.0, 10.0, 20.0, 0.0, 0.0],
            [60.0, 0.0, 15.0, 15.0, 0.8, 0.0],
            [60.0, 0.0, 15.0, 15.0, 0.0, 0.5],
            [0.0, 0.0, 15.0, 15.0, 0.0, 0.0],
            [120.0, 0.0, 15.0, 15.0, 0.0, 0.0],
        ],
    },
    {
        "name": "airDensity",
        "command": "kernel.calculateAirDensityKernel",
        "path": "addons/ballistics/functions/fnc_calculateAirDensityKernel.sqf",
        "tolerance_rel": 1e-6,
        "tolerance_abs": 0.0,
        "vectors": [
            [15.0, 1013.25, 50.0],
            [0.0, 1013.25, 100.0],
            [30.0, 1000.0, 80.0],
            [-40.0, 900.0, 0.0],
            [50.0, 1050.0, 20.0],
        ],
    },
    {
        "name": "solveTwoNode",
        "command": "kernel.solveTwoNodeKernel",
        "path": "addons/thermal/functions/solver/fnc_solveTwoNodeKernel.sqf",
        # The 12-iteration nonlinear fixed point amplifies one f32 engine
        # rounding (about 6e-8) by the Newton gain; the measured engine
        # divergence is of order 1e-5 relative, so the bound is the plan's
        # ceiling, 1e-3, with this written reason (ADR-034).
        "tolerance_rel": 1e-3,
        "tolerance_abs": 0.0,
        "vectors": [
            # human, neutral: core/skin mass, DuBois area, metabolism
            [
                15.0,
                1.0,
                500.0,
                1.0,
                63.0,
                7.0,
                1.8258,
                0.15,
                36.8,
                33.7,
                120.0,
                "vertical",
                0.5,
                15.0,
                True,
                True,
                5.0,
                0.0,
                -273.0,
                0.0,
                1.0,
                0.0,
                1.0,
                0.95,
                0.7,
            ],
            # human, cold and shivering
            [
                0.0,
                5.0,
                0.0,
                1.0,
                63.0,
                7.0,
                1.8258,
                0.15,
                35.0,
                28.0,
                80.0,
                "vertical",
                0.5,
                0.0,
                True,
                True,
                5.0,
                0.0,
                -273.0,
                0.0,
                1.0,
                0.0,
                1.0,
                0.95,
                0.7,
            ],
            # human, rain wettedness
            [
                15.0,
                1.0,
                500.0,
                1.0,
                63.0,
                7.0,
                1.8258,
                0.15,
                36.8,
                33.7,
                120.0,
                "vertical",
                0.5,
                15.0,
                True,
                True,
                5.0,
                0.0,
                -273.0,
                1.0,
                1.0,
                0.0,
                1.0,
                0.95,
                0.7,
            ],
            # human, immersed in still water
            [
                15.0,
                0.0,
                0.0,
                1.0,
                63.0,
                7.0,
                1.8258,
                0.15,
                36.8,
                33.7,
                120.0,
                "vertical",
                0.5,
                15.0,
                True,
                True,
                5.0,
                0.0,
                10.0,
                0.0,
                1.0,
                0.0,
                1.0,
                0.95,
                0.7,
            ],
            # inert vehicle panel, engine heat
            [
                0.0,
                5.0,
                0.0,
                1.0,
                50.0,
                20.0,
                6.0,
                1.5,
                0.0,
                0.0,
                5000.0,
                "vertical",
                0.5,
                0.0,
                False,
                False,
                5.0,
                0.0,
                -273.0,
                0.0,
                1.0,
                0.0,
                1.0,
                0.9,
                0.5,
            ],
            # inert panel, horizontal-up orientation
            [
                20.0,
                2.0,
                800.0,
                0.8,
                100.0,
                30.0,
                10.0,
                2.0,
                25.0,
                25.0,
                2000.0,
                "up",
                0.6,
                20.0,
                False,
                False,
                5.0,
                0.0,
                -273.0,
                0.0,
                1.0,
                0.5,
                5.0,
                0.9,
                0.5,
            ],
        ],
    },
)


def build() -> dict:
    kernels = {}
    for kernel in KERNELS:
        path = ROOT / kernel["path"]
        cases = [
            {"args": args, "expected": run_sqf(path, args)}
            for args in kernel["vectors"]
        ]
        kernels[kernel["name"]] = {
            "command": kernel["command"],
            "path": kernel["path"],
            "tolerance_rel": kernel["tolerance_rel"],
            "tolerance_abs": kernel["tolerance_abs"],
            "vectors": cases,
        }
    return {"kernels": kernels}


def render(data: dict) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail on drift, write nothing"
    )
    args = parser.parse_args()

    block = render(build())
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != block:
            print("kernel vectors: stale (run without --check)")
            return 1
        print(f"kernel vectors: PASS ({len(KERNELS)} kernels)")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(block, encoding="utf-8")
    print(f"kernel vectors: wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
