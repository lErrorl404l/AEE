#!/usr/bin/env python3
"""Regression tests for the core-stack QA fixes (2026-10-08).

F1  addons/blast/XEH_postInit.sqf
    The blast handler called `ace_medical_fnc_addToLog` with no guard.  `fx`
    does not require ACE, and the function actually lives in
    ace_medical_treatment, so the name was wrong even with ACE present.

F2  addons/thermal/functions/ground/fnc_applyGroundContactStamps.sqf
    A tyre temperature was declared `private _wheelTemp = nil` and written
    inside a `forEach` body, then read after it.  A nil initialiser does not
    bind the local in SQF (the repository documents this at
    fnc_getBiome.sqf:41), so the write lands in the block scope and is lost;
    the read after the block sees nil and the tyre stamp never fires.  The
    fix assigns at one scope (findIf + a single read).

F3  README.md
    The Requirements section claimed the core addons are standalone, but
    aee_core calls into the module addons; loading it alone throws.

F4  addons/core/functions/fnc_updateEnvironment.sqf
    A dedicated server has no currentUnit, so _posASL is empty and the
    unguarded `getTerrainHeightASL (_posASL select [0, 2])` receives nothing.

Run: python3 -m unittest tools.tests.test_qa_core_stack -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FX_POSTINIT = ROOT / "addons/blast/XEH_postInit.sqf"
STAMPS = ROOT / "addons/thermal/functions/ground/fnc_applyGroundContactStamps.sqf"
CORE_ENV = ROOT / "addons/core/functions/fnc_updateEnvironment.sqf"
README = ROOT / "README.md"


def source(path):
    return path.read_text(encoding="utf-8")


def code_only(text):
    """Drop // and /* */ comments so a doc mention of a pattern is not a hit."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


class TestFxBlastAceGuard(unittest.TestCase):
    """F1: the blast medical-log call is guarded and names the right function."""

    def test_call_names_the_ace_medical_treatment_function(self):
        text = code_only(source(FX_POSTINIT))
        self.assertNotIn(
            "ace_medical_fnc_addToLog",
            text,
            "ace_medical_fnc_addToLog does not exist; the function is in "
            "ace_medical_treatment",
        )
        self.assertIn("ace_medical_treatment_fnc_addToLog", text)

    def test_call_is_guarded(self):
        text = code_only(source(FX_POSTINIT))
        self.assertRegex(
            text,
            r'!isNil "ace_medical_treatment_fnc_addToLog"',
            "the call must be guarded so a machine without ACE does not throw",
        )


class TestGroundStampWheelRead(unittest.TestCase):
    """F2: the tyre temperature is assigned and read at one scope."""

    def test_nil_initialiser_is_gone(self):
        text = code_only(source(STAMPS))
        self.assertNotIn(
            "private _wheelTemp = nil;",
            text,
            "a nil initialiser does not bind the local, so a nested-block write "
            "is lost",
        )

    def test_no_bare_wheel_temp_assignment(self):
        # The old defect wrote `_wheelTemp = ...` as a bare assignment inside
        # the forEach body.  The fixed form assigns only in the declaration.
        text = code_only(source(STAMPS))
        self.assertIsNone(
            re.search(r"^\s*_wheelTemp = ", text, re.MULTILINE),
            "_wheelTemp must not be assigned from inside a nested block",
        )

    def test_wheel_selection_is_found_at_one_scope(self):
        text = code_only(source(STAMPS))
        self.assertRegex(text, r"_wheelIdx = _wheelNames findIf")
        self.assertRegex(
            text,
            r"if \(_wheelIdx >= 0\) then \{\s*private _wheelTemp = _selTemps getOrDefault",
            "the temperature must be declared and read inside the same block",
        )


class TestNoUnboundLocalWrittenInANestedBlock(unittest.TestCase):
    """F2 class guard: no `private _v = nil` anywhere in the tree.

    The pattern is the root cause of F2 and of the two earlier RPT defects.
    A nil initialiser does not bind, so any later write from a nested block
    creates a block-scoped local and the outer read sees nil.
    """

    def test_no_nil_initialised_local(self):
        pattern = re.compile(r"\bprivate _[A-Za-z0-9_]+ = nil\b")
        hits = []
        for path in sorted((ROOT / "addons").rglob("*.sqf")):
            for i, line in enumerate(source(path).splitlines(), 1):
                if pattern.search(re.sub(r"//.*$", "", line)):
                    hits.append(f"{path.relative_to(ROOT)}:{i}")
        self.assertEqual(
            hits,
            [],
            "a local initialised to nil does not bind in SQF; a later "
            "nested-block write then lands in the block scope and is lost. "
            "Found: " + ", ".join(hits),
        )


class TestCoreReferenceAltitudeGuard(unittest.TestCase):
    """F4: the empty position on a dedicated server is guarded."""

    def test_empty_position_is_guarded_before_the_terrain_query(self):
        text = code_only(source(CORE_ENV))
        self.assertRegex(
            text,
            r"count _posASL >= 2",
            "getTerrainHeightASL must not receive an empty position",
        )
        self.assertRegex(
            text,
            r"getTerrainHeightASL \(_posASL select \[0, 2\]\)",
            "the terrain query is still made when the position is real",
        )


class TestCoreStandaloneReadme(unittest.TestCase):
    """F3: the README does not claim aee_core is standalone."""

    def test_readme_states_the_module_dependency(self):
        text = source(README)
        self.assertNotIn(
            "The core addons are standalone",
            text,
            "aee_core calls into the module addons, so it is not standalone",
        )
        self.assertRegex(text, r"aee_core` calls into the module addons")


if __name__ == "__main__":
    unittest.main()
