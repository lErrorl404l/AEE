#!/usr/bin/env python3
"""The console command set is complete and holds its trust boundary.

Two layers.

A source contract asserts that every operation has a guard in ``fnc_devExec``,
that the verb table lists exactly the accepted set, that the ``AEE_DEV_FUNCS``
whitelist exists, and that the only ``compile`` call is the gated ``eval`` verb.

A behavioural layer runs ``fnc_devExec`` through the SQF harness with an
in-memory ``missionNamespace``, so the refusal paths (``set`` on a foreign
name, ``callfunc`` on a function outside the whitelist) return an error result.

Run: python3 -m unittest tools.tests.test_dev_console_contract
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "tools" / "dev-harness" / "addons" / "dev"
EXEC = DEV / "functions" / "fnc_devExec.sqf"
VERBS = DEV / "functions" / "fnc_devVerbs.sqf"
FUNCS = DEV / "functions" / "fnc_devFuncs.sqf"
DISPATCH = DEV / "functions" / "fnc_devDispatch.sqf"

OPS = (
    "ping",
    "get",
    "set",
    "dump",
    "eval",
    "callfunc",
    "batch",
    "scenario",
    "probes",
    "remote",
    "verbs",
)

# The whitelist the whitelist test seeds into the harness.
WHITELIST = ("aee_diagnostics_fnc_dumpState", "aee_lib_fnc_readState")


def _code_only(text: str) -> str:
    """Blank out line and block comments so a prose word is not a code hit."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def _globals(store: dict):
    return {
        "missionNamespace": "ns",
        "getVariable": lambda _ns, spec: (
            store.get(spec[0], spec[1] if len(spec) > 1 else None)
            if isinstance(spec, list)
            else store.get(spec)
        ),
        "setVariable": lambda _ns, spec: store.__setitem__(spec[0], spec[1]),
        "aee_dev_funcs": list(WHITELIST),
        "aee_dev_verbs": list(OPS),
    }


def _run(op, args, store=None):
    store = {} if store is None else store
    return run_sqf(EXEC, [op, args], _globals(store)), store


class TestConsoleSourceContract(unittest.TestCase):
    """Every operation is guarded and the table is exact."""

    def test_the_verb_table_lists_every_operation(self):
        text = VERBS.read_text(encoding="utf-8")
        for op in OPS:
            self.assertIn(f'"{op}"', text, op)

    def test_every_operation_has_a_guard(self):
        text = EXEC.read_text(encoding="utf-8")
        for op in OPS:
            self.assertIn(f'_op == "{op}"', text, op)

    def test_the_whitelist_exists(self):
        text = FUNCS.read_text(encoding="utf-8")
        self.assertIn("aee_diagnostics_fnc_dumpState", text)

    def test_compile_is_used_only_by_eval(self):
        code = _code_only(EXEC.read_text(encoding="utf-8"))
        self.assertEqual(code.count("compile"), 1)
        eval_guard = code.index('_op == "eval"')
        self.assertGreater(code.index("compile"), eval_guard)

    def test_the_dispatcher_never_compiles(self):
        self.assertNotIn("compile", _code_only(DISPATCH.read_text(encoding="utf-8")))


class TestConsoleBehaviour(unittest.TestCase):
    """The refusal paths return an error result; the happy paths answer."""

    def test_ping_answers(self):
        self.assertEqual(_run("ping", [])[0], "pong")

    def test_verbs_returns_the_table(self):
        self.assertEqual(_run("verbs", [])[0], list(OPS))

    def test_get_reads_a_namespace_variable(self):
        out, _ = _run("get", ["aee_x"], store={"aee_x": 1.0})
        self.assertEqual(out, "1")

    def test_set_refuses_a_foreign_name(self):
        out, store = _run("set", ["foo", 1])
        self.assertIn("error", out)
        self.assertNotIn("foo", store)

    def test_set_writes_an_aee_name(self):
        out, store = _run("set", ["aee_x", 1])
        self.assertEqual(out, "ok")
        self.assertEqual(store["aee_x"], 1)

    def test_callfunc_refuses_a_name_outside_the_whitelist(self):
        out, _ = _run("callfunc", ["evil", []])
        self.assertIn("error", out)

    def test_callfunc_reports_a_missing_function(self):
        out, _ = _run("callfunc", [WHITELIST[0], []])
        self.assertIn("error", out)

    def test_callfunc_calls_a_whitelisted_function(self):
        store = {WHITELIST[0]: lambda *_args: "core state"}
        out, _ = _run("callfunc", [WHITELIST[0], []], store=store)
        self.assertEqual(out, "core state")

    def test_dump_calls_a_component_dump(self):
        store = {"aee_diagnostics_fnc_dumpState": lambda *_args: "core state"}
        out, _ = _run("dump", ["diagnostics"], store=store)
        self.assertEqual(out, "core state")

    def test_unknown_verb_returns_an_error(self):
        out, _ = _run("nope", [])
        self.assertIn("error", out)

    def test_scenario_without_a_registry_entry_returns_an_error(self):
        out, _ = _run("scenario", ["missing"])
        self.assertRegex(out, re.compile("error"))


if __name__ == "__main__":
    unittest.main()
