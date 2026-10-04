#!/usr/bin/env python3
"""Wildlife ecology kernel and source-contract tests.

The pure kernels run from their real SQF through tools/tests/sqf_lite.py, so a
test failure is a source failure, not a mirror drift.  The source contracts
read the engine wiring, which the harness cannot execute.

Run: python3 -m unittest tools.tests.test_wildlife -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WILDLIFE = ROOT / "addons" / "wildlife"
FUNCS = WILDLIFE / "functions"
DATA = WILDLIFE / "data"
MANIFEST = DATA / "sound_manifest.sqf"

# The only CfgSFX classes the manifest may name.  Each is a confirmed vanilla
# class (BIKI CfgSFX).  A new class here needs a dossier citation.
ALLOWED_CFGSFX = {"Owl", "Sound_Stream"}
ALLOWED_EXTENSIONS = {".wss", ".ogg", ".wav"}


def load_manifest():
    """The manifest rows from the real data file."""
    return run_sqf(MANIFEST, [])


class TestSoundManifest(unittest.TestCase):
    """The vanilla sound manifest carries no third-party media."""

    def test_manifest_is_a_non_empty_list_of_four_element_rows(self):
        rows = load_manifest()
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertEqual(len(row), 4, f"bad manifest row: {row}")

    def test_every_source_is_a_vanilla_path_or_a_listed_cfg_sfx_class(self):
        for key, source, _distance, _gain in load_manifest():
            self.assertIsInstance(key, str)
            self.assertNotEqual(key, "")
            self.assertIsInstance(source, str)
            if "." in source:
                self.assertTrue(
                    source.lower().startswith("a3\\"),
                    f"non-vanilla path: {source}",
                )
            else:
                self.assertIn(
                    source,
                    ALLOWED_CFGSFX,
                    f"unlisted CfgSFX class: {source}",
                )

    def test_no_third_party_prefix_and_only_known_media_extensions(self):
        for _key, source, _distance, _gain in load_manifest():
            self.assertFalse(
                source.lower().startswith(("x\\", "z\\")),
                f"third-party prefix: {source}",
            )
            if "." in source:
                extension = source[source.rfind(".") :].lower()
                self.assertIn(
                    extension,
                    ALLOWED_EXTENSIONS,
                    f"unexpected media extension: {source}",
                )

    def test_every_distance_and_gain_is_a_number(self):
        for row in load_manifest():
            self.assertIsInstance(row[2], (int, float))
            self.assertIsInstance(row[3], (int, float))
            self.assertGreater(row[2], 0)
            self.assertGreater(row[3], 0)


if __name__ == "__main__":
    unittest.main()
