#!/usr/bin/env python3
"""A console result is evidence, not a gate (ADR-035).

The console ``probes`` op returns ``[[tag, verdict, diag], ...]`` for the tags
its runner can reach.  Every such fact must name a probe file, so no console
fact is an assumption with nothing behind it.

The class decides whether the fact also gates CI:

* a ``headless`` console fact runs on the dedicated server, so it must also
  carry a ``verify.py`` PASS gate;
* a ``headless-client`` or ``interface`` console fact cannot run in the
  server-only gate, so it must NOT carry one - it stays evidence.

Run: python3 -m unittest tools.tests.test_console_fact_gating
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEV = REPO / "tools" / "dev-harness" / "addons" / "dev"
MANIFEST = DEV / "functions" / "fnc_devProbeManifest.sqf"
RUNNER = DEV / "functions" / "fnc_devProbes.sqf"
MISSION = REPO / "tests" / "docker" / "missions" / "aee_test.Stratis"
VERIFY = REPO / "tests" / "docker" / "verify.py"
ADR = REPO / "docs" / "adr" / "ADR-035-truth-versus-assumption-console-evidence.md"

_TAG = re.compile(r'"(P[0-9A-Za-z]+)"')
_ROW = re.compile(r'\[\s*"(P[0-9A-Za-z]+)"\s*,\s*"([a-z-]+)"\s*,\s*"([^"]+)"\s*\]')
_PASS = re.compile(r'"\[P([0-9A-Za-z]+)\] \[PASS\]"')


def _console_tags() -> set[str]:
    return set(_TAG.findall(RUNNER.read_text(encoding="utf-8")))


def _manifest() -> dict[str, tuple[str, str]]:
    return {
        tag: (cls, name)
        for tag, cls, name in _ROW.findall(MANIFEST.read_text(encoding="utf-8"))
    }


def _gating_tags() -> set[str]:
    return {"P" + tag for tag in _PASS.findall(VERIFY.read_text(encoding="utf-8"))}


class TestConsoleFactGating(unittest.TestCase):
    def test_every_console_fact_names_a_probe_file_that_carries_its_tag(self):
        manifest = _manifest()
        problems = []
        for tag in sorted(_console_tags()):
            if tag not in manifest:
                problems.append(f"{tag}: no manifest row")
                continue
            _cls, name = manifest[tag]
            path = MISSION / name
            if not path.exists():
                problems.append(f"{tag}: missing probe file {name}")
            elif f"[{tag}]" not in path.read_text(encoding="utf-8", errors="replace"):
                problems.append(f"{tag}: {name} does not report with [{tag}]")
        self.assertEqual(problems, [], "; ".join(problems))

    def test_a_headless_console_fact_also_gates_ci(self):
        manifest = _manifest()
        gating = _gating_tags()
        missing = sorted(
            tag
            for tag in _console_tags()
            if manifest.get(tag, ("", ""))[0] == "headless" and tag not in gating
        )
        self.assertEqual(
            missing,
            [],
            "headless console facts with no verify.py gate: " + ", ".join(missing),
        )

    def test_a_client_console_fact_does_not_gate_ci(self):
        manifest = _manifest()
        gating = _gating_tags()
        wrong = sorted(
            tag
            for tag in _console_tags()
            if manifest.get(tag, ("", ""))[0] in ("headless-client", "interface")
            and tag in gating
        )
        self.assertEqual(
            wrong,
            [],
            "console-only facts must not gate CI: " + ", ".join(wrong),
        )

    def test_the_truth_rule_is_recorded(self):
        self.assertTrue(ADR.exists(), f"missing {ADR.name}")
        text = ADR.read_text(encoding="utf-8")
        self.assertIn("evidence, not a gate", text)
        self.assertIn("verify.py", text)


if __name__ == "__main__":
    unittest.main()
