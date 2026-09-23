"""The work-distribution mode must be honest.

A setting a user can select but that does nothing is the dead-setting
defect this project has already fixed twenty-one times. These tests read
the source, because the property is "this mode is actually honoured",
which no runtime test can see on a headless server.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def read(rel):
    return (REPO / rel).read_text(encoding="utf-8")


class TestComputeMode(unittest.TestCase):
    def setUp(self):
        self.settings = read("addons/core/initSettings.inc.sqf")
        self.biome = read("addons/environmental/functions/biome/fnc_getBiome.sqf")

    def test_the_setting_is_declared(self):
        self.assertIn("QGVAR(computeMode)", self.settings)

    def test_every_offered_mode_is_honoured(self):
        """Each value in the LIST must be read somewhere. A mode a user can
        pick but that changes nothing is a dead setting."""
        block = re.search(
            r"QGVAR\(computeMode\),(.*?)\] call CBA_fnc_addSetting",
            self.settings,
            re.S,
        )
        self.assertIsNotNone(block, "computeMode block not found")
        offered = re.findall(r'"([A-Z][A-Z_]{5,})"', block.group(1))
        self.assertTrue(offered, "no modes parsed from the list")
        sources = self.settings + self.biome
        for mode in offered:
            self.assertIn(mode, sources, f"{mode} is offered but never read")

    def test_server_authority_is_not_offered(self):
        """It was declared and never implemented. Offering it would be the
        dead-setting defect, and a partial broadcast would desynchronise
        machines, which is the one failure this mod cannot have."""
        self.assertNotIn("SERVER_AUTHORITY", self.settings)

    def test_the_client_still_scans_when_the_server_has_not_published(self):
        """The mode is an optimisation, never a correctness dependency. A
        player who joins mid mission never saw the one-shot broadcast, so
        the client must fall back to running its own sweep."""
        self.assertIn("scanWaitTicks", self.biome)

    def test_the_server_publishes_the_map_facts(self):
        self.assertIn("terrainSignalsPublished", self.biome)

    def test_the_default_mode_sends_nothing(self):
        """DETERMINISTIC is the default and must remain the no-network
        path, so an unmodified install never broadcasts."""
        block = re.search(
            r"QGVAR\(computeMode\),(.*?)\] call CBA_fnc_addSetting",
            self.settings,
            re.S,
        )
        # The default index is the third element of the value list.
        defaults = re.findall(r"\n\s+(\d+)\s*\n\s+\]\,", block.group(1))
        self.assertTrue(defaults, "default index not found")
        self.assertEqual(defaults[-1], "0", "the default mode must be index 0")


if __name__ == "__main__":
    unittest.main()
