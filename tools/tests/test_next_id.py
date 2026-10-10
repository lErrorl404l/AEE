"""The dynamic identifier allocator (tools/next_id.py).

The allocator derives the next free ADR number and probe tag from the
committed records plus a shared reservation registry, so two concurrent
worktrees never hand out the same value.

Run: python3 -m unittest tools.tests.test_next_id
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

_SPEC = importlib.util.spec_from_file_location("next_id", REPO / "tools" / "next_id.py")
assert _SPEC is not None and _SPEC.loader is not None
next_id = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(next_id)


def _tree(adrs: tuple[int, ...] = (), probes: tuple[int, ...] = ()) -> Path:
    root = Path(tempfile.mkdtemp())
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    for number in adrs:
        (adr_dir / f"ADR-{number:03d}-slug.md").write_text("record\n")
    probe_dir = root / "tests" / "docker" / "missions" / "aee_test.Stratis"
    probe_dir.mkdir(parents=True)
    manifest_dir = root / "tools" / "dev-harness" / "addons" / "dev" / "functions"
    manifest_dir.mkdir(parents=True)
    rows = ""
    for number in probes:
        (probe_dir / f"aee_p{number:03d}_probe.sqf").write_text("probe\n")
        rows += f'["P{number:03d}", "headless", "aee_p{number:03d}_probe.sqf"],\n'
    (manifest_dir / "fnc_devProbeManifest.sqf").write_text("[\n" + rows + "]\n")
    return root


class TestNextId(unittest.TestCase):
    def test_committed_adr_reads_the_glob(self):
        root = _tree(adrs=(1, 2, 37))
        self.assertEqual(next_id.committed_adr(root), [1, 2, 37])

    def test_committed_probe_reads_the_manifest_and_the_files(self):
        root = _tree(probes=(140, 141, 142))
        self.assertEqual(next_id.committed_probe(root), [140, 141, 142])

    def test_next_free_is_max_plus_one(self):
        self.assertEqual(next_id.next_free([1, 37], []), 38)
        self.assertEqual(next_id.next_free([1, 37], [38, 39]), 40)
        self.assertEqual(next_id.next_free([], []), 1)

    def test_allocate_adr_is_distinct_across_callers(self):
        root = _tree(adrs=(1, 37))
        registry = root / "registry.json"
        self.assertEqual(next_id.allocate("adr", root, registry), "038")
        self.assertEqual(next_id.allocate("adr", root, registry), "039")

    def test_allocate_probe_carries_the_p_prefix(self):
        root = _tree(probes=(142,))
        registry = root / "registry.json"
        self.assertEqual(next_id.allocate("probe", root, registry), "P143")

    def test_a_committed_value_does_not_repeat_a_reservation(self):
        root = _tree(adrs=(1, 37))
        registry = root / "registry.json"
        next_id.allocate("adr", root, registry)
        (root / "docs" / "adr" / "ADR-038-slug.md").write_text("record\n")
        self.assertEqual(next_id.allocate("adr", root, registry), "039")

    def test_release_drops_a_reservation_once(self):
        root = _tree(adrs=(1, 37))
        registry = root / "registry.json"
        next_id.allocate("adr", root, registry)
        self.assertTrue(next_id.release("adr", "038", registry))
        self.assertFalse(next_id.release("adr", "038", registry))
        self.assertEqual(json.loads(registry.read_text())["adr"], [])


if __name__ == "__main__":
    unittest.main()
