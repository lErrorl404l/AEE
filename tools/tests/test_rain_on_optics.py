#!/usr/bin/env python3
"""Rain-on-optics accumulation against the engine rain unit (issue #257).

fnc_calculateRainOnOptics.sqf accumulates lens droplets.  Its thresholds are
mm/h.  The engine ``rain`` command returns a 0..1 level, not a rate (Arma 3
wiki; tools/arma3-wiki/commands-reference.md), so the function must convert
the level before the comparison.  The optics module owns the conversion:
fnc_calculatePrecipitationVisibility.sqf scales the level with
``_rainRate * 25`` (1.0 engine rain = 25 mm/h, heavy rain).

The conversion, the gate, the branch thresholds, the branch divisors and the
accumulation default are read from the SQF source, so this suite fails while
the engine level is compared against the mm/h thresholds directly.

Run: python3 -m unittest tools.tests.test_rain_on_optics
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SENSOR = REPO / "addons" / "optics" / "functions" / "sensor"
OPTICS_FN = SENSOR / "fnc_calculateRainOnOptics.sqf"
MAPPING_FN = SENSOR / "fnc_calculatePrecipitationVisibility.sqf"

CONVERSION_RE = re.compile(r"private _rainMMH = _rainRate \* ([0-9.]+|ENGINE_RAIN_FULL_MMH);")
CONSTANTS = REPO / "addons" / "lib" / "constants.hpp"


def _engine_rain_full_mmh() -> float:
    match = re.search(r"#define ENGINE_RAIN_FULL_MMH ([0-9.]+)", CONSTANTS.read_text(encoding="utf-8"))
    assert match is not None, "constants.hpp must define ENGINE_RAIN_FULL_MMH"
    return float(match.group(1))
GATE_RE = re.compile(r"if \(_rainMMH > ([0-9.]+)\) then")
BRANCH_RE = re.compile(
    r"case \(_rainMMH > ([0-9.]+)\):\s*\{\s*_droplets = _droplets \+ "
    r"\(?_accumRate(?: / ([0-9.]+))?\)?;\s*\};"
)
DEFAULT_RE = re.compile(
    r"default\s*\{\s*_droplets = _droplets \+ \(_accumRate / ([0-9.]+)\);\s*\};"
)
ACCUM_DEFAULT_RE = re.compile(r"\[QGVAR\(rainAccumRate\), ([0-9.]+)\]")


def source() -> str:
    return OPTICS_FN.read_text(encoding="utf-8")


def conversion(src: str) -> float:
    """Engine rain level -> mm/h factor, from the function source."""
    match = CONVERSION_RE.search(src)
    assert match is not None, (
        "fnc_calculateRainOnOptics compares the engine 0..1 rain level against "
        "mm/h thresholds with no conversion (issue #257)"
    )
    token = match.group(1)
    return _engine_rain_full_mmh() if token == "ENGINE_RAIN_FULL_MMH" else float(token)


def branches(src: str) -> tuple[float, list[tuple[float, float]], float]:
    """(gate mm/h, [(threshold mm/h, accum divisor)], default divisor)."""
    gate = GATE_RE.search(src)
    assert gate is not None, "the gate must test the mm/h rate (_rainMMH)"
    cases = [
        (float(threshold), float(divisor) if divisor else 1.0)
        for threshold, divisor in BRANCH_RE.findall(src)
    ]
    assert cases, "the switch must keep its mm/h case thresholds"
    default = DEFAULT_RE.search(src)
    assert default is not None, "the switch must keep its default branch"
    return float(gate.group(1)), cases, float(default.group(1))


def accumulation(src: str, engine_rain: float, interval_scale: float = 1.0) -> float:
    """Droplets added this tick, mirroring the function's branch chain."""
    rate_mmh = engine_rain * conversion(src)
    gate, cases, default_divisor = branches(src)
    accum_default = float(ACCUM_DEFAULT_RE.search(src).group(1))
    accum_rate = accum_default * interval_scale
    if rate_mmh <= gate:
        return 0.0
    for threshold, divisor in cases:
        if rate_mmh > threshold:
            return accum_rate / divisor
    return accum_rate / default_divisor


class TestRainUnitConversion(unittest.TestCase):
    def test_the_scale_matches_the_optics_precipitation_mapping(self):
        theirs = conversion(MAPPING_FN.read_text(encoding="utf-8"))
        self.assertEqual(conversion(source()), theirs)

    def test_branch_thresholds_are_reachable_at_full_scale(self):
        # The engine level tops out at 1.0, so a mm/h threshold above the
        # full-scale rate can never fire.
        src = source()
        full_scale_mmh = conversion(src)
        _gate, cases, _default = branches(src)
        for threshold, _divisor in cases:
            self.assertLess(
                threshold,
                full_scale_mmh,
                f"the {threshold} mm/h threshold is above the {full_scale_mmh} "
                "mm/h full scale, so the branch is unreachable",
            )


class TestBranchSelection(unittest.TestCase):
    def test_heavy_rain_takes_the_heavy_branch(self):
        src = source()
        heavy = accumulation(src, 1.0)
        self.assertGreater(heavy, 0.0)
        # 0.5 engine rain is 12.5 mm/h on the 25 mm/h full scale: heavy rain.
        self.assertEqual(accumulation(src, 0.5), heavy)

    def test_moderate_rain_takes_the_moderate_branch(self):
        src = source()
        heavy = accumulation(src, 1.0)
        moderate = accumulation(src, 0.1)  # 2.5 mm/h
        self.assertGreater(moderate, 0.0)
        self.assertEqual(moderate, heavy / 2)

    def test_light_rain_takes_the_light_branch(self):
        src = source()
        light = accumulation(src, 0.02)  # 0.5 mm/h
        self.assertGreater(light, 0.0)
        self.assertEqual(light, accumulation(src, 1.0) / 5)

    def test_dry_weather_accumulates_nothing(self):
        self.assertEqual(accumulation(source(), 0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
