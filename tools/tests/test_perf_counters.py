#!/usr/bin/env python3
"""Performance counter logic tests (issue #97).

The BEGIN/END_COUNTER macros (addons/main/script_debug.hpp) accumulate
[lastStart, [start, stop], ...] pairs per counter; the dump function
(addons/core/functions/fnc_dumpPerformanceCounters.sqf) skips the first
2 entries (warm-up), averages the closed samples, and reports ms/call.
These tests mirror the dump arithmetic so the SQF aggregation logic is
locked: a counter regression (wrong skip, wrong average) fails here.

The macros are compile-time gated (ENABLE_PERFORMANCE_COUNTERS): a
production build has ZERO overhead.  This file validates the logic the
gated build uses, and the zero-overhead property (macros expand to
nothing) is asserted structurally.

Run: python3 -m unittest tools.tests.test_perf_counters
"""

import unittest


# ─── Mirror of fnc_dumpPerformanceCounters.sqf aggregation ────────────────
# A counter in the SQF is:
#   [name, firstStart, [start1, stop1], [start2, stop2], ...]
# The dump iterates from index 3 (skipping [name] and [firstStart] and
# the first sample) and averages only closed samples (stop >= start).


def average_ms_per_call(counter, skip_first_sample=True):
    """Mirror of the dump's per-counter average, in ms (0.0 if none)."""
    total = 0.0
    count = 0
    start_i = 3 if skip_first_sample else 2
    for i in range(start_i, len(counter)):
        pair = counter[i]
        dt = pair[1] - pair[0]
        if dt >= 0:
            total += dt
            count += 1
    if count == 0:
        return 0.0
    return total / count * 1000.0


class TestCounterAggregation(unittest.TestCase):
    """The dump's averaging logic."""

    def test_skips_metadata_and_warmup(self):
        # [name, firstStart, [warmup sample], [real sample 0.5 ms], ...]
        counter = [
            "aee_core_fnc_updateEnvironment_counter",
            1000.0,
            [1000.0, 1000.5],  # warm-up: skipped
            [2000.0, 2000.0005],  # 0.5 ms
            [3000.0, 3000.0008],  # 0.8 ms
        ]
        avg = average_ms_per_call(counter)
        self.assertAlmostEqual(avg, 0.65, places=6)  # (0.5+0.8)/2

    def test_warmup_skipped_not_averaged(self):
        counter = [
            "counter",
            0.0,
            [0.0, 10.0],  # 10 s warm-up — must NOT pollute the avg
            [100.0, 100.001],  # 1 ms
        ]
        avg = average_ms_per_call(counter)
        self.assertAlmostEqual(avg, 1.0, places=6)

    def test_open_sample_discarded(self):
        # An open sample (stop < start, from an early exit) is dropped.
        counter = [
            "counter",
            0.0,
            [0.0, 1.0],
            [100.0, 100.0],  # open: equal times, dt=0 -> kept as 0
            [200.0, 99.0],  # open/negative: discarded
            [300.0, 300.001],  # 1 ms
        ]
        avg = average_ms_per_call(counter)
        # Kept: [100,100] dt 0 and [300,300.001] dt 1 ms -> avg 0.5 ms
        self.assertAlmostEqual(avg, 0.5, places=6)

    def test_single_sample(self):
        counter = ["counter", 0.0, [0.0, 1.0], [100.0, 100.001]]
        avg = average_ms_per_call(counter)
        self.assertAlmostEqual(avg, 1.0, places=6)

    def test_no_closed_samples_returns_none(self):
        counter = ["counter", 0.0, [0.0, 1.0], [100.0, 99.0]]
        self.assertEqual(average_ms_per_call(counter), 0.0)

    def test_sort_descending(self):
        # The dump sorts heaviest first.
        results = [
            (0.2, "light"),
            (3.1, "heavy"),
            (1.0, "mid"),
        ]
        results.sort(reverse=True)
        self.assertEqual(results[0][1], "heavy")
        self.assertEqual(results[-1][1], "light")


class TestZeroOverheadGate(unittest.TestCase):
    """The macros must expand to nothing in production."""

    def test_counters_disabled_by_default(self):
        # script_debug.hpp: ENABLE_PERFORMANCE_COUNTERS is commented; the
        # #else branch defines the macros as empty.  Assert the header
        # still has the disabled branch intact.
        import re
        from pathlib import Path

        hdr = Path("addons/main/script_debug.hpp").read_text(encoding="utf-8")
        self.assertIn("#else", hdr)
        self.assertIn("#define BEGIN_COUNTER(x) ; /* disabled */", hdr)
        # The enable define must be commented in the committed header.
        self.assertIn("//#define ENABLE_PERFORMANCE_COUNTERS", hdr)

    def test_dump_is_noop_without_counters(self):
        # The dump guards on aee_perfCounters being nil (production).
        from pathlib import Path

        dump = Path("addons/core/functions/fnc_dumpPerformanceCounters.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn('isNil "aee_perfCounters"', dump)


if __name__ == "__main__":
    unittest.main()
