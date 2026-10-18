#!/usr/bin/env python3
"""Module-ownership gate checks on the environment tick (issues #288, #296).

A computed quantity must be gated by the module that owns it, never by an
unrelated module's toggle.  Two calls in fnc_updateEnvironment.sqf broke that
rule:

  - calculateSeaSurfaceTemperature sat inside the radio-propagation gate, so
    with radio off the maritime SST (and the internal-wave and acoustics state
    derived from it) stayed at the default 15 C (#296);
  - calculateCompassDeviation sat inside the maritime gate, so with Maritime
    off the declination rose read 0 for the whole mod (#288).

These tests recover the enclosing `if (...) then {` conditions of each call
site, so a later edit that re-nests either call under the foreign toggle fails
here.  The counter block nesting is checked too, because the SST call moved out
of the radio counter.

Run: python3 -m unittest tools.tests.test_env_tick_gates
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TICK = REPO / "addons" / "core" / "functions" / "fnc_updateEnvironment.sqf"

_SST = "EFUNC(maritime,calculateSeaSurfaceTemperature)"
_COMPASS = "EFUNC(magnetism,calculateCompassDeviation)"
_RADIO_INDEX = "EFUNC(radio,calculateRadioPropagation)"

_IF_RE = re.compile(r"^if\s*\((.*)\)\s*then\s*\{")
_COUNTER_RE = re.compile(r"(BEGIN|END)_COUNTER\((\w+)\)")


def _mask(line):
    """Blank string literals and //-comments, so their braces do not count."""
    line = re.sub(r'"[^"]*"', '""', line)
    return re.sub(r"//.*$", "", line)


def guards_at(text, needle):
    """Enclosing if-conditions of the line that contains `needle`, outermost
    first.  A condition that spans lines, or an unguarded block, yields None."""
    stack = []
    for raw in text.splitlines():
        line = _mask(raw)
        if needle in line:
            return list(stack)
        net = line.count("{") - line.count("}")
        if net > 0:
            match = _IF_RE.match(line.strip())
            guard = match.group(1) if match else None
            stack.extend([guard] + [None] * (net - 1))
        elif net < 0:
            for _ in range(-net):
                if stack:
                    stack.pop()
    raise AssertionError(f"{needle} not found in {TICK.name}")


class TestProducerGates(unittest.TestCase):
    """Each quantity has one producer, gated by its owner."""

    def setUp(self):
        self.text = TICK.read_text(encoding="utf-8")

    def test_sst_is_gated_by_maritime_not_radio(self):
        guards = " ".join(str(g) for g in guards_at(self.text, _SST))
        self.assertIn("maritimeEnabled", guards)
        self.assertNotIn("radioPropagationEnabled", guards)

    def test_compass_deviation_is_not_gated_by_maritime(self):
        guards = " ".join(str(g) for g in guards_at(self.text, _COMPASS))
        self.assertNotIn("maritimeEnabled", guards)
        self.assertNotIn("radioPropagationEnabled", guards)

    def test_each_quantity_has_one_producer(self):
        self.assertEqual(self.text.count(_SST), 1)
        self.assertEqual(self.text.count(_COMPASS), 1)

    def test_sst_precedes_the_propagation_index(self):
        # The evaporation-duct feed must be fresh when the index is computed.
        self.assertLess(self.text.index(_SST), self.text.index(_RADIO_INDEX))


class TestCounterAccounting(unittest.TestCase):
    """The hoisted SST call must leave the counter blocks balanced."""

    def test_counters_are_balanced_and_nested(self):
        stack = []
        for raw in TICK.read_text(encoding="utf-8").splitlines():
            for kind, name in _COUNTER_RE.findall(_mask(raw)):
                if kind == "BEGIN":
                    stack.append(name)
                else:
                    self.assertTrue(stack, f"END_COUNTER({name}) with no open block")
                    self.assertEqual(stack.pop(), name)
        self.assertEqual(stack, [], "unclosed BEGIN_COUNTER block")


if __name__ == "__main__":
    unittest.main()
