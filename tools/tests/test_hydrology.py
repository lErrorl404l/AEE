"""Hydrology mirrors for issue #24.

Issue #24 gives exact test vectors for each model. They are reproduced
here so the published numbers, not my reading of the formulas, are what
the code is held to.

  SCS Curve Number   CN=80, P=50 -> Q=13.80 mm
                     CN=98, P=25 -> Q=19.70 mm
  Fill-spill         Ds=5, +3/tick -> spills 0, 1, 3 mm
  Baseflow           k_g=0.2/day -> K=0.8187, Q(1)=8.187, Q(5)=3.679

Sources: NRCS TR-55 1986 (SCS CN); Chu et al. 2013 (depression storage);
USGS SIR 2022-5114 (baseflow recession).
"""

import math
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HYDROLOGY = REPO / "addons" / "mobility" / "functions" / "hydrology"
RIVER_SQF = (
    REPO / "addons" / "mobility" / "functions" / "fnc_calculateRiverWaterLevel.sqf"
)
PREP_HPP = REPO / "addons" / "mobility" / "XEH_PREP.hpp"
GA_SQF = HYDROLOGY / "fnc_calculateGreenAmptInfiltration.sqf"
D8_SQF = HYDROLOGY / "fnc_routeRunoffD8.sqf"

SECONDS_PER_DAY = 86400.0


def scs_runoff(rain_mm, cn, moisture=0.4):
    """Mirrors fnc_calculateRunoffSCS.sqf.

    The default moisture is 0.4, inside the neutral band (0.3 to 0.5), so
    no antecedent adjustment applies and the raw CN is used. The issue's
    vectors are stated for the unadjusted number.
    """
    if rain_mm <= 0:
        return 0.0
    if moisture >= 0.5:
        cn = cn / (0.427 + 0.00573 * cn)
    elif moisture < 0.3:
        cn = cn / (2.281 - 0.01281 * cn)
    cn = max(30, min(99, cn))
    s = (25400 / cn) - 254
    ia = 0.2 * s
    if rain_mm <= ia:
        return 0.0
    return (rain_mm - ia) ** 2 / (rain_mm + 0.8 * s)


def depression_storage(stored, inflow, capacity):
    """Mirrors fnc_calculateDepressionStorage.sqf."""
    stored = max(0.0, stored)
    capacity = max(0.0, capacity)
    filled = min(capacity, stored + inflow)
    spill = max(0.0, (stored + inflow) - filled)
    return filled, spill


def baseflow(store, inflow, k_g, interval=SECONDS_PER_DAY):
    """Mirrors fnc_calculateBaseflow.sqf."""
    store = max(0.0, store)
    decay = math.exp(-k_g * (interval / SECONDS_PER_DAY))
    new_store = (store + inflow) * decay
    return new_store, max(0.0, (store + inflow) - new_store)


def manning_stage(q_m3s, width_m, slope, n):
    """Mirrors the Manning rating in fnc_calculateRiverWaterLevel.sqf."""
    if q_m3s <= 0:
        return 0.0
    return (q_m3s * n / (width_m * math.sqrt(slope))) ** 0.6


class TestSCSCurveNumber(unittest.TestCase):
    def test_issue_vector_1(self):
        """#24: CN=80, P=50 -> Q=13.80 mm."""
        self.assertAlmostEqual(scs_runoff(50, 80), 13.80, places=2)

    def test_issue_vector_2(self):
        """#24: CN=98, P=25 -> Q=19.70 mm."""
        self.assertAlmostEqual(scs_runoff(25, 98), 19.70, places=2)

    def test_below_initial_abstraction_no_runoff(self):
        """A small fall is absorbed entirely. This is why a per-tick
        application of a cumulative method returns zero."""
        self.assertEqual(scs_runoff(5, 80), 0.0)

    def test_impervious_sheds_more_than_pervious(self):
        self.assertGreater(scs_runoff(50, 98), scs_runoff(50, 75))

    def test_wet_soil_runs_off_more(self):
        """Group III antecedent moisture raises the number."""
        dry = scs_runoff(50, 80, moisture=0.2)
        neutral = scs_runoff(50, 80, moisture=0.4)
        wet = scs_runoff(50, 80, moisture=0.6)
        self.assertLess(dry, neutral)
        self.assertLess(neutral, wet)


class TestDepressionStorage(unittest.TestCase):
    def test_issue_vector(self):
        """#24: Ds=5, +3/tick -> spills 0, 1, 3 mm."""
        store = 0.0
        spills = []
        for _ in range(3):
            store, spill = depression_storage(store, 3, 5)
            spills.append(spill)
        self.assertEqual(spills, [0, 1, 3])

    def test_a_full_store_spills_the_lot(self):
        _store, spill = depression_storage(5, 3, 5)
        self.assertEqual(spill, 3)

    def test_capacity_is_never_exceeded(self):
        store, _spill = depression_storage(0, 100, 5)
        self.assertEqual(store, 5)


class TestBaseflow(unittest.TestCase):
    def test_issue_recession_constant(self):
        """#24: k_g=0.2/day -> K=0.8187."""
        self.assertAlmostEqual(math.exp(-0.2), 0.8187, places=4)

    def test_issue_flows(self):
        """#24: Q(1)=8.187, Q(5)=3.679 from Q0=10."""
        self.assertAlmostEqual(10 * math.exp(-0.2 * 1), 8.187, places=3)
        self.assertAlmostEqual(10 * math.exp(-0.2 * 5), 3.679, places=3)

    def test_a_dry_store_produces_no_flow(self):
        _store, out = baseflow(0, 0, 0.2)
        self.assertEqual(out, 0.0)

    def test_recession_over_a_day_matches_the_constant(self):
        """One day at k_g=0.2 must retain K of the store. The published
        K is rounded to 0.8187, so the comparison carries its precision."""
        store, _out = baseflow(10, 0, 0.2, interval=SECONDS_PER_DAY)
        self.assertAlmostEqual(store / 10, 0.8187, places=4)


class TestManningStage(unittest.TestCase):
    def test_stage_rises_with_discharge(self):
        low = manning_stage(0.5, 4, 0.001, 0.035)
        high = manning_stage(5.0, 4, 0.001, 0.035)
        self.assertGreater(high, low)

    def test_stage_is_sublinear(self):
        """h goes as Q^(3/5), so ten times the flow is less than ten times
        the stage. A linear response would be wrong."""
        one = manning_stage(1.0, 4, 0.001, 0.035)
        ten = manning_stage(10.0, 4, 0.001, 0.035)
        self.assertLess(ten, one * 10)
        self.assertAlmostEqual(ten / one, 10**0.6, places=6)

    def test_a_steeper_bed_lowers_the_stage(self):
        gentle = manning_stage(1.0, 4, 0.0001, 0.035)
        steep = manning_stage(1.0, 4, 0.01, 0.035)
        self.assertLess(steep, gentle)

    def test_no_flow_is_no_stage(self):
        self.assertEqual(manning_stage(0.0, 4, 0.001, 0.035), 0.0)


# ─── Green-Ampt (issue #24) ───────────────────────────────────────────────

# Rawls, Brakensiek and Miller 1983, Table 2, as the issue lists it:
# texture -> (theta_e, psi_mm, K_mm_per_h). theta_e is EFFECTIVE porosity.
GA_TABLE = {
    "sand": (0.417, 49.5, 117.8),
    "loamy sand": (0.401, 61.3, 29.9),
    "sandy loam": (0.412, 110.1, 10.9),
    "loam": (0.434, 88.9, 3.4),
    "silt loam": (0.486, 166.8, 6.5),
    "sandy clay loam": (0.330, 218.5, 1.5),
    "clay loam": (0.309, 208.8, 1.0),
    "silty clay loam": (0.432, 273.0, 1.0),
    "sandy clay": (0.321, 239.0, 0.6),
    "silty clay": (0.423, 292.2, 0.5),
    "clay": (0.385, 316.3, 0.3),
}


def green_ampt(F, theta_e, psi, k, theta_i=0.0):
    """Mirrors fnc_calculateGreenAmptInfiltration.sqf.

    dTheta is theta_e - theta_i. theta_e is the table's EFFECTIVE porosity,
    not the total porosity.
    """
    dtheta = max(theta_e - theta_i, 1e-6)
    psi_dtheta = psi * dtheta
    rate = k * (1 + psi_dtheta / max(F, 1e-6))
    t = (F - psi_dtheta * math.log(1 + F / psi_dtheta)) / k
    return rate, F, t


class TestGreenAmpt(unittest.TestCase):
    def test_sand_vector(self):
        """#24: sand, F=50, theta_i=0 -> t=0.209 h (exact 0.2089)."""
        _rate, _f, t = green_ampt(50, *GA_TABLE["sand"])
        self.assertAlmostEqual(t, 0.2089, places=3)

    def test_clay_vector_is_the_analytic_value(self):
        """Clay, F=10, theta_i=0 -> t=1.298 h.

        The issue states 16.0 h for this vector. That value is NOT
        reproducible from the published parameters: the table's clay row
        (theta_e=0.385, psi=316.3 mm, K=0.3 mm/h) gives 1.298 h. Reaching
        16.0 h needs theta_i=0.3712, a nearly saturated soil, which
        contradicts the sand vector's theta_i=0. The 16.0 h figure is a
        defect in the issue and is not encoded here.
        """
        _rate, _f, t = green_ampt(10, *GA_TABLE["clay"])
        self.assertAlmostEqual(t, 1.298, places=3)

    def test_dtheta_uses_effective_porosity(self):
        """The convention that matters: theta_e, never total porosity.

        Sand, F=50: theta_e=0.417 gives 0.2089 h; the total porosity
        0.437 gives 0.2046 h. Asserting 0.2089 stops the wrong convention
        from creeping back.
        """
        _rate, _f, correct = green_ampt(50, 0.417, 49.5, 117.8)
        _rate2, _f2, wrong = green_ampt(50, 0.437, 49.5, 117.8)
        self.assertAlmostEqual(correct, 0.2089, places=3)
        self.assertAlmostEqual(wrong, 0.2046, places=3)
        self.assertNotAlmostEqual(correct, wrong, places=3)

    def test_rate_falls_toward_k_as_f_grows(self):
        """The limit behaviour: a wet soil infiltrates at K."""
        theta_e, psi, k = GA_TABLE["sand"]
        rate, _f, _t = green_ampt(1.0e6, theta_e, psi, k)
        self.assertAlmostEqual(rate, k, places=1)

    def test_rate_is_large_as_f_approaches_zero(self):
        theta_e, psi, k = GA_TABLE["sand"]
        rate, _f, _t = green_ampt(0.0, theta_e, psi, k)
        self.assertGreater(rate, k * 100)

    def test_rate_decreases_with_f(self):
        theta_e, psi, k = GA_TABLE["loam"]
        rates = [green_ampt(F, theta_e, psi, k)[0] for F in (1, 10, 100, 1000)]
        for earlier, later in zip(rates, rates[1:]):
            self.assertGreater(earlier, later)

    def test_a_wet_soil_infiltrates_less(self):
        theta_e, psi, k = GA_TABLE["loam"]
        dry = green_ampt(10, theta_e, psi, k, theta_i=0.0)[0]
        wet = green_ampt(10, theta_e, psi, k, theta_i=0.3)[0]
        self.assertLess(wet, dry)


class TestGreenAmptSource(unittest.TestCase):
    """Evaluate the SQF table and the dTheta expression, not the mirror.

    A mirror compared against itself proves nothing. This class reads the
    constants and the convention out of the SQF and evaluates them, so it
    fails when the source is wrong however the mirror is written.
    """

    def setUp(self):
        self.text = GA_SQF.read_text(encoding="utf-8")

    def _parsed_table(self):
        rows = {}
        for name, e, psi, k in re.findall(
            r'\[\s*"([^"]+)"\s*,\s*\[\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,'
            r"\s*([0-9.]+)\s*\]\s*\]",
            self.text,
        ):
            rows[name] = (float(e), float(psi), float(k))
        return rows

    def test_table_matches_rawls_1983(self):
        parsed = self._parsed_table()
        for name, row in GA_TABLE.items():
            self.assertIn(name, parsed, f"{name} missing from the SQF table")
            self.assertEqual(parsed[name], row, f"{name} row drifted")

    def test_sand_row_uses_effective_porosity(self):
        parsed = self._parsed_table()
        self.assertEqual(parsed["sand"][0], 0.417)
        self.assertNotEqual(parsed["sand"][0], 0.437)

    def test_dtheta_is_theta_e_minus_theta_i(self):
        match = re.search(r"_dTheta\s*=\s*\(\s*_thetaE\s*-\s*_thetaI\s*\)", self.text)
        self.assertIsNotNone(match, "dTheta must use _thetaE, not total porosity")

    def test_vector_evaluated_from_the_sqf_constants(self):
        """Read the sand constants out of the SQF and evaluate t(50)."""
        theta_e, psi, k = self._parsed_table()["sand"]
        _rate, _f, t = green_ampt(50, theta_e, psi, k)
        self.assertAlmostEqual(t, 0.2089, places=3)

    def test_registered_and_wired(self):
        prep = PREP_HPP.read_text(encoding="utf-8")
        river = RIVER_SQF.read_text(encoding="utf-8")
        self.assertIn("PREPS(hydrology,calculateGreenAmptInfiltration)", prep)
        self.assertIn("calculateGreenAmptInfiltration", river)


# ─── D8 routing (issue #24) ───────────────────────────────────────────────

# The fixed tie-break order: E, SE, S, SW, W, NW, N, NE, clockwise from east.
D8_OFFSETS = [[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]]


def d8_receivers(heights, nx, ny, step, offsets=None, strict=True):
    """Mirrors the receiver selection in fnc_routeRunoffD8.sqf."""
    offsets = D8_OFFSETS if offsets is None else offsets
    diag = step * math.sqrt(2)
    receivers = []
    for iy in range(ny):
        for ix in range(nx):
            h = heights[iy * nx + ix]
            best = -1
            best_slope = 0.0
            for dx, dy in offsets:
                jx, jy = ix + dx, iy + dy
                if 0 <= jx < nx and 0 <= jy < ny:
                    dist = step if (dx == 0 or dy == 0) else diag
                    slope = (h - heights[jy * nx + jx]) / dist
                    if (slope > best_slope) if strict else (slope >= best_slope):
                        best_slope = slope
                        best = jy * nx + jx
            receivers.append(best)
    return receivers


def d8_accumulate(heights, nx, ny, step):
    """Mirrors the downhill accumulation in fnc_routeRunoffD8.sqf."""
    receivers = d8_receivers(heights, nx, ny, step)
    area = [step * step] * (nx * ny)
    order = sorted(range(nx * ny), key=lambda i: (heights[i], i), reverse=True)
    for i in order:
        r = receivers[i]
        if r >= 0:
            area[r] += area[i]
    return area


class TestD8Routing(unittest.TestCase):
    def test_known_path_accumulates_exactly(self):
        """A 1x4 column, step 10: each cell drains to the next lower one."""
        heights = [40, 30, 20, 10]
        area = d8_accumulate(heights, 1, 4, 10)
        self.assertEqual(area, [100, 200, 300, 400])

    def test_flat_grid_is_all_sinks(self):
        """No lower neighbour: each cell keeps its own water."""
        area = d8_accumulate([0] * 9, 3, 3, 10)
        self.assertEqual(area, [100] * 9)

    def test_single_low_corner_collects_all_flow(self):
        """Every cell drains to the one low corner at index 0."""
        heights = [10, 20, 20, 30]
        area = d8_accumulate(heights, 2, 2, 10)
        self.assertEqual(area, [400, 100, 100, 100])

    def test_tie_resolves_consistently(self):
        """Two equal steepest slopes: the first in the order wins, twice."""
        heights = [5, 0, 0, 5]
        first = d8_accumulate(heights, 2, 2, 10)
        second = d8_accumulate(heights, 2, 2, 10)
        self.assertEqual(first, second)
        self.assertEqual(first, [100, 200, 200, 100])

    def test_slope_uses_true_distance_not_drop_alone(self):
        """A diagonal step is sqrt(2) longer, so an equal drop is gentler.

        Centre height 10, all neighbours 0. E drops 10 over 10 m (slope 1);
        SE drops 10 over 14.14 m (slope 0.707). The orthogonal E is the
        steepest, so it wins the tie among the four orthogonals.
        """
        heights = [0, 0, 0, 0, 10, 0, 0, 0, 0]
        receivers = d8_receivers(heights, 3, 3, 10)
        self.assertEqual(receivers[4], 5)  # E of centre, not the diagonal


class TestD8Source(unittest.TestCase):
    """Extract the D8 order and comparison from the SQF and evaluate them."""

    def setUp(self):
        self.text = D8_SQF.read_text(encoding="utf-8")
        self.code = self.text[self.text.index("*/") + 2 :]

    def _parsed_offsets(self):
        match = re.search(r"_neighbours\s*=\s*(\[\[.*?\]\])\s*;", self.text)
        self.assertIsNotNone(match, "no _neighbours literal found")
        return [
            [int(a), int(b)]
            for a, b in re.findall(r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]", match.group(1))
        ]

    def test_offset_order_is_the_documented_one(self):
        self.assertEqual(self._parsed_offsets(), D8_OFFSETS)

    def test_comparison_is_strict_so_the_first_wins(self):
        self.assertIn("if (_slope > _bestSlope) then", self.text)

    def test_no_random_tie_breaking(self):
        self.assertNotIn("random", self.code.lower())

    def test_tie_resolves_to_the_first_listed_direction(self):
        """Evaluate the parsed order on the tie grid.

        With the strict comparison, the first offset at the maximum slope
        wins. On the [5, 0, 0, 5] grid, index 0 ties E and S, so E (the
        first) wins; index 3 ties W and N, so W wins.
        """
        offsets = self._parsed_offsets()
        receivers = d8_receivers([5, 0, 0, 5], 2, 2, 10, offsets=offsets)
        self.assertEqual(receivers[0], 1)
        self.assertEqual(receivers[3], 2)

        # A non-strict comparison would pick the last direction instead.
        loose = d8_receivers([5, 0, 0, 5], 2, 2, 10, offsets=offsets, strict=False)
        self.assertNotEqual(receivers[0], loose[0])

    def test_accumulation_visits_high_cells_first(self):
        self.assertIn("_order sort false", self.text)

    def test_registered_and_wired(self):
        prep = PREP_HPP.read_text(encoding="utf-8")
        river = RIVER_SQF.read_text(encoding="utf-8")
        self.assertIn("PREPS(hydrology,routeRunoffD8)", prep)
        self.assertIn("routeRunoffD8", river)
        self.assertIn("_d8CatchmentM2", river)

    def test_result_is_a_flat_array(self):
        """The result is row-major, so the river can index it directly."""
        self.assertTrue(self.code.rstrip().endswith("_area"))
        self.assertIn("flat array", self.text)


if __name__ == "__main__":
    unittest.main()
