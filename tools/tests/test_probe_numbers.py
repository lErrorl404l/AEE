"""The Docker probe numbers must be unique across the harness.

Each mission probe reports with its own ``[P<n>]`` tag and ``verify.py`` gates
on one named PASS line per probe.  Three workers picked overlapping numbers in
parallel (P115 eye, P116 engine override, P117 map defects), so this test fails
if any two phases share a number.  It guards both the expected-PASS list and the
FAIL regex in ``verify.py``, and the ``execVM`` list in the mission.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
VERIFY = ROOT / "tests" / "docker" / "verify.py"
INIT = ROOT / "tests" / "docker" / "missions" / "aee_test.Stratis" / "init.sqf"

_EXPECTED = re.compile(r'"\[P([0-9A-Za-z]+)\] \[PASS\]"')
_FAIL_REGEX = re.compile(r"P\(\?:([0-9A-Za-z|]+)\)")
_EXECVM = re.compile(r'execVM "aee_p(\d+)_')


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    dupes: list[str] = []
    for value in values:
        if value in seen and value not in dupes:
            dupes.append(value)
        seen.add(value)
    return dupes


class TestProbeNumbers(unittest.TestCase):
    def test_expected_pass_numbers_unique(self) -> None:
        numbers = _EXPECTED.findall(VERIFY.read_text(encoding="utf-8"))
        self.assertTrue(numbers, "no probe PASS expectations found in verify.py")
        self.assertEqual(_duplicates(numbers), [], "duplicate probe PASS numbers")

    def test_fail_regex_numbers_unique(self) -> None:
        match = _FAIL_REGEX.search(VERIFY.read_text(encoding="utf-8"))
        self.assertIsNotNone(match, "the probe FAIL regex was not found in verify.py")
        numbers = match.group(1).split("|")
        self.assertEqual(
            _duplicates(numbers), [], "duplicate numbers in the FAIL regex"
        )

    def test_fail_regex_numbers_have_a_pass_expectation(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        expected = set(_EXPECTED.findall(text))
        match = _FAIL_REGEX.search(text)
        self.assertIsNotNone(match, "the probe FAIL regex was not found in verify.py")
        unknown = sorted(n for n in match.group(1).split("|") if n not in expected)
        self.assertEqual(unknown, [], "FAIL regex numbers with no PASS expectation")

    def test_execvm_numbers_unique(self) -> None:
        numbers = _EXECVM.findall(INIT.read_text(encoding="utf-8"))
        self.assertTrue(numbers, "no probe execVM lines found in init.sqf")
        self.assertEqual(_duplicates(numbers), [], "duplicate probe execVM numbers")


if __name__ == "__main__":
    unittest.main()
