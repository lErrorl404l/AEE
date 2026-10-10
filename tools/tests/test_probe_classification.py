#!/usr/bin/env python3
"""Every Docker probe file carries a run class, and each class holds its guard.

A probe is ``headless`` (a pure kernel or config read the dedicated server can
run), ``headless-client`` (it needs a non-dedicated machine, so the file guards
``!isDedicated``) or ``interface`` (it needs a human interface or rendering, so
the file guards ``hasInterface``).  A dedicated server and a headless client
both report ``hasInterface = false``, so an ``interface`` probe never runs on
either.

``fnc_devProbeManifest`` is the single machine-readable manifest.  This suite
fails when a probe file has no class, when a class is unknown, when a manifest
row names a missing file, or when a class that needs a machine carries no guard.
It also holds the console runner to the manifest, so a console probe cannot
report a client probe as passing from a server-only run.

Run: python3 -m unittest tools.tests.test_probe_classification
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

CLASSES = ("headless", "headless-client", "interface")
# One row: ["Pxx", "<class>", "aee_pxx_probe.sqf"],
_ROW = re.compile(r'\[\s*"(P[0-9A-Za-z]+)"\s*,\s*"([a-z-]+)"\s*,\s*"([^"]+)"\s*\]')
_FILE = re.compile(r"^aee_p([0-9]+[a-z]?)_")


def _rows() -> list[tuple[str, str, str]]:
    return _ROW.findall(MANIFEST.read_text(encoding="utf-8"))


def _probe_files() -> list[Path]:
    return sorted(MISSION.glob("aee_p*_probe.sqf"))


def _tag_of(path: Path) -> str | None:
    match = _FILE.match(path.name)
    return "P" + match.group(1).upper() if match else None


class TestProbeClassification(unittest.TestCase):
    def test_every_probe_file_has_a_class(self):
        classified = {tag for tag, _cls, _file in _rows()}
        missing = [
            path.name for path in _probe_files() if _tag_of(path) not in classified
        ]
        self.assertEqual(
            missing,
            [],
            "probe files with no manifest class: " + ", ".join(missing),
        )

    def test_every_class_is_known(self):
        unknown = sorted({cls for _tag, cls, _file in _rows() if cls not in CLASSES})
        self.assertEqual(unknown, [], "unknown probe classes: " + ", ".join(unknown))

    def test_no_duplicate_manifest_tags(self):
        tags = [tag for tag, _cls, _file in _rows()]
        dupes = sorted({tag for tag in tags if tags.count(tag) > 1})
        self.assertEqual(dupes, [], "duplicate manifest tags: " + ", ".join(dupes))

    def test_every_manifest_row_names_a_file_that_carries_its_tag(self):
        problems = []
        for tag, _cls, name in _rows():
            path = MISSION / name
            if not path.exists():
                problems.append(f"{tag}: missing file {name}")
            elif f"[{tag}]" not in path.read_text(encoding="utf-8", errors="replace"):
                problems.append(f"{tag}: {name} does not report with [{tag}]")
        self.assertEqual(problems, [], "; ".join(problems))

    def test_headless_client_probes_guard_a_dedicated_server(self):
        problems = []
        for tag, cls, name in _rows():
            if cls != "headless-client":
                continue
            text = (MISSION / name).read_text(encoding="utf-8", errors="replace")
            if "isDedicated" not in text:
                problems.append(f"{tag}: {name} needs an !isDedicated guard")
        self.assertEqual(problems, [], "; ".join(problems))

    def test_interface_probes_guard_an_interface(self):
        problems = []
        for tag, cls, name in _rows():
            if cls != "interface":
                continue
            text = (MISSION / name).read_text(encoding="utf-8", errors="replace")
            if "hasInterface" not in text:
                problems.append(f"{tag}: {name} needs a hasInterface guard")
        self.assertEqual(problems, [], "; ".join(problems))

    def test_the_default_harness_has_no_client_and_the_dev_config_has_one(self):
        default = (REPO / "tests" / "docker" / "config.toml").read_text(
            encoding="utf-8"
        )
        client = (REPO / "tests" / "docker" / "config.client.toml").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            default,
            r"\[headless\]\s*\nclients\s*=\s*0",
            "the default harness must stay at clients = 0",
        )
        self.assertRegex(
            client,
            r"\[headless\]\s*\nclients\s*=\s*1",
            "the dev client config must set clients = 1",
        )

    def test_the_runner_honours_the_class(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("headless-client", text, "the runner must know the client class")
        self.assertIn("interface", text, "the runner must know the interface class")
        self.assertIn("isDedicated", text, "the runner must gate on a dedicated server")
        self.assertIn("hasInterface", text, "the runner must gate on an interface")
        self.assertIn(
            "client-unavailable",
            text,
            "a client probe on a server-only run must report client-unavailable, not a pass",
        )


if __name__ == "__main__":
    unittest.main()
