#!/usr/bin/env python3
"""The CBA per-frame handler calling convention contract.

CBA_fnc_addPerFrameHandler (CBA_A3 addons/common/fnc_addPerFrameHandler.sqf)
takes [function, delay, args].  init_perFrameHandler.sqf runs the registered
function as `[_args, _handle] call _function`, and `_args` defaults to [].
A handler registered without args therefore receives `_this = [[], _handle]`.

A named handler registered with no args must NOT declare a top-level `params`
statement, because that statement validates the handler array and throws a
type error every frame.  This is the live AI and wildlife defect: fnc_aiTick
declared `params [["_dryRun", false, [false]]]` and saw `[]` (an Array where a
Bool was expected), and fnc_wildlifeTick declared `params [["_anchor", [], [[]]],
["_dryRun", false, [false]]]` and saw the handle Number where a Bool was
expected.  The framework calls are correct; the handler signatures were wrong.

A `params` statement nested inside a code block is fine: it validates the
block's own arguments, not the handler array.  Only a top-level statement is
checked.  A directly-callable entry with `params` is also fine: only the
function registered with the per-frame handler is checked.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDONS = ROOT / "addons"

# A named registration: [FUNC(name), delay] or [EFUNC(addon, name), delay],
# optionally with a third element (the args array).  Inline code blocks are
# not named handlers and are out of scope.
_REGISTRATION = re.compile(
    r"\[\s*((?:E)?FUNC)\s*\(([^)]*)\)\s*,\s*([^\]]*?)\s*\]\s*"
    r"call\s+CBA_fnc_addPerFrameHandler"
)


def _strip(text):
    """Remove comments and string literals, preserving newlines."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            out.append(" ")
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                out.append("\n" if i < n and text[i] == "\n" else " ")
                i += 1
            i += 1
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            i += 2
            while i < n and not text.startswith("*/", i):
                out.append("\n" if text[i] == "\n" else " ")
                i += 1
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _has_top_level_params(text):
    """True when `params [` is a statement at brace depth zero."""
    stripped = _strip(text)
    depth = 0
    for match in re.finditer(r"[{}]|\bparams\b", stripped):
        token = match.group(0)
        if token == "{":
            depth += 1
        elif token == "}":
            depth = max(0, depth - 1)
        elif depth == 0 and re.match(r"\s*\[", stripped[match.end() :]):
            return True
    return False


def _find_function(addon, name):
    """Resolve a PREP'd function by name under the addon's functions tree."""
    base = ADDONS / addon / "functions"
    if not base.is_dir():
        return None
    matches = sorted(base.rglob("fnc_%s.sqf" % name))
    return matches[0] if matches else None


def _named_registrations():
    for path in sorted(ADDONS.rglob("*.sqf")):
        addon = path.relative_to(ADDONS).parts[0]
        text = path.read_text(encoding="utf-8")
        for match in _REGISTRATION.finditer(text):
            kind = match.group(1)
            names = [part.strip() for part in match.group(2).split(",")]
            args_tail = match.group(3)
            if kind == "FUNC":
                target = _find_function(addon, names[0])
            else:
                target = _find_function(names[0], names[-1])
            yield path, kind, match.group(2), args_tail, target


class TestPerFrameHandlerParamsContract(unittest.TestCase):
    """A no-args per-frame handler must not declare a top-level params."""

    def test_a_named_registration_resolves_to_a_file(self):
        for path, kind, names, _tail, target in _named_registrations():
            self.assertIsNotNone(
                target,
                "cannot resolve %s(%s) registered in %s" % (kind, names, path),
            )

    def test_no_arg_handler_has_no_top_level_params(self):
        offenders = []
        for path, _kind, names, args_tail, target in _named_registrations():
            # A third element means the registration supplies _args, so the
            # handler may legitimately declare params matching [_args, _handle].
            if "," in args_tail or target is None:
                continue
            if _has_top_level_params(target.read_text(encoding="utf-8")):
                offenders.append(
                    "%s is registered without args in %s (%s) but declares a "
                    "top-level params; the per-frame handler passes "
                    "[_args, _handle]" % (target.relative_to(ROOT), path.name, names)
                )
        self.assertEqual(offenders, [], "\n".join(offenders))


if __name__ == "__main__":
    unittest.main()
