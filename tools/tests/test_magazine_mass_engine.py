"""Tests for the emitted CfgMagazines mass and its consumer (Task 4).

Three properties:
  * the generator emits a mass for a known magazine;
  * the generator emits no mass for a magazine with no held mass;
  * the emitted config mass agrees with the scripted resolver
    (fnc_getMagazineMass empty mass plus the fnc_getMagazineLoad round tiers),
    so the engine mass and the AEE load model never diverge.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
MAG_HPP = REPO / "addons" / "ballistics" / "generated" / "CfgMagazines.hpp"
MASS_SQF = (
    REPO / "addons" / "clothing" / "functions" / "clothing" / "fnc_getMagazineMass.sqf"
)
LOAD_SQF = (
    REPO / "addons" / "clothing" / "functions" / "clothing" / "fnc_getMagazineLoad.sqf"
)

# The emitted mass is the loaded-mass median; the resolver is the empty-mass
# median plus the round tier. The two agree for the pure-derived groups and
# differ only where a published loaded value shifts the median. 20 g covers
# the widest observed spread (4.7 g on 20Rnd_762x51_Mag).
TOLERANCE_KG = 0.02


def _emitted_mass() -> dict[str, float]:
    text = MAG_HPP.read_text(encoding="utf-8")
    out: dict[str, float] = {}
    for match in re.finditer(
        r"class (\w+): \w+ \{\n\s+initSpeed = [\d.]+;\n\s+mass = ([\d.]+);", text
    ):
        out[match.group(1)] = float(match.group(2))
    return out


def _emitted_classes() -> set[str]:
    text = MAG_HPP.read_text(encoding="utf-8")
    return set(re.findall(r"class (\w+): \w+ \{", text))


def _resolver_tables() -> tuple[
    list[tuple[str, int, float]], dict[int, float], dict[str, float]
]:
    mass_text = MASS_SQF.read_text(encoding="utf-8")
    table = [
        (cal, int(cap), float(value))
        for cal, cap, value in re.findall(
            r'\["([a-z0-9]+)", (\d+), ([\d.]+), \d+\]', mass_text
        )
    ]
    tiers_block = mass_text.split("private _tiers")[1]
    tiers = {
        int(cap): float(value)
        for cap, value in re.findall(r"\[(\d+), (\d+)\]", tiers_block)
    }
    load_text = LOAD_SQF.read_text(encoding="utf-8")
    rounds = {
        token: float(value)
        for token, value in re.findall(
            r'\["([a-z0-9]+)", ([\d.]+)\]',
            load_text.split("_roundTiers")[1].split("];")[0],
        )
    }
    return table, tiers, rounds


def _classname_capacity(class_name: str) -> int:
    lower = class_name.lower()
    marker = lower.find("rnd")
    if marker <= 0:
        return 0
    digits = ""
    index = marker - 1
    while index >= 0 and lower[index].isdigit():
        digits = lower[index] + digits
        index -= 1
    return int(digits) if digits else 0


def _resolver(
    class_name: str,
    table: list[tuple[str, int, float]],
    tiers: dict[int, float],
    rounds: dict[str, float],
) -> float:
    lower = class_name.lower()
    capacity = _classname_capacity(class_name)
    empty = 0.0
    for cal, cap, value in table:
        if cal in lower and cap == capacity:
            empty = value
            break
    if empty == 0.0 and capacity == 0:
        for cal, _cap, value in table:
            if cal in lower:
                empty = value
                break
    if empty == 0.0:
        empty = tiers.get(capacity, 0.0)
    round_g = 0.0
    for token, value in rounds.items():
        if token in lower:
            round_g = value
            break
    return empty / 1000.0 + capacity * round_g / 1000.0


class TestMagazineMassEngine(unittest.TestCase):
    def test_generator_emits_mass_for_known_magazine(self) -> None:
        emitted = _emitted_mass()
        self.assertIn("30Rnd_556x45_Stanag", emitted)
        self.assertAlmostEqual(emitted["30Rnd_556x45_Stanag"], 0.5107, places=4)

    def test_generator_emits_nothing_for_magazine_with_no_mass(self) -> None:
        # 10Rnd_762x54_Mag carries an initSpeed but no loaded mass resolves
        # (no 7.62x54mmR magazine group). It must have no mass key.
        text = MAG_HPP.read_text(encoding="utf-8")
        self.assertIn("class 10Rnd_762x54_Mag:", text)
        block = re.search(
            r"class 10Rnd_762x54_Mag: \w+ \{\n(.*?)\n    \};", text, re.DOTALL
        )
        self.assertIsNotNone(block)
        self.assertIn("initSpeed", block.group(1))
        self.assertNotIn("mass", block.group(1))

    def test_config_mass_agrees_with_scripted_resolver(self) -> None:
        emitted = _emitted_mass()
        self.assertTrue(emitted, "no mass emitted")
        table, tiers, rounds = _resolver_tables()
        for class_name, mass in emitted.items():
            resolved = _resolver(class_name, table, tiers, rounds)
            self.assertLessEqual(
                abs(mass - resolved),
                TOLERANCE_KG,
                f"{class_name}: config {mass} vs resolver {resolved}",
            )


if __name__ == "__main__":
    unittest.main()
