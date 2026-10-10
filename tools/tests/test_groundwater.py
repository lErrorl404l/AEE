"""Groundwater and aquifer model (issue #26).

The water table, the spring discharge and the aquifer property table. The
two arithmetic kernels are executed through the SQF harness (issue #204), so
a drift in the shipped SQF fails the test. The property table is parsed out
of the source and evaluated, because the harness has no
createHashMapFromArray builtin.

Sources:
  specific yield   Johnson (1967), USGS Water-Supply Paper 1662-D
  saturated K      Freeze and Cherry (1979), Groundwater, Table 2.2
  water table      Meinzer (1923), USGS WSP 489; Healy and Cook (2002), the
                   water-table fluctuation method, Hydrogeology J. 10:91-109
  spring discharge Darcy (1856)

Run: python3 -m unittest tools.tests.test_groundwater -v
"""

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HYD = REPO / "addons" / "hydrology" / "functions" / "hydrology"
PREP = REPO / "addons" / "hydrology" / "XEH_PREP.hpp"
RIVER = REPO / "addons" / "hydrology" / "functions" / "fnc_calculateRiverWaterLevel.sqf"
BEARING = (
    REPO / "addons" / "mobility" / "functions" / "fnc_calculateSoilBearingStrength.sqf"
)

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

WT_SQF = HYD / "fnc_calculateWaterTableDepth.sqf"
SPRING_SQF = HYD / "fnc_calculateSpringFlow.sqf"
AQUIFER_SQF = HYD / "fnc_getAquiferProperties.sqf"

# Johnson 1967 / Freeze and Cherry 1979, Table 2.2.
AQUIFER_TABLE = {
    "rock": (0.23, 1000.0),
    "ground": (0.21, 10.0),
    "vegetation": (0.08, 0.1),
    "water": (0.0, 0.0),
    "concrete": (0.03, 0.001),
    "asphalt": (0.03, 0.001),
    "metal": (0.03, 0.001),
    "glass": (0.03, 0.001),
    "wood": (0.03, 0.001),
}
CLAY_DEFAULT = (0.03, 0.001)


def water_table(store, sy, ref=3.0):
    """Mirror of fnc_calculateWaterTableDepth.sqf."""
    sy = max(sy, 0.01)
    head = max(store, 0.0) / (1000 * sy)
    return max(ref - head, 0.0), head


def spring_flow(wt, orifice, ksat, area, gradient):
    """Mirror of fnc_calculateSpringFlow.sqf."""
    if wt >= orifice:
        return 0.0, False
    return (ksat * area * gradient) / 86400, True


def buoyancy_factor(wt_depth, foundation=1.0):
    """Mirror of the water-table term in fnc_calculateSoilBearingStrength.sqf."""
    if wt_depth >= foundation:
        return 1.0
    return 0.5 + 0.5 * (wt_depth / foundation)


def parse_aquifer_table():
    text = AQUIFER_SQF.read_text(encoding="utf-8")
    block = re.search(r"createHashMapFromArray\s*\[(.*?)\n\];", text, re.S)
    assert block, "no createHashMapFromArray table in fnc_getAquiferProperties"
    rows = {}
    for name, sy, ksat in re.findall(
        r'\[\s*"([^"]+)"\s*,\s*\[\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\]\s*\]',
        block.group(1),
    ):
        rows[name] = (float(sy), float(ksat))
    return rows


class TestAquiferProperties(unittest.TestCase):
    def setUp(self):
        self.text = AQUIFER_SQF.read_text(encoding="utf-8")

    def test_table_matches_the_cited_values(self):
        parsed = parse_aquifer_table()
        for name, row in AQUIFER_TABLE.items():
            self.assertIn(name, parsed, f"{name} missing from the table")
            self.assertEqual(parsed[name], row, f"{name} row drifted")

    def test_rock_uses_the_free_draining_values(self):
        """The classifier merges gravel into rock, so rock is the gravel row."""
        self.assertEqual(parse_aquifer_table()["rock"], (0.23, 1000.0))

    def test_unknown_class_falls_to_clay(self):
        """The default row is clay, the least transmissive lithology."""
        self.assertIn("getOrDefault [_material, [0.03, 0.001]]", self.text)

    def test_cites_the_sources(self):
        for token in ("Johnson", "1662-D", "Freeze", "Table 2.2"):
            self.assertIn(token, self.text)


class TestWaterTable(unittest.TestCase):
    def test_empty_store_sits_at_the_reference_depth(self):
        depth, head = water_table(0, 0.1, 3.0)
        self.assertEqual(head, 0.0)
        self.assertEqual(depth, 3.0)

    def test_head_is_store_over_specific_yield(self):
        """100 mm over S_y=0.2 is a 0.5 m rise (the WTF relation dS = S_y dh)."""
        depth, head = water_table(100, 0.2, 3.0)
        self.assertAlmostEqual(head, 0.5, places=6)
        self.assertAlmostEqual(depth, 2.5, places=6)

    def test_a_full_aquifer_puts_the_table_at_the_surface(self):
        depth, _head = water_table(600, 0.2, 3.0)
        self.assertEqual(depth, 0.0)

    def test_the_table_cannot_rise_above_the_ground(self):
        depth, _head = water_table(100000, 0.2, 3.0)
        self.assertEqual(depth, 0.0)

    def test_a_wetter_store_raises_the_table(self):
        dry, _ = water_table(50, 0.2, 3.0)
        wet, _ = water_table(300, 0.2, 3.0)
        self.assertLess(wet, dry)

    def test_cites_the_water_table_fluctuation_method(self):
        text = WT_SQF.read_text(encoding="utf-8")
        self.assertIn("water-table fluctuation method", text)
        self.assertIn("Meinzer", text)
        self.assertIn("Healy", text)

    def test_executes_the_shipped_kernel(self):
        """Run the real SQF, not the mirror (issue #204)."""
        depth, head = run_sqf(WT_SQF, [100, 0.2, 3])
        self.assertAlmostEqual(head, 0.5, places=6)
        self.assertAlmostEqual(depth, 2.5, places=6)
        depth2, _ = run_sqf(WT_SQF, [100000, 0.2, 3])
        self.assertEqual(depth2, 0.0)


class TestSpringFlow(unittest.TestCase):
    def test_darcy_discharge_vector(self):
        """K=10 m/day, A=1 m2, i=0.01 -> 0.1 m3/day = 1.157e-6 m3/s."""
        flow, active = spring_flow(0.5, 1.0, 10.0, 1.0, 0.01)
        self.assertTrue(active)
        self.assertAlmostEqual(flow, 0.1 / 86400, places=12)

    def test_a_deep_water_table_leaves_the_spring_dry(self):
        flow, active = spring_flow(1.5, 1.0, 10.0, 1.0, 0.01)
        self.assertFalse(active)
        self.assertEqual(flow, 0.0)

    def test_the_orifice_depth_is_the_threshold(self):
        _flow, at = spring_flow(1.0, 1.0, 10.0, 1.0, 0.01)
        _flow, just_above = spring_flow(0.99, 1.0, 10.0, 1.0, 0.01)
        self.assertFalse(at)
        self.assertTrue(just_above)

    def test_a_larger_gradient_flows_more(self):
        low, _ = spring_flow(0.5, 1.0, 10.0, 1.0, 0.001)
        high, _ = spring_flow(0.5, 1.0, 10.0, 1.0, 0.05)
        self.assertGreater(high, low)

    def test_cites_darcy(self):
        text = SPRING_SQF.read_text(encoding="utf-8")
        self.assertIn("Darcy", text)
        self.assertIn("Freeze", text)

    def test_executes_the_shipped_kernel(self):
        flow, active = run_sqf(SPRING_SQF, [0.5, 1, 10, 1, 0.01])
        self.assertTrue(active)
        self.assertAlmostEqual(flow, 0.1 / 86400, places=12)
        dry, active2 = run_sqf(SPRING_SQF, [2, 1, 10, 1, 0.01])
        self.assertFalse(active2)
        self.assertEqual(dry, 0)


class TestBearingCoupling(unittest.TestCase):
    def test_a_surface_water_table_halves_the_bearing(self):
        self.assertAlmostEqual(buoyancy_factor(0.0), 0.5, places=6)

    def test_a_deep_water_table_leaves_the_bearing_intact(self):
        self.assertEqual(buoyancy_factor(1.0), 1.0)
        self.assertEqual(buoyancy_factor(30.0), 1.0)

    def test_the_reduction_is_linear_to_the_foundation(self):
        self.assertAlmostEqual(buoyancy_factor(0.5), 0.75, places=6)

    def test_consumer_reads_the_published_water_table(self):
        text = BEARING.read_text(encoding="utf-8")
        self.assertIn("EGVAR(core,waterTableDepth_m)", text)


class TestWiring(unittest.TestCase):
    def test_kernels_are_prepared(self):
        prep = PREP.read_text(encoding="utf-8")
        for name in (
            "calculateWaterTableDepth",
            "calculateSpringFlow",
            "getAquiferProperties",
        ):
            self.assertIn(f"PREPS(hydrology,{name})", prep)

    def test_river_calls_the_groundwater_kernels(self):
        river = RIVER.read_text(encoding="utf-8")
        self.assertIn("FUNC(getAquiferProperties)", river)
        self.assertIn("FUNC(calculateWaterTableDepth)", river)
        self.assertIn("FUNC(calculateSpringFlow)", river)

    def test_spring_flow_feeds_the_river_discharge(self):
        river = RIVER.read_text(encoding="utf-8")
        self.assertIn(
            "_totalDischarge = _dischargeM3s + _baseflowM3s + _springM3s", river
        )

    def test_the_water_table_is_published(self):
        river = RIVER.read_text(encoding="utf-8")
        self.assertIn(
            "setVariable [QEGVAR(core,waterTableDepth_m), _waterTableDepth_m]", river
        )

    def test_the_baseflow_model_is_reused_not_reimplemented(self):
        """One baseflow model: the river still calls the issue-#24 reservoir."""
        river = RIVER.read_text(encoding="utf-8")
        self.assertIn("FUNC(calculateBaseflow)", river)


if __name__ == "__main__":
    unittest.main()
