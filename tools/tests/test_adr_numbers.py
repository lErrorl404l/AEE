#!/usr/bin/env python3
"""The ADR records must carry unique, gap-free numbers.

Each record is ``docs/adr/ADR-NNN-<slug>.md``.  Two records once claimed
number 029 (``ADR-029-map-legibility...`` and ``ADR-029-marker-derivation...``)
because nothing checked uniqueness.  A gap is the same defect in reverse: it
hides a deleted or mis-numbered record.

Discovery is by glob, not by memory.  This test fails on a duplicate number or
a gap in the sequence, until the exception sits on the allowlist below with a
reason.

Run: python3 -m unittest tools.tests.test_adr_numbers
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADR_DIR = REPO / "docs" / "adr"

# ADR number -> reason.  A deliberate gap or duplicate must be justified here.
# The sequence is unique and gap-free apart from an allowlisted number.
ALLOWLIST: dict[int, str] = {
    # ADR-038 is reserved by the map-realism plan, which lands on main as a
    # separate branch. The gap closes when the two branches merge.
    38: "reserved by the map-realism plan; lands on main as a separate branch",
    39: "reserved by the aircraft-catalogue-expansion plan (ADR-039); landed separately.",
}
}

_ADR = re.compile(r"^ADR-(\d{3})-[A-Za-z0-9]")


def _numbers() -> list[int]:
    numbers = []
    for path in ADR_DIR.glob("ADR-*.md"):
        match = _ADR.match(path.name)
        if match:
            numbers.append(int(match.group(1)))
    return sorted(numbers)


def _duplicates(values: list[int]) -> list[int]:
    seen: set[int] = set()
    duplicate = []
    for value in values:
        if value in seen and value not in duplicate:
            duplicate.append(value)
        seen.add(value)
    return duplicate


class TestAdrNumbers(unittest.TestCase):
    def test_adr_directory_is_not_empty(self):
        self.assertTrue(_numbers(), "no docs/adr/ADR-NNN-*.md records found")

    def test_adr_numbers_are_unique(self):
        duplicate = [n for n in _duplicates(_numbers()) if n not in ALLOWLIST]
        self.assertEqual(
            duplicate,
            [],
            "duplicate ADR numbers: " + ", ".join(f"{n:03d}" for n in duplicate),
        )

    def test_adr_sequence_is_gap_free(self):
        numbers = _numbers()
        if not numbers:
            self.skipTest("no ADR records")
        present = set(numbers)
        expected = set(range(numbers[0], numbers[-1] + 1))
        gap = sorted(n for n in expected - present if n not in ALLOWLIST)
        self.assertEqual(
            gap, [], "gaps in the ADR sequence: " + ", ".join(f"{n:03d}" for n in gap)
        )

    def test_the_allowlist_has_a_reason_for_every_entry(self):
        for number, reason in ALLOWLIST.items():
            self.assertTrue(
                reason.strip(), f"ADR-{number:03d} allowlist entry has no reason"
            )


if __name__ == "__main__":
    unittest.main()
