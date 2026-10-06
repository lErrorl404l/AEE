#!/usr/bin/env python3
"""FilmGrain colour invariant (aee-workshop-copy item 8).

The sixth element of a FilmGrain parameter array is the monochromatic flag:
BIKI Arma 3 gives 0 as monochrome and any other value as colour (Post Process
Effects, capture 20240220225631).  A 0 drains the whole scene to grey, the
defect fixed at c753730.  This suite pins the invariant across every addon.
It scans every .sqf and .cpp for a grain ppEffectAdjust array, and it also
parses the pure kernels that return a grain array without an adjust call.

Run: python3 -m unittest tools.tests.test_film_grain_invariant -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"

PERCEPTION = ADDONS / "optics" / "functions" / "perception" / "fnc_perceptionParams.sqf"
BASE_GRADE = ADDONS / "optics" / "functions" / "grade" / "fnc_baseGradeParams.sqf"
WEATHER = ADDONS / "optics" / "functions" / "vision" / "fnc_weatherGrainParams.sqf"
TUBE = ADDONS / "nightvision" / "functions" / "fnc_applyNVGTubeModel.sqf"

# The pure kernels return the grain array from a local; the imperative drivers
# feed it to ppEffectAdjust.  Both forms are fixtures.
FIXTURES = (
    (PERCEPTION, r"_grain\s*=\s*"),
    (BASE_GRADE, r"_grainParams\s*=\s*"),
    (WEATHER, r"_params\s*=\s*"),
)

_LINE_COMMENT = re.compile(r"//[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_GRAIN_ADJUST = r"\b\w*[Gg]rain\w*\s+ppEffectAdjust\s*"


def live_source(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


def split_top_level(body: str) -> list[str]:
    """Split on commas that are not inside brackets."""
    parts: list[str] = []
    depth = 0
    cur = ""
    for ch in body:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def arrays_after(text: str, pattern: str):
    """Yield the body of each top-level bracket array after a pattern match."""
    for match in re.finditer(pattern, text):
        start = text.find("[", match.end())
        if start < 0:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    yield text[start + 1 : i]
                    break


def sixth_element(body: str):
    parts = split_top_level(body)
    if len(parts) != 6:
        return None
    return parts[5].strip()


def is_monochrome(token: str) -> bool:
    """True only for a numeric zero.  `true` is not numeric and is out of
    scope: the one array that carries it runs at intensity 0."""
    try:
        return float(token) == 0.0
    except ValueError:
        return False


def collected():
    """Every FilmGrain array as (relative path, sixth element token)."""
    found: list[tuple[str, str]] = []
    paths = sorted(ADDONS.rglob("*.sqf")) + sorted(ADDONS.rglob("*.cpp"))
    for path in paths:
        text = live_source(path)
        if "ppEffectAdjust" not in text:
            continue
        for body in arrays_after(text, _GRAIN_ADJUST):
            sixth = sixth_element(body)
            if sixth is not None:
                found.append((str(path.relative_to(REPO)), sixth))
    for path, pattern in FIXTURES:
        for body in arrays_after(live_source(path), pattern):
            sixth = sixth_element(body)
            if sixth is not None:
                found.append((str(path.relative_to(REPO)), sixth))
    return found


FOUND = collected()


class TestFilmGrainColourInvariant(unittest.TestCase):
    """Every FilmGrain array keeps a colour sixth element."""

    def test_at_least_four_arrays_are_found(self):
        self.assertGreaterEqual(len(FOUND), 4, FOUND)

    def test_no_grain_array_is_monochrome(self):
        monochrome = [(p, s) for p, s in FOUND if is_monochrome(s)]
        self.assertEqual(monochrome, [], f"monochrome grain arrays: {monochrome}")

    def test_the_named_sources_are_present(self):
        paths = {p for p, _ in FOUND}
        for named in (PERCEPTION, BASE_GRADE, WEATHER, TUBE):
            with self.subTest(path=named):
                self.assertIn(str(named.relative_to(REPO)), paths)

    def test_the_tube_model_grain_is_colour(self):
        tokens = [s for p, s in FOUND if p == str(TUBE.relative_to(REPO))]
        self.assertTrue(tokens, "the NVG tube grain array was not found")
        for token in tokens:
            with self.subTest(token=token):
                self.assertFalse(is_monochrome(token))


if __name__ == "__main__":
    unittest.main()
