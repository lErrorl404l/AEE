#!/usr/bin/env python3
"""The dev console contract doc is generated, never hand-synced (ADR-035).

The generator projects three sources into one marked doc block:

  * the extension command set from the Rust registration in
    ``tools/dev-harness/extension/src/lib.rs``;
  * the console verb table from ``fnc_devVerbs.sqf``;
  * the ``AEE_DEV_FUNCS`` whitelist from ``fnc_devFuncs.sqf``.

This suite fails when the block is stale, when a source name is missing from
the block, and when a deliberate drift passes ``--check``.

Run: python3 -m unittest tools.tests.test_dev_console_contract_doc
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import gen_dev_console_contract as gen  # noqa: E402


class TestGeneratedBlock(unittest.TestCase):
    def test_the_doc_block_is_fresh(self):
        doc = gen.DOC.read_text(encoding="utf-8")
        self.assertEqual(
            gen.current_block(doc),
            gen.build_block(),
            "the dev console contract is stale; run "
            "python3 tools/gen_dev_console_contract.py",
        )

    def test_the_extension_command_set_comes_from_the_rust_registration(self):
        commands = gen.extension_commands()
        self.assertIn("ping", commands)
        self.assertIn("start", commands)
        self.assertIn("stop", commands)
        self.assertTrue(
            any(name.startswith("kernel.") for name in commands),
            "no kernel command was read from the Rust registration",
        )

    def test_the_verb_table_comes_from_the_sqf_source(self):
        verbs = gen.console_verbs()
        for verb in ("ping", "get", "set", "callfunc", "verbs"):
            self.assertIn(verb, verbs)

    def test_the_whitelist_comes_from_the_sqf_source(self):
        self.assertEqual(
            gen.console_funcs(),
            ["aee_diagnostics_fnc_dumpState", "aee_lib_fnc_readState"],
        )

    def test_the_block_names_every_command_and_function(self):
        block = gen.build_block()
        for name in (
            gen.extension_commands() + gen.console_verbs() + gen.console_funcs()
        ):
            self.assertIn(f"`{name}`", block, name)

    def test_check_mode_exits_zero(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "gen_dev_console_contract.py"),
                "--check",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_drift_fails_check(self):
        doc = gen.DOC.read_text(encoding="utf-8")
        present = gen.current_block(doc)
        self.assertIsNotNone(present, "the generated markers are missing")
        # Insert the drift INSIDE the marked block, before the END marker.
        drifted = doc.replace(gen.END, "- `drift`\n" + gen.END)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dev-console-contract.md"
            path.write_text(drifted, encoding="utf-8")
            original = gen.DOC
            gen.DOC = path
            argv = sys.argv
            sys.argv = ["gen_dev_console_contract.py", "--check"]
            try:
                rc = gen.main()
            finally:
                gen.DOC = original
                sys.argv = argv
        self.assertEqual(rc, 1, "a stale block must fail --check")


if __name__ == "__main__":
    unittest.main()
