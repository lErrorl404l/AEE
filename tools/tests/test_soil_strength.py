"""Fail-closed soil-strength contract for fnc_calculateSoilStrength (issue #117).

The live function publishes no numeric soil result. The real-world vehicle
inputs and the VCI50 prediction source are unverified. The function returns
`[false, reason]` and publishes an explicit unknown state.

This suite tests only that contract. The verified NRMM research (RCI, the
wheeled Mobility Index, VCI1) belongs in its own research suite, not here.

Reason vocabulary, closed: `null`, `tracked`, `unverifiedInputs`.

Runtime coverage is out of scope. The SQF harness (tools/tests/sqf_lite.py)
cannot execute this function. It resolves only the thermal-solver subset
and has no evaluator for missionNamespace, setVariable, QGVAR, objNull,
nil, isNull or isKindOf. The argument-safety tests read the live body and
prove the ordering and the guards. Replace them with a runtime call when
the harness gains those commands.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOIL = ROOT / "addons" / "mobility" / "functions" / "fnc_calculateSoilStrength.sqf"

REASON_TOKENS = frozenset({"null", "tracked", "unverifiedInputs"})

KNOWN_VAR = "QGVAR(currentSoilStrengthKnown)"
REASON_VAR = "QGVAR(currentSoilStrengthReason)"
CLEARED_VARS = ("currentVCI1", "currentVCI50", "currentMobilityIndex")

# The published constant forms of the quarantined model. None may appear.
FORMULA_CONSTANTS = (
    "28.23",
    "0.43",
    "92.67",
    "3.67",
    "11.48",
    "39.2",
    "2.14",
    "4.1",
    "0.446",
    "0.553",
    "0.033",
    "1.050",
    "0.142",
    "0.278",
    "0.420",
    "3.115",
)

# Class-table keys and numeric private values removed from the live path.
CLASS_KEYS = ('"MRAP"', '"Wheeled_APC"', '"Car"', '"Truck"')
NUMERIC_IDENTIFIERS = (
    "_vci1",
    "_vci50",
    "_mi",
    "_passes50",
    "_passes1",
    "_cpf",
    "_tef",
    "_wlf",
    "_cf",
    "_wf",
    "_wfC1",
    "_wfC2",
    "_gf",
    "_ef",
    "_tf",
    "_dcf",
    "_spec",
)


def live_code(src: str) -> str:
    """The function body with the header block and line comments removed.

    The header records the excluded forms, so the negative checks must run
    on the code, not on the whole file.
    """
    body = src.split("*/", 1)[-1]
    return "\n".join(line.split("//", 1)[0] for line in body.splitlines())


def compact(code: str) -> str:
    """Collapse whitespace so a match does not depend on SQF layout."""
    return re.sub(r"\s+", " ", code)


def has_identifier(code: str, name: str) -> bool:
    """True when the exact identifier appears, not a longer name."""
    return re.search(r"(?<![\w])" + re.escape(name) + r"(?![\w])", code) is not None


def reason_literals(code: str) -> set[str]:
    """Every reason string the code can emit.

    Covers an assigned `_reason = "..."` and an inline `[false, "..."]`.
    """
    assigned = re.findall(r'_reason\s*=\s*"([^"]+)"', code)
    inline = re.findall(r'\[\s*false\s*,\s*"([^"]+)"\s*\]', code)
    return set(assigned) | set(inline)


class TestFailClosedStatus(unittest.TestCase):
    """The published status is always unknown."""

    def setUp(self):
        self.code = live_code(SOIL.read_text(encoding="utf-8"))
        self.flat = compact(self.code)

    def test_returns_false_and_a_reason(self):
        self.assertRegex(self.flat, r"\[\s*false\s*,\s*_reason\s*\]")

    def test_publishes_known_false(self):
        self.assertRegex(
            self.flat,
            re.escape(KNOWN_VAR) + r"\s*,\s*false\s*\]",
        )

    def test_publishes_the_reason(self):
        self.assertRegex(
            self.flat,
            re.escape(REASON_VAR) + r"\s*,\s*_reason\s*\]",
        )

    def test_clears_the_three_numeric_variables(self):
        for name in CLEARED_VARS:
            self.assertRegex(
                self.flat,
                re.escape("QGVAR(" + name + ")") + r"\s*,\s*nil\s*\]",
                f"{name} must be cleared with nil",
            )


class TestReasonVocabulary(unittest.TestCase):
    """The reason vocabulary is closed and complete."""

    def setUp(self):
        self.code = live_code(SOIL.read_text(encoding="utf-8"))

    def test_vocabulary_is_exactly_the_three_tokens(self):
        self.assertEqual(reason_literals(self.code), REASON_TOKENS)

    def test_every_token_appears_as_a_literal(self):
        for token in REASON_TOKENS:
            self.assertIn(f'"{token}"', self.code, f"reason {token} missing")

    def test_null_vehicle_guard_is_present(self):
        self.assertRegex(self.code, r"isNull\s+_vehicle")

    def test_tracked_classification_is_present(self):
        self.assertIn('"Tracked_APC"', self.code)

    def test_unverified_inputs_is_the_default_outcome(self):
        self.assertIn('"unverifiedInputs"', self.code)


class TestNoNumericResultPath(unittest.TestCase):
    """The live path holds no model arithmetic and publishes no number."""

    def setUp(self):
        self.code = live_code(SOIL.read_text(encoding="utf-8"))

    def test_no_formula_constants(self):
        for const in FORMULA_CONSTANTS:
            self.assertNotIn(const, self.code, f"formula constant {const} present")

    def test_no_numeric_private_variables(self):
        for name in NUMERIC_IDENTIFIERS:
            self.assertFalse(
                has_identifier(self.code, name), f"numeric variable {name} present"
            )

    def test_no_class_table(self):
        for key in CLASS_KEYS:
            self.assertNotIn(key, self.code, f"class-table key {key} present")

    def test_no_invented_floor(self):
        self.assertNotRegex(self.code, r"\bmax\s+[0-9]")

    def test_no_engine_mass_or_geometry_read(self):
        self.assertNotIn("getMass", self.code)
        self.assertNotIn("getVehicleGeometry", self.code)

    def test_no_go_no_go_comparison(self):
        self.assertNotIn("_rci >=", compact(self.code))


class TestArgumentSafety(unittest.TestCase):
    """The status contract holds for malformed and missing arguments.

    Runtime coverage is out of scope. The SQF harness (tools/tests/sqf_lite.py)
    cannot execute this function. These checks read the live body and prove
    the ordering and the guards instead.
    """

    def setUp(self):
        self.code = live_code(SOIL.read_text(encoding="utf-8"))
        self.flat = compact(self.code)

    def _at(self, needle, label):
        pos = self.code.find(needle)
        self.assertNotEqual(pos, -1, f"{label} missing from the live body")
        return pos

    def test_params_has_no_restrictive_type_arrays(self):
        # ["_vehicle", objNull, [objNull]] and ["_rci", 0, [0]] throw on a
        # wrongly typed element before the stale state clears.
        self.assertNotIn(", [objNull]", self.code)
        self.assertNotIn(", [0]", self.code)

    def test_params_is_permissive(self):
        self.assertIn('["_vehicle", objNull]', self.flat)
        self.assertIn('["_rci", 0]', self.flat)

    def test_clears_run_before_the_argument_parse(self):
        # A malformed _this cannot reach params before the stale state clears.
        self.assertLess(
            self._at("QGVAR(currentVCI1)", "numeric clear"),
            self._at("params", "params parse"),
        )

    def test_knownness_and_clears_run_before_the_class_check(self):
        kind = self._at("isKindOf", "isKindOf")
        self.assertLess(self._at(KNOWN_VAR, "known flag"), kind)
        self.assertLess(self._at("QGVAR(currentVCI1)", "numeric clear"), kind)

    def test_clears_run_before_the_null_check(self):
        self.assertLess(
            self._at("QGVAR(currentVCI1)", "numeric clear"),
            self._at("isNull", "isNull"),
        )

    def test_object_type_check_guards_isNull_and_isKindOf(self):
        # isEqualType cannot throw on a non-object. isNull and isKindOf can.
        guard = self._at("isEqualType objNull", "object-type guard")
        self.assertLess(guard, self._at("isNull", "isNull"))
        self.assertLess(guard, self._at("isKindOf", "isKindOf"))

    def test_malformed_input_cannot_bypass_the_status_publication(self):
        # No early return may run before the reason is published.
        reason = self._at(REASON_VAR, "reason publication")
        for match in re.finditer(r"exitWith", self.code):
            self.assertGreater(
                match.start(), reason, "exitWith precedes the status publication"
            )


if __name__ == "__main__":
    unittest.main()
