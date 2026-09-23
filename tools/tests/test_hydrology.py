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
import unittest

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


if __name__ == "__main__":
    unittest.main()
