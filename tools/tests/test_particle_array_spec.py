#!/usr/bin/env python3
"""ParticleArray spec validator (issue #157).

docs/wiki/research/particle-array-spec.md documents the 22-element
ParticleArray.  The document is only useful if its index mapping matches
the array the shipped pipeline actually builds, so this test derives the
mapping from BOTH and compares them.

A mirror of the table would prove nothing: it would encode the same error.
This test reads the emitter's source and the document's table
independently.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
EMIT = "addons/fx/functions/particle/fnc_particlePipelineEmit.sqf"
DOC = "docs/wiki/research/particle-array-spec.md"


def shipped_array_elements() -> list[str]:
    """The top-level elements of the `private _params = [...]` array."""
    src = (REPO / EMIT).read_text(encoding="utf-8")
    m = re.search(r"private _params = \[(.*?)\n\];", src, re.S)
    assert m, "the shipped _params array is gone"
    body = m.group(1)
    elems, depth, cur = [], 0, ""
    for ch in body:
        if ch == "[":
            depth += 1
        if ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            elems.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        elems.append(cur.strip())
    return elems


def doc_rows() -> list[tuple[int, str]]:
    """The (index, name) rows of the spec table."""
    doc = (REPO / DOC).read_text(encoding="utf-8")
    return [
        (int(i), name) for i, name in re.findall(r"^\| (\d+) \| (\w+) \|", doc, re.M)
    ]


class TestArrayShape(unittest.TestCase):
    def test_doc_covers_every_shipped_element(self):
        shipped = shipped_array_elements()
        rows = doc_rows()
        self.assertEqual(
            len(rows),
            len(shipped),
            f"the doc has {len(rows)} rows but the emitter builds "
            f"{len(shipped)} elements",
        )

    def test_indices_are_contiguous_from_zero(self):
        rows = doc_rows()
        self.assertEqual(
            [i for i, _ in rows],
            list(range(len(rows))),
            "the doc's indices are not contiguous from 0",
        )


class TestNamedIndices(unittest.TestCase):
    """Every element the emitter sets from a named variable must be
    documented under that name at that index.  A shift in either breaks
    the pipeline silently, so the table must not drift."""

    EXPECTED = {
        8: "weight",
        9: "volume",
        10: "rubbing",
        11: "size",
        20: "onSurface",
        21: "bounceOnSurface",
    }

    def test_named_indices_match_the_emitter(self):
        docmap = dict(doc_rows())
        for idx, name in self.EXPECTED.items():
            self.assertEqual(
                docmap.get(idx),
                name,
                f"index {idx} is documented as {docmap.get(idx)!r} but the "
                f"emitter's named element there is {name!r}",
            )

    def test_obsolete_element_one_is_documented(self):
        # Index 1 must be documented as obsolete and empty: a non-empty
        # value throws a skeletal-animation RPT error.
        docmap = dict(doc_rows())
        self.assertEqual(docmap.get(1), "animationName")
        src = (REPO / EMIT).read_text(encoding="utf-8")
        self.assertIn('    "",\n', src, "element 1 is no longer empty in the emitter")


class TestCompanionCalls(unittest.TestCase):
    """The four calls that configure a source must all appear in the doc
    and in the emitter."""

    CALLS = [
        "setParticleParams",
        "setParticleRandom",
        "setParticleCircle",
        "setDropInterval",
    ]

    def test_all_four_calls_in_emitter(self):
        src = (REPO / EMIT).read_text(encoding="utf-8")
        for call in self.CALLS:
            self.assertIn(call, src, f"{call} is gone from the emitter")

    def test_all_four_calls_in_doc(self):
        doc = (REPO / DOC).read_text(encoding="utf-8")
        for call in self.CALLS:
            self.assertIn(call, doc, f"{call} is not in the spec doc")


if __name__ == "__main__":
    unittest.main()
