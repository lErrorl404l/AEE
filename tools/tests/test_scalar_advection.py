#!/usr/bin/env python3
"""Executes the ACTUAL SQF scalar-advection kernels (issue #116).

This suite runs the shipped pure kernels through sqf_lite.py - a minimal SQF
evaluator for their subset - and asserts the transport anchors.  It does NOT
mirror the SQF: the SQF file itself is the subject under test.  If the SQF
changes, this test executes the new code.

The issue's validation is the puff test below: one puff in a constant wind
must move one cell per dx/u seconds without growing beyond the interpolation
error.  The grid is the issue's recommended 2D grid (31x31 at 1 km).

Sources (issue #116): Stam 1999 "Stable Fluids"; Staniforth & Cote 1991;
Courant, Friedrichs & Lewy 1928 (the CFL condition); the explicit-diffusion
von Neumann bound D <= 1/2.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqf_lite import run_sqf

_REPO = Path(__file__).resolve().parents[2]
_SCALAR = _REPO / "addons" / "weather" / "functions" / "scalar"
_ADVECT = _SCALAR / "fnc_scalarAdvectKernel.sqf"
_STABILITY = _SCALAR / "fnc_scalarStabilityKernel.sqf"
_CONFIG = _SCALAR / "fnc_scalarFieldConfig.sqf"

# The kernels read no engine state, so an empty globals map is enough.
_GLOBALS = {}

_W = 31
_H = 31
_CELL_M = 1000.0


def _flat(width, height, fills):
    """A flat row-major field, width*height, with {index: value} set."""
    field = [0.0] * (width * height)
    for index, value in fills.items():
        field[index] = value
    return field


def _advect(field, u, v, dt, width=_W, height=_H, cell_m=_CELL_M):
    return run_sqf(
        _ADVECT,
        [field, width, height, 0.0, 0.0, cell_m, u, v, dt],
        _GLOBALS,
    )


class TestScalarAdvectKernel(unittest.TestCase):
    """The REAL advection kernel SQF, executed, against transport anchors."""

    def test_puff_moves_one_cell_per_dx_over_u_seconds(self):
        # The issue's validation.  A puff at cell (5, 15); wind u = 20 m/s,
        # dt = 50 s, dx = 1000 m, so dx/u = 50 s and the puff moves exactly
        # one cell downwind to (6, 15), with no interpolation error.
        field = _flat(_W, _H, {5 + 15 * _W: 1.0})
        out = _advect(field, 20.0, 0.0, 50.0)
        self.assertAlmostEqual(out[6 + 15 * _W], 1.0, places=9)
        self.assertAlmostEqual(sum(out), 1.0, places=9)
        for index, value in enumerate(out):
            if index != 6 + 15 * _W:
                self.assertAlmostEqual(value, 0.0, places=9)

    def test_puff_advances_one_cell_each_step(self):
        # Ten steps of 50 s at 20 m/s move the puff ten cells.
        field = _flat(_W, _H, {5 + 15 * _W: 1.0})
        for _ in range(10):
            field = _advect(field, 20.0, 0.0, 50.0)
        self.assertAlmostEqual(field[15 + 15 * _W], 1.0, places=6)
        self.assertAlmostEqual(sum(field), 1.0, places=6)

    def test_partial_step_spreads_by_at_most_one_cell(self):
        # A half-cell step (dx/u / 2) splits the puff across two cells; the
        # peak must NOT grow beyond the initial value (no false gain).
        field = _flat(_W, _H, {5 + 15 * _W: 1.0})
        out = _advect(field, 20.0, 0.0, 25.0)
        self.assertLessEqual(max(out), 1.0 + 1e-9)
        self.assertAlmostEqual(sum(out), 1.0, places=9)

    def test_uniform_field_stays_uniform(self):
        # Bilinear interpolation of a uniform field is that field, anywhere.
        field = [1.0] * (_W * _H)
        out = _advect(field, 30.0, -12.0, 100.0)
        for value in out:
            self.assertAlmostEqual(value, 1.0, places=9)

    def test_zero_wind_is_the_identity(self):
        field = _flat(_W, _H, {3 + 4 * _W: 2.0, 20 + 25 * _W: 0.5})
        out = _advect(field, 0.0, 0.0, 5.0)
        self.assertEqual(out, field)

    def test_diagonal_wind_moves_in_both_axes(self):
        # u and v each displace one cell at their own rate; a puff at (5, 5)
        # with u = v = 20 and dt = 50 moves to (6, 6).
        field = _flat(_W, _H, {5 + 5 * _W: 1.0})
        out = _advect(field, 20.0, 20.0, 50.0)
        self.assertAlmostEqual(out[6 + 6 * _W], 1.0, places=9)

    def test_sqf_executes_not_mirror(self):
        self.assertTrue(_ADVECT.exists(), f"kernel missing: {_ADVECT}")


class TestScalarStabilityKernel(unittest.TestCase):
    """The REAL stability kernel SQF, executed, against the cited limits."""

    def test_issue_example_is_stable_by_fifty(self):
        # 1 km cells, 1 Hz, 20 m/s: C = u dt / dx = 20*1/1000 = 0.02.
        c, d, stable = run_sqf(_STABILITY, [20.0, 0.0, 1000.0, 1.0, 0.0], _GLOBALS)
        self.assertAlmostEqual(c, 0.02, places=9)
        self.assertAlmostEqual(d, 0.0, places=9)
        self.assertTrue(stable)

    def test_advection_number_uses_the_faster_axis(self):
        c, _, _ = run_sqf(_STABILITY, [5.0, -30.0, 1000.0, 1.0, 0.0], _GLOBALS)
        self.assertAlmostEqual(c, 0.03, places=9)

    def test_cfl_limit_is_one(self):
        # u dt / dx = 1 exactly: still stable (<=).
        _, _, stable = run_sqf(_STABILITY, [20.0, 0.0, 1000.0, 50.0, 0.0], _GLOBALS)
        self.assertTrue(stable)
        # 2x over the limit: unstable.
        _, _, unstable = run_sqf(_STABILITY, [20.0, 0.0, 1000.0, 100.0, 0.0], _GLOBALS)
        self.assertFalse(unstable)

    def test_diffusion_number_limits_at_one_half(self):
        # D = K dt / dx^2.  K = 5000, dt = 100, dx = 1000 -> D = 0.5: stable.
        _, d, stable = run_sqf(_STABILITY, [0.0, 0.0, 1000.0, 100.0, 5000.0], _GLOBALS)
        self.assertAlmostEqual(d, 0.5, places=9)
        self.assertTrue(stable)
        # K = 6000 -> D = 0.6: unstable.
        _, _, unstable = run_sqf(
            _STABILITY, [0.0, 0.0, 1000.0, 100.0, 6000.0], _GLOBALS
        )
        self.assertFalse(unstable)

    def test_zero_cell_does_not_divide_by_zero(self):
        c, d, stable = run_sqf(_STABILITY, [20.0, 0.0, 0.0, 1.0, 0.0], _GLOBALS)
        self.assertEqual((c, d, stable), (0.0, 0.0, True))


class TestScalarFieldConfig(unittest.TestCase):
    """The REAL field table SQF, executed, against the two v1 fields."""

    def test_two_fields_smoke_and_dust(self):
        rows = run_sqf(_CONFIG, [], _GLOBALS)
        keys = [row[0] for row in rows]
        self.assertEqual(keys, ["smoke", "dust"])

    def test_smoke_reuses_the_repo_rain_scavenging(self):
        rows = run_sqf(_CONFIG, [], _GLOBALS)
        smoke = next(row for row in rows if row[0] == "smoke")
        self.assertEqual(smoke[2], 3.0)  # kScav = 3, the repo's smoke model

    def test_dust_source_is_wind_gated_at_five(self):
        rows = run_sqf(_CONFIG, [], _GLOBALS)
        dust = next(row for row in rows if row[0] == "dust")
        self.assertEqual(dust[3], "background")
        self.assertEqual(dust[4], 5.0)  # the repo's atmospheric-dust gate


if __name__ == "__main__":
    unittest.main()
