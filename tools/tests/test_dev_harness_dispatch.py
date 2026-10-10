#!/usr/bin/env python3
"""The SQF extension-callback dispatcher correlates by id and parses literals.

``fnc_devDispatch`` is the SQF half of the callback bridge.  It parses the
extension request with ``parseSimpleArray`` only, runs the operation through
``fnc_devExec`` and returns the ``["reply", [id, payload]]`` list the event
handler forwards to ``callExtension``.

The operation table is replaced by a stub so this suite tests the envelope:
the id correlation, the reply shape and the malformed-payload path.  The
operation table has its own contract test (``test_dev_console_contract``).

Run: python3 -m unittest tools.tests.test_dev_harness_dispatch
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "tools" / "dev-harness" / "addons" / "dev"
DISPATCH = DEV / "functions" / "fnc_devDispatch.sqf"


def _exec_stub(result: str):
    """A stand-in for fnc_devExec that returns a fixed result."""

    def _run(op: str, args: list) -> str:
        del op, args
        return result

    return _run


class TestDevDispatchEnvelope(unittest.TestCase):
    """The dispatcher parses the request and answers the extension."""

    def test_known_id_emits_a_reply(self):
        out = run_sqf(
            DISPATCH,
            ["exec", '[7, "ping", []]'],
            {"aee_dev_fnc_devExec": _exec_stub("pong")},
        )
        self.assertEqual(out, ["reply", ["7", "pong"]])

    def test_malformed_payload_returns_an_error_reply(self):
        out = run_sqf(
            DISPATCH,
            ["exec", "not an array"],
            {"aee_dev_fnc_devExec": _exec_stub("pong")},
        )
        self.assertEqual(out[0], "reply")
        self.assertEqual(out[1][0], "0")
        self.assertIn("error", out[1][1])

    def test_short_payload_keeps_the_readable_id(self):
        out = run_sqf(
            DISPATCH,
            ["exec", "[42]"],
            {"aee_dev_fnc_devExec": _exec_stub("pong")},
        )
        self.assertEqual(out, ["reply", ["42", "error: malformed payload"]])

    def test_a_non_exec_function_is_ignored(self):
        out = run_sqf(
            DISPATCH,
            ["other", '[1, "ping", []]'],
            {"aee_dev_fnc_devExec": _exec_stub("pong")},
        )
        self.assertIsNone(out)

    def test_the_named_operation_receives_its_name_and_args(self):
        seen = {}

        def _record(op: str, args: list) -> str:
            seen["op"] = op
            seen["args"] = args
            return "ok"

        run_sqf(
            DISPATCH,
            ["exec", '[3, "get", ["aee_x"]]'],
            {"aee_dev_fnc_devExec": _record},
        )
        self.assertEqual(seen["op"], "get")
        self.assertEqual(seen["args"], ["aee_x"])


if __name__ == "__main__":
    unittest.main()
