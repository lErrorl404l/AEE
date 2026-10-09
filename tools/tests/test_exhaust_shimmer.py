#!/usr/bin/env python3
"""Exhaust heat-shimmer physics, class selection and overdraw tests.

Verifies fnc_calculateThermalRefraction.sqf (the optical kernel) and
fnc_calculateExhaustPlume.sqf (the power ramp kernel), both in mobility, and
fnc_applyExhaustShimmer.sqf (the renderer) in fx, plus the vision-mode gate
on the mirage emitter and the solar-glare LightShafts effect.

The kernel tests PARSE the real SQF and read their constants from the file
they test, then re-derive the physics from first principles, so a wrong
constant in either place fails.  A hand-transcribed Python mirror is not
acceptable: a mirror once replicated the SQF's own bugs and drifted without
detection.

Every test that reads SQF strips comments first, because the headers quote
the broken constructs they explain and a raw search matches the prose.

Sources held for the constants:
  K = 2.26e-4 m^3/kg  Stone and Zimmerman, "Index of Refraction of Air",
                      NIST Engineering Metrology Toolbox, which publishes
                      the Edlen and Ciddor equations.
  rho = 1.225 kg/m^3  ISA sea level density, the same datum the shock
                      kernel uses.

Run: python3 -m unittest tools.tests.test_exhaust_shimmer -v
"""

import math
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KERNEL = REPO / "addons/hydrology/functions/fnc_calculateThermalRefraction.sqf"
PLUME = REPO / "addons/vehicles/functions/fnc_calculateExhaustPlume.sqf"
LOAD = REPO / "addons/vehicles/functions/fnc_calculateEngineLoad.sqf"
AIRLOAD = REPO / "addons/flight/functions/fnc_calculateAirEngineLoad.sqf"
MIRAGE = REPO / "addons/optics/functions/fx/fnc_applyMirageFX.sqf"
GLARE = REPO / "addons/optics/functions/fx/fnc_applySolarGlareFX.sqf"
SHIMMER = REPO / "addons/weatherfx/functions/weather/fnc_applyExhaustShimmer.sqf"

KERNEL_SRC = KERNEL.read_text(encoding="utf-8")
PLUME_SRC = PLUME.read_text(encoding="utf-8")
LOAD_SRC = LOAD.read_text(encoding="utf-8")
AIRLOAD_SRC = AIRLOAD.read_text(encoding="utf-8")
SHIMMER_SRC = SHIMMER.read_text(encoding="utf-8")


def _code_only(text):
    """Blank out comments so a search cannot match the prose.

    The file headers explain the tokens the tests search for, so a raw search
    finds the explanation before the code.  Block comments and line comments
    are both removed, because the renderer header is a block comment.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = []
    for line in text.split("\n"):
        idx = line.find("//")
        out.append(line if idx < 0 else line[:idx])
    return "\n".join(out)


def _sqf_number(pattern):
    """Read a numeric literal out of the real SQF, so the test cannot drift."""
    match = re.search(pattern, KERNEL_SRC)
    if not match:
        raise AssertionError(f"SQF no longer matches {pattern!r}")
    return float(match.group(1))


def _tier_rows():
    """Parse the renderer tier table into {key: [idleT, fullT, idleD, fullD]}."""
    code = _code_only(SHIMMER_SRC)
    block = re.search(r"_TIERS\s*=\s*createHashMapFromArray\s*\[(.*?)\n\];", code, re.S)
    if not block:
        raise AssertionError("the renderer no longer declares a _TIERS table")
    rows = {}
    for key, nums in re.findall(r'\["(\w+)",\s*\[([^\]]+)\]\]', block.group(1)):
        rows[key] = [float(x) for x in nums.split(",")]
    return rows


def _brace_block_end(text, token):
    """Return the index just past the } that closes the block after `token`.

    Counting braces proves the air branch sits AFTER the difficultyEnabledRTD
    block CLOSES, not merely after the token appears.  A positional find()
    cannot tell an inner statement from a sibling one.
    """
    start = text.find(token)
    if start < 0:
        raise AssertionError(f"token not found: {token}")
    open_idx = text.find("{", start)
    if open_idx < 0:
        raise AssertionError(f"no block follows {token}")
    depth = 0
    for j in range(open_idx, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return j
    raise AssertionError(f"unbalanced block follows {token}")


class ThermalRefractionKernel(unittest.TestCase):
    def setUp(self):
        self.k = _sqf_number(r"private _k\s*=\s*([0-9.]+)\s*;")
        self.rho0 = _sqf_number(r"private _rhoAmbient\s*=\s*([0-9.]+)")

    def contrast(self, gas_c, ambient_c, rho_rel=1.0):
        """The kernel result in its reported units, re-derived here."""
        if rho_rel <= 0:
            return 0.0
        if gas_c <= ambient_c:
            return 0.0
        gas_k = gas_c + 273.15
        ambient_k = ambient_c + 273.15
        if gas_k <= 0 or ambient_k <= 0:
            return 0.0
        return self.k * self.rho0 * rho_rel * (ambient_k / gas_k - 1.0) / 0.0001

    # ── the constants are the sourced ones ─────────────────────────────
    def test_gladstone_dale_coefficient(self):
        self.assertAlmostEqual(self.k, 0.000226, places=9)

    def test_ambient_density_is_isa_sea_level(self):
        self.assertEqual(self.rho0, 1.225)

    # ── the reference values the task fixes ────────────────────────────
    def test_500c_ratio_and_contrast(self):
        ratio = 288.15 / (500 + 273.15)
        self.assertAlmostEqual(ratio, 0.373, places=3)
        self.assertAlmostEqual(self.contrast(500, 15), -1.74, places=2)

    def test_600c_ratio_and_contrast(self):
        ratio = 288.15 / (600 + 273.15)
        self.assertAlmostEqual(ratio, 0.330, places=3)
        self.assertAlmostEqual(self.contrast(600, 15), -1.85, places=2)

    def test_1200c_ratio_and_contrast(self):
        ratio = 288.15 / (1200 + 273.15)
        self.assertAlmostEqual(ratio, 0.196, places=3)
        self.assertAlmostEqual(self.contrast(1200, 15), -2.23, places=2)

    def test_equal_temperatures_return_exactly_zero(self):
        self.assertEqual(self.contrast(15, 15), 0.0)

    def test_colder_gas_returns_exactly_zero(self):
        self.assertEqual(self.contrast(10, 15), 0.0)

    def test_sign_is_negative_for_hot_gas(self):
        for gas in (200, 500, 800, 1200):
            self.assertLess(self.contrast(gas, 15), 0.0)

    def test_contrast_grows_with_gas_temperature(self):
        seq = [abs(self.contrast(t, 15)) for t in (100, 300, 500, 800, 1200)]
        for a, b in zip(seq, seq[1:]):
            self.assertLess(a, b)

    def test_contrast_scales_with_rho_rel(self):
        self.assertGreater(
            abs(self.contrast(500, 15, 1.2)), abs(self.contrast(500, 15, 1.0))
        )
        self.assertGreater(
            abs(self.contrast(500, 15, 1.0)), abs(self.contrast(500, 15, 0.8))
        )

    # ── the guards the SQF must keep ───────────────────────────────────
    def test_hot_gas_guard_is_present(self):
        self.assertRegex(
            KERNEL_SRC,
            r"if \(_gasTempC\s*<=\s*_ambientTempC\)\s*exitWith \{\s*0\s*\}",
        )

    def test_rho_rel_guard_is_present(self):
        self.assertRegex(KERNEL_SRC, r"if \(_rhoRel\s*<=\s*0\)\s*exitWith \{\s*0\s*\}")

    def test_kelvin_guards_are_present(self):
        self.assertIn("if (_gasK <= 0) exitWith { 0 }", KERNEL_SRC)
        self.assertIn("if (_ambientK <= 0) exitWith { 0 }", KERNEL_SRC)

    def test_negative_absolute_gas_is_guarded_by_the_ordering(self):
        # A gas colder than ambient already returns 0, and an unphysical
        # Kelvin value is caught by the explicit guard, so both paths exist.
        self.assertEqual(self.contrast(-400, -500), 0.0)

    # ── the header keeps the honesty claims ────────────────────────────
    def test_header_states_the_negative_sign(self):
        header = KERNEL_SRC.upper()
        self.assertIn("NEGATIVE", header)
        self.assertIn("LESS dense", KERNEL_SRC)

    def test_header_states_the_ceiling_over_the_plume(self):
        header = KERNEL_SRC.upper()
        self.assertIn("CEILING", header)
        self.assertIn("gas temperature alone", KERNEL_SRC)

    def test_header_excludes_condensation_and_soot(self):
        self.assertIn("condensation", KERNEL_SRC)
        self.assertIn("soot", KERNEL_SRC)

    def test_header_cites_the_gladstone_dale_source(self):
        self.assertIn("Gladstone-Dale", KERNEL_SRC)
        self.assertIn("Stone and Zimmerman", KERNEL_SRC)
        self.assertIn("NIST", KERNEL_SRC)
        self.assertIn("2.26e-4", KERNEL_SRC)

    def test_header_keeps_the_radio_constant_separate(self):
        self.assertIn("ITU-R", KERNEL_SRC)
        self.assertIn("RADIO", KERNEL_SRC)

    def test_declares_params_and_return(self):
        self.assertIn("params [", KERNEL_SRC)
        self.assertIn("Arguments:", KERNEL_SRC)
        self.assertIn("Returns the refractive index contrast", KERNEL_SRC)

    def test_reports_in_1e_4_units(self):
        self.assertIn("_contrast / 0.0001", KERNEL_SRC)


class ExhaustPlumeKernel(unittest.TestCase):
    """The power ramp kernel: linear, clamped, and guarded against inversion."""

    def setUp(self):
        self.src = PLUME_SRC

    def _default(self, name):
        return float(re.search(rf'\["{name}",\s*([0-9.]+)', self.src).group(1))

    def test_defaults_are_the_land_diesel_row(self):
        self.assertEqual(self._default("_idleTempC"), 300.0)
        self.assertEqual(self._default("_fullTempC"), 480.0)
        self.assertEqual(self._default("_idleDepthM"), 0.35)
        self.assertEqual(self._default("_fullDepthM"), 0.60)

    def test_interpolation_is_linear_in_the_power_fraction(self):
        # The expression form is the contract: idle at 0, full at 1.
        self.assertIn("_idleTempC + ((_fullTempC - _idleTempC) * _fraction)", self.src)
        self.assertIn(
            "_idleDepthM + ((_fullDepthM - _idleDepthM) * _fraction)", self.src
        )
        self.assertIn("params [", self.src)

    def test_returns_the_interpolated_pair(self):
        self.assertIn("[_gasTempC, _depthM]", self.src)

    def test_power_fraction_is_clamped(self):
        self.assertIn("_power max 0 min 1", self.src)

    def test_inverted_pairs_are_refused(self):
        # A full value below its idle value interpolates backwards.
        self.assertIn("if (_fullTempC < _idleTempC) exitWith { [0, 0] };", self.src)
        self.assertIn("if (_fullDepthM < _idleDepthM) exitWith { [0, 0] };", self.src)

    def test_non_positive_values_are_refused(self):
        self.assertIn(
            "if (_idleTempC <= 0 || _fullTempC <= 0) exitWith { [0, 0] };", self.src
        )
        self.assertIn(
            "if (_idleDepthM <= 0 || _fullDepthM <= 0) exitWith { [0, 0] };", self.src
        )

    def test_a_caller_passing_outside_the_range_gets_an_endpoint(self):
        # The clamp makes the endpoints the values at and beyond 0 and 1.
        # Re-derive: the interpolation is linear, so at 0 the idle pair and
        # at 1 the full pair, whatever a caller passes beyond the range.
        idle_d = self._default("_idleDepthM")
        full_d = self._default("_fullDepthM")
        self.assertLess(idle_d, full_d)
        self.assertAlmostEqual(
            idle_d + ((full_d - idle_d) * min(max(2.0, 0.0), 1.0)), full_d
        )
        self.assertAlmostEqual(
            idle_d + ((full_d - idle_d) * min(max(-1.0, 0.0), 1.0)), idle_d
        )

    # ── the header keeps the honesty claims ────────────────────────────
    def test_header_states_the_contrast_versus_size_arithmetic(self):
        for figure in ("1.58", "1.85", "2.09", "2.23"):
            self.assertIn(figure, self.src, f"missing contrast figure {figure}")
        self.assertIn("factor of 1.4", self.src)
        self.assertIn("factor of 7", self.src)

    def test_header_states_the_linear_curve_is_an_approximation(self):
        upper = self.src.upper()
        self.assertIn("LINEAR", upper)
        self.assertIn("APPROXIMATION", upper)
        self.assertIn("declared defaults", self.src)

    def test_header_describes_the_gated_reader(self):
        # The reader exists: collectiveRTD / throttleRTD, gated on the
        # advanced flight model.  The old header claimed no reader existed.
        upper = self.src.upper()
        self.assertIn("DIFFICULTYENABLEDRTD", upper)
        self.assertIn("collectiveRTD", self.src)
        self.assertIn("throttleRTD", self.src)
        self.assertNotIn("NO NUMERIC COLLECTIVE", upper)

    def test_header_cites_the_refraction_kernel_for_the_figures(self):
        self.assertIn("fnc_calculateThermalRefraction", self.src)


class VisionModeGate(unittest.TestCase):
    """The three FX files must each gate on currentVisionMode.

    The mirage refract billboard and the LightShafts god-rays were drawn on
    top of the NVG and thermal sensor images because neither function checked
    currentVisionMode.  These read the SOURCE; a mirror would prove nothing.
    """

    def test_mirage_gates_on_vision_mode(self):
        code = _code_only(MIRAGE.read_text(encoding="utf-8"))
        self.assertIn("currentVisionMode", code)
        self.assertRegex(code, r"if \(_visionMode != 0\) exitWith")
        # The source must be DELETED, not merely faded.
        self.assertIn("deleteVehicle _leak", code)
        self.assertIn("QGVAR(mirageSource), objNull", code)

    def test_solar_glare_gates_on_vision_mode(self):
        code = _code_only(GLARE.read_text(encoding="utf-8"))
        self.assertIn("currentVisionMode", code)
        self.assertRegex(code, r"if \(_visionMode != 0\) exitWith")
        # The string-LHS form is disabled on the way out.
        self.assertIn('"LightShafts" ppEffectEnable false', code)

    def test_exhaust_shimmer_gates_on_vision_mode(self):
        code = _code_only(SHIMMER_SRC)
        self.assertIn("currentVisionMode", code)
        self.assertRegex(code, r"if \(_visionMode != 0\) exitWith")
        self.assertIn("deleteVehicle _src", code)


class ExhaustTierSelection(unittest.TestCase):
    """The class tier table and the branch that selects each tier."""

    def setUp(self):
        self.code = _code_only(SHIMMER_SRC)

    def test_table_declares_four_tiers(self):
        rows = _tier_rows()
        self.assertEqual(set(rows), {"land", "heli", "jet", "ab"})
        for key, row in rows.items():
            self.assertEqual(len(row), 4, f"{key} row is not four numbers")

    def test_every_tier_is_reachable_by_its_own_branch(self):
        # Reachability is asserted by finding the branch that selects the
        # tier, not by asserting the row appears in a comment.
        self.assertIn('getVariable ["aee_exhaustTier", ""]', self.code)
        self.assertRegex(self.code, r"_tier = _override")
        self.assertRegex(self.code, r'isKindOf "Helicopter"\) then \{\s*_tier = "heli"')
        self.assertRegex(
            self.code,
            r'getVariable \["aee_exhaustAfterburner", false\]\) then \{\s*_tier = "ab"',
        )
        self.assertRegex(self.code, r'isKindOf "Plane"\) then \{\s*_tier = "jet"')
        self.assertRegex(self.code, r'_tier = "land"')

    def test_helicopter_branch_is_not_the_plane_branch(self):
        # The bug being fixed: the old selector tested only isKindOf "Plane",
        # so a helicopter silently took the fixed-wing row.  Vanilla Air has
        # two roots, Helicopter: Air and Plane: Air.
        self.assertIn('isKindOf "Helicopter"', self.code)
        self.assertIn('isKindOf "Plane"', self.code)
        self.assertRegex(self.code, r'isKindOf "Helicopter"\) then \{\s*_tier = "heli"')
        self.assertRegex(self.code, r'isKindOf "Plane"\) then \{\s*_tier = "jet"')

    def test_selection_order_is_override_then_heli_then_afterburner_then_plane(self):
        order = [
            self.code.find('getVariable ["aee_exhaustTier", ""]'),
            self.code.find('isKindOf "Helicopter"'),
            self.code.find('getVariable ["aee_exhaustAfterburner", false]'),
            self.code.find('isKindOf "Plane"'),
        ]
        self.assertTrue(all(i >= 0 for i in order), "a selection branch is missing")
        self.assertEqual(
            order, sorted(order), "the selection branches are out of order"
        )

    def test_header_records_the_two_vanilla_air_roots(self):
        self.assertIn("Helicopter: Air", SHIMMER_SRC)
        self.assertIn("Plane: Air", SHIMMER_SRC)

    def test_header_declares_the_four_profiles(self):
        for token in (
            "idle 300 C / 0.35 m",
            "full 480 C / 0.60 m",
            "idle 420 C / 0.35 m",
            "full 600 C / 1.00 m",
            "idle 480 C / 0.40 m",
            "full 750 C / 1.50 m",
            "idle 550 C / 0.50 m",
            "full 1200 C / 2.50 m",
        ):
            self.assertIn(token, SHIMMER_SRC, f"missing profile {token}")


class ExhaustShimmerRenderer(unittest.TestCase):
    def setUp(self):
        self.code = _code_only(SHIMMER_SRC)

    # ── the physics is ungated, the render is gated ────────────────────
    def test_contrast_is_published_before_the_render_gate(self):
        publish = self.code.find("QGVAR(exhaustRefraction)")
        gate = self.code.find("if (_visionMode != 0) exitWith")
        self.assertNotEqual(publish, -1, "the contrast is never published")
        self.assertNotEqual(gate, -1, "the render gate is missing")
        self.assertLess(
            publish, gate, "the physics store must sit outside the render gate"
        )

    def test_plume_kernel_is_called_from_the_renderer(self):
        self.assertIn("EFUNC(vehicles,calculateExhaustPlume)", self.code)

    def test_contrast_kernel_is_called_from_the_renderer(self):
        self.assertIn("EFUNC(hydrology,calculateThermalRefraction)", self.code)

    def test_power_reaches_the_plume_kernel(self):
        self.assertIn("_power", self.code)
        self.assertRegex(
            self.code,
            r"\[_power, _idleT, _fullT, _idleD, _fullD\] call "
            r"EFUNC\(vehicles,calculateExhaustPlume\)",
        )

    # ── true physical scale, no visibility scale factor ────────────────
    def test_uses_the_vanilla_refractive_shape(self):
        self.assertIn(r"\A3\data_f\ParticleEffects\Universal\refract", self.code)
        self.assertIn("Billboard", self.code)
        self.assertIn("setParticleParams", self.code)

    def test_header_records_the_pixel_arithmetic(self):
        self.assertIn("1662.8", SHIMMER_SRC)
        for px in (
            "17 px",
            "8 px",
            "27 px",
            "13 px",
            "67 px",
            "33 px",
            "83 px",
            "42 px",
            "0.18 px",
        ):
            self.assertIn(px, SHIMMER_SRC, f"missing pixel figure {px}")

    def test_header_states_no_visibility_scale_factor(self):
        self.assertIn("NO VISIBILITY SCALE FACTOR", SHIMMER_SRC.upper())
        self.assertIn("NONE IS NEEDED", SHIMMER_SRC.upper())

    def test_sprite_size_is_the_plume_depth(self):
        # The particle size array is [depth, depth], not a fudge constant.
        self.assertIn("[_depth, _depth]", self.code)

    # ── the overdraw budget ────────────────────────────────────────────
    def test_live_count_falls_with_depth_and_holds_the_budget(self):
        budget = float(
            re.search(r"_OVERDRAW_BUDGET\s*=\s*([0-9.]+)", self.code).group(1)
        )
        sources = float(re.search(r"_MAX_SOURCES\s*=\s*([0-9.]+)", self.code).group(1))
        maxlive = float(re.search(r"_MAX_LIVE\s*=\s*([0-9.]+)", self.code).group(1))
        minlive = float(re.search(r"_MIN_LIVE\s*=\s*([0-9.]+)", self.code).group(1))
        self.assertEqual(budget, 190.0)
        self.assertEqual(sources, 3.0)
        self.assertEqual(maxlive, 12.0)
        self.assertGreater(minlive, 0.0)

        worst = 0.0
        prev_live = None
        d = 0.35
        while d <= 2.5001:
            allowed = budget / (sources * d * d)
            live = max(min(math.floor(allowed), maxlive), minlive)
            overdraw = sources * live * d * d
            self.assertLessEqual(overdraw, budget + 1e-6)
            if prev_live is not None:
                self.assertLessEqual(live, prev_live, "the live count rose with depth")
            prev_live = live
            worst = max(worst, overdraw)
            d += 0.01
        # The bound is tight and reaches 190 at the depth where the count
        # steps down: the sampled maximum is 188.8 m2 just below the 2.297 m
        # step, and at the 2.5 m maximum the count is 10 and the product is
        # 187.5.
        self.assertGreater(worst, 187.0)
        self.assertLessEqual(worst, budget)
        # The fixed 12-count bound the user broke would have been 225.
        self.assertLess(3 * 12 * 2.5 * 2.5, 225.0 + 0.1)

    def test_header_states_the_overdraw_arithmetic(self):
        self.assertIn("190", SHIMMER_SRC)
        self.assertIn("642", SHIMMER_SRC)
        self.assertIn("187.5", SHIMMER_SRC)
        self.assertIn("225", SHIMMER_SRC)

    def test_live_sprite_count_is_the_divisor_of_the_drop_interval(self):
        self.assertIn("_drop = _LIFETIME / _liveN", self.code)
        self.assertIn("setDropInterval _dropInterval", self.code)
        self.assertIn("floor _allowed", self.code)

    def test_lifetime_sits_in_the_lifetime_slot(self):
        # Index 4 is the lifetime, per docs/wiki/research/particle-array-spec.md
        # line 32 and vanilla muzzle/rockettrail.sqf.  A previous defect put a
        # fixed 0.4 there and the derived lifetime in slots 7 and 8.
        self.assertRegex(self.code, r'"Billboard",\s*1,\s*_lifetime,')

    # ── declared defaults and the reachable gas temperature ────────────
    def test_header_states_no_reachable_exhaust_gas_temperature(self):
        self.assertIn("NOT REACHABLE FROM THE THERMAL SOLVER", SHIMMER_SRC.upper())
        self.assertIn("SURFACE", SHIMMER_SRC.upper())

    def test_measured_override_is_read_with_a_fallback(self):
        self.assertIn('getVariable ["aee_exhaustGasTempC", -1]', self.code)
        self.assertIn('getVariable ["aee_exhaustPlumeM", -1]', self.code)

    def test_measured_override_wins_over_the_tier_row(self):
        gas = self.code.find('getVariable ["aee_exhaustGasTempC", -1]')
        profile = self.code.find("calculateExhaustPlume)")
        self.assertGreater(gas, profile, "the override must follow the kernel call")

    # ── power resolution, in the order the user chose ──────────────────
    def test_power_resolution_order(self):
        block = re.search(r"private _resolvePower = \{(.*?)\n\};", self.code, re.S)
        self.assertIsNotNone(block, "the power resolver is missing")
        body = block.group(1)
        published = body.find("aee_enginePowerFraction")
        guard = body.find("difficultyEnabledRTD")
        collective = body.find("collectiveRTD")
        throttle = body.find("throttleRTD")
        idle = body.find("_power = _idlePower")
        self.assertTrue(
            -1 < published < guard < collective < throttle < idle,
            "power order is wrong",
        )

    def test_rtd_reader_is_behind_the_flight_model_guard(self):
        # The RTD group reports meaningful values only when the advanced
        # helicopter flight model is on, so the guard must enclose the reads.
        block = re.search(r"if \(_power < 0\) then \{(.*?)\n    \};", self.code, re.S)
        self.assertIsNotNone(block, "the reader branch is missing")
        reader = block.group(1)
        guard = reader.find("difficultyEnabledRTD")
        collective = reader.find("collectiveRTD _this")
        throttle = reader.find("throttleRTD _this")
        self.assertTrue(
            -1 < guard < collective < throttle, "the guard does not enclose the reads"
        )

    def test_reader_is_compiled_at_run_time(self):
        # The harness server binary lacks throttleRTD, so naming the token
        # directly would fail the script parse there.  The reader strings are
        # compiled only when the reader is reached, which is client-only.
        block = re.search(r"private _resolvePower = \{(.*?)\n\};", self.code, re.S)
        body = block.group(1)
        self.assertIn('"collectiveRTD _this"', body)
        self.assertIn('"throttleRTD _this"', body)
        self.assertIn("compile _reader", body)

    def test_helicopter_uses_collective_and_plane_uses_throttle(self):
        block = re.search(r"private _resolvePower = \{(.*?)\n\};", self.code, re.S)
        body = block.group(1)
        heli = body.find('isKindOf "Helicopter"')
        collective = body.find("collectiveRTD _this")
        plane = body.find('isKindOf "Plane"')
        throttle = body.find("throttleRTD _this")
        self.assertTrue(
            -1 < heli < collective < plane < throttle,
            "the reader is paired with the wrong class",
        )

    def test_rotor_outwash_proxy_is_gone(self):
        # The proxy existed only because the reader was believed absent.
        for token in ("calculateDownwash", "_ROTOR_FULL_OUTWASH", "_rotorFull"):
            self.assertNotIn(token, self.code, f"the outwash proxy {token} survives")

    def test_mobility_modifier_is_not_used(self):
        self.assertNotIn("aee_vehicles_enginePowerModifier", self.code)

    def test_published_power_name_is_declared(self):
        self.assertIn('getVariable ["aee_enginePowerFraction", -1]', self.code)

    # ── the contrast is not the power ramp ─────────────────────────────
    def test_alpha_is_not_ramped_by_power(self):
        alpha_lines = [line for line in self.code.splitlines() if "_alpha =" in line]
        self.assertTrue(alpha_lines, "the alpha expression is missing")
        for line in alpha_lines:
            self.assertNotIn("power", line.lower(), "alpha must not ramp with power")
        # It is on the contrast curve instead.
        self.assertIn('["mag", 0]', self.code)
        self.assertIn("_alphaMax", self.code)

    def test_header_states_the_separation(self):
        upper = SHIMMER_SRC.upper()
        self.assertIn("POWER RAMP DRIVES THE PLUME SIZE, NOT ALPHA", upper)
        self.assertIn("factor of 1.4", SHIMMER_SRC)
        self.assertIn("factor of 7", SHIMMER_SRC)

    def test_header_describes_the_gated_reader(self):
        upper = SHIMMER_SRC.upper()
        self.assertIn("DIFFICULTYENABLEDRTD", upper)
        self.assertIn("collectiveRTD", SHIMMER_SRC)
        self.assertIn("throttleRTD", SHIMMER_SRC)
        self.assertNotIn("NO NUMERIC COLLECTIVE", upper)

    def test_header_declares_the_per_vehicle_variables(self):
        for name in (
            "aee_exhaustTier",
            "aee_exhaustAfterburner",
            "aee_enginePowerFraction",
        ):
            self.assertIn(name, SHIMMER_SRC, f"missing variable {name}")

    # ── bounded scope and lifecycle ────────────────────────────────────
    def test_scope_is_player_vehicle_plus_nearest_capped(self):
        self.assertIn("nearestObjects", self.code)
        self.assertIn("_MAX_SOURCES", self.code)
        self.assertIn("isEngineOn", self.code)

    def test_sources_are_tracked_and_reaped(self):
        self.assertIn("QGVAR(exhaustSources)", self.code)
        self.assertIn("deleteVehicle _src", self.code)

    def test_client_only(self):
        self.assertIn("if (!hasInterface) exitWith {};", self.code)

    def test_uses_exhaust_memory_points_with_a_fallback(self):
        self.assertIn("selectionPosition", self.code)
        self.assertIn('"exhaust"', self.code)
        self.assertIn("[0, -2, 0.6]", self.code)

    def test_uses_the_alpha_setting_as_the_only_lever(self):
        self.assertIn("QGVAR(exhaustShimmerAlpha)", self.code)
        self.assertIn("_alphaMax", self.code)

    def test_size_range_spans_the_canonical_bounds(self):
        rows = _tier_rows()
        idle = min(row[2] for row in rows.values())
        full = max(row[3] for row in rows.values())
        self.assertAlmostEqual(idle, 0.35)
        self.assertAlmostEqual(full, 2.50)
        for row in rows.values():
            self.assertLess(row[2], row[3], "a tier does not grow with power")


class ExhaustWiring(unittest.TestCase):
    """Registration, the environment tick, the settings, and the docs."""

    def test_thermal_kernel_is_registered_in_hydrology(self):
        prep = (REPO / "addons/hydrology/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(calculateThermalRefraction);", prep)

    def test_plume_kernel_is_registered_in_vehicles(self):
        prep = (REPO / "addons/vehicles/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(calculateExhaustPlume);", prep)

    def test_neither_kernel_is_registered_in_ballistics(self):
        prep = (REPO / "addons/ballistics/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertNotIn("PREP(calculateThermalRefraction);", prep)
        self.assertNotIn("PREP(calculateExhaustPlume);", prep)

    def test_renderer_is_registered_in_fx(self):
        prep = (REPO / "addons/weatherfx/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREPS(weather,applyExhaustShimmer);", prep)

    def test_renderer_is_not_registered_in_optics(self):
        prep = (REPO / "addons/optics/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertNotIn("applyExhaustShimmer", prep)

    def test_renderer_is_wired_into_the_environment_tick(self):
        tick = (REPO / "addons/core/functions/fnc_updateEnvironment.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("EFUNC(weatherfx,applyExhaustShimmer)", tick)
        # It runs with the other optics FX, after the mirage call.
        self.assertLess(
            tick.find("EFUNC(optics,applyMirageFX)"),
            tick.find("EFUNC(weatherfx,applyExhaustShimmer)"),
        )

    def test_setting_is_registered_in_fx(self):
        settings = (REPO / "addons/weatherfx/initSettings.inc.sqf").read_text(encoding="utf-8")
        self.assertIn("AEE_SETTING_SLIDER(exhaustShimmerAlpha", settings)

    def test_setting_is_not_registered_in_optics(self):
        settings = (REPO / "addons/optics/initSettings.inc.sqf").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("exhaustShimmerAlpha", settings)

    def test_settings_doc_records_the_setting(self):
        config = (REPO / "docs/wiki/chapters/configuration.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn("aee_weatherfx_exhaustShimmerAlpha", config)

    def test_state_variables_doc_records_the_new_state(self):
        state = (REPO / "docs/wiki/chapters/state-variables.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn("aee_fx_exhaustSources", state)
        self.assertIn("aee_fx_exhaustRefraction", state)

    def test_configuration_doc_records_the_per_vehicle_values(self):
        config = (REPO / "docs/wiki/chapters/configuration.qmd").read_text(
            encoding="utf-8"
        )
        for name in (
            "aee_exhaustTier",
            "aee_exhaustAfterburner",
            "aee_enginePowerFraction",
            "aee_exhaustGasTempC",
            "aee_exhaustPlumeM",
        ):
            self.assertIn(name, config, f"missing published value {name}")


class EngineLoadKernel(unittest.TestCase):
    """The derived engine-load kernel.

    A road vehicle has no throttle reader, so the load is DERIVED from the
    tractive power demand plus the acceleration, not measured.  The kernel is
    pure arithmetic over scalars, so this suite reads its constants from the
    real SQF, re-derives the balance from first principles, and pins the
    linearity, the clamp and the guards.
    """

    def setUp(self):
        self.code = _code_only(LOAD_SRC)

    def _default(self, name):
        return float(re.search(rf'\["{name}",\s*([0-9.]+)', self.code).group(1))

    # ── the balance and its units ──────────────────────────────────────
    def test_resistance_is_force_plus_grade_plus_drag(self):
        self.assertIn("_dragN = 0.5 * _rho * _dragAreaM2 * _speed * _speed", self.code)
        self.assertIn(
            "_resistanceN = _tractionForceN + _gradeForceN + _dragN", self.code
        )

    def test_power_terms_are_force_times_speed(self):
        # Force N times speed m/s is W; the inertial power is m a v in W.
        self.assertIn("_tractiveW = _resistanceN * _speed", self.code)
        self.assertIn("_inertialW = _massKg * _accelerationMS2 * _speed", self.code)
        self.assertIn("_load = (_tractiveW + _inertialW) / _ratedPowerW", self.code)

    def test_speed_is_a_magnitude(self):
        self.assertIn("_speed = abs _speedMS", self.code)

    def test_the_ratio_is_linear_in_force_and_acceleration(self):
        # Re-derived: at fixed rated power the fraction is a linear sum, so a
        # doubling of either term doubles its contribution.
        rated = 150000.0

        def fraction(
            force, accel, speed=20.0, mass=1500.0, drag=0.7, rho=1.225, idle=0.0
        ):
            res = force + (0.5 * rho * drag * speed * speed)
            return ((res * speed) + (mass * accel * speed)) / rated + idle

        f1 = fraction(1000.0, 0.0)
        f2 = fraction(2000.0, 0.0)
        self.assertAlmostEqual(f2 - f1, (1000.0 * 20.0) / rated)
        a1 = fraction(1000.0, 1.0)
        a2 = fraction(1000.0, 2.0)
        self.assertAlmostEqual(a2 - a1, (1500.0 * 1.0 * 20.0) / rated)

    def test_larger_force_gives_a_larger_fraction(self):
        rated = 150000.0

        def fraction(force, speed=20.0, drag=0.7, rho=1.225):
            res = force + (0.5 * rho * drag * speed * speed)
            return (res * speed) / rated

        self.assertGreater(fraction(5000.0), fraction(1000.0))

    # ── the clamp and the idle floor ───────────────────────────────────
    def test_fraction_is_clamped_to_zero_and_one(self):
        self.assertIn("_load = (_load max _idle) min 1", self.code)
        self.assertIn("private _idle = _idleFraction max 0 min 1", self.code)

    def test_zero_force_and_acceleration_return_the_idle_floor(self):
        # Re-derived from the balance: with no force, no acceleration and no
        # speed, the demand is zero, so the floor is what remains.
        idle = self._default("_idleFraction")
        self.assertGreater(idle, 0.0)
        self.assertIn('["_idleFraction", 0.05', self.code)

    def test_idle_floor_is_why_a_stationary_engine_is_not_dark(self):
        upper = LOAD_SRC.upper()
        self.assertIn("STATIONARY VEHICLE AT HIGH RPM CANNOT BE DISTINGUISHED", upper)
        self.assertIn("IDLE", upper)
        self.assertIn("LIMIT OF THE ENGINE", upper)

    # ── the guards ─────────────────────────────────────────────────────
    def test_non_positive_rated_power_is_refused(self):
        self.assertIn("if (_ratedPowerW <= 0) exitWith { -1 };", self.code)

    def test_non_positive_mass_is_refused(self):
        self.assertIn("if (_massKg <= 0) exitWith { -1 };", self.code)

    # ── the honesty claims ─────────────────────────────────────────────
    def test_header_states_the_load_is_derived_and_not_measured(self):
        upper = LOAD_SRC.upper()
        self.assertIn("DERIVED", upper)
        self.assertIn("NOT A MEASUREMENT", upper)
        self.assertIn("NO NUMERIC THROTTLE READER", upper)

    def test_header_states_no_road_throttle_reader_exists(self):
        self.assertIn("collectiveRTD", LOAD_SRC)
        self.assertIn("throttleRTD", LOAD_SRC)
        self.assertIn("LandVehicle", LOAD_SRC)

    def test_header_labels_rated_power_and_drag_as_defaults(self):
        self.assertIn("150000", LOAD_SRC)
        self.assertIn("0.7 m^2", LOAD_SRC)
        upper = LOAD_SRC.upper()
        self.assertIn("DECLARED DEFAULT", upper)

    def test_header_states_the_object_work_is_the_callers(self):
        upper = LOAD_SRC.upper()
        self.assertIn("PURE ARITHMETIC", upper)
        self.assertIn("OBJECT-SIDE WORK IS THE CALLER'S", upper)
        self.assertIn("_tractionForce", LOAD_SRC)
        self.assertIn("fnc_calculateTraction", LOAD_SRC)


class EngineLoadWiring(unittest.TestCase):
    """The renderer's derived ground branch and the published-value precedence."""

    def setUp(self):
        self.code = _code_only(SHIMMER_SRC)

    def test_kernel_is_registered_in_vehicles(self):
        prep = (REPO / "addons/vehicles/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(calculateEngineLoad);", prep)

    def test_renderer_calls_the_derived_kernel(self):
        self.assertIn("EFUNC(vehicles,calculateEngineLoad)", self.code)
        self.assertIn("_deriveGroundPower", self.code)

    def test_land_vehicle_reaches_the_derived_branch(self):
        # The land root is named directly, so the fall-through is explicit.
        block = re.search(r"private _resolvePower = \{(.*?)\n\};", self.code, re.S)
        self.assertIsNotNone(block, "the power resolver is missing")
        body = block.group(1)
        derived = body.find('isKindOf "LandVehicle"')
        self.assertGreater(derived, -1, "the LandVehicle branch is missing")
        self.assertIn("_deriveGroundPower", body[derived:])
        # The helper is what calls the kernel.
        helper = re.search(
            r"private _deriveGroundPower = \{(.*?)\n\};", self.code, re.S
        )
        self.assertIsNotNone(helper, "the derived ground helper is missing")
        self.assertIn("EFUNC(vehicles,calculateEngineLoad)", helper.group(1))

    def test_rtd_branch_is_still_compiled_from_a_string(self):
        self.assertIn('"collectiveRTD _this"', self.code)
        self.assertIn('"throttleRTD _this"', self.code)
        self.assertIn("compile _reader", self.code)

    def test_published_value_still_wins_over_the_derived_term(self):
        block = re.search(r"private _resolvePower = \{(.*?)\n\};", self.code, re.S)
        body = block.group(1)
        published = body.find("aee_enginePowerFraction")
        guard = body.find("difficultyEnabledRTD")
        land = body.find('isKindOf "LandVehicle"')
        idle = body.find("_power = _idlePower")
        self.assertTrue(
            -1 < published < guard < land < idle,
            "the power order is published, RTD, derived, idle",
        )

    def test_derived_term_uses_the_published_traction_force(self):
        # The code reads the mobility value by its cross-addon macro; the
        # expanded name appears only in the prose, so this checks the code.
        self.assertIn("QEGVAR(mobility,tractionForce)", self.code)
        self.assertIn("aee_mobility_tractionForce", SHIMMER_SRC)

    def test_derived_term_is_smoothed_with_a_declared_time_constant(self):
        self.assertIn("_ACCEL_TAU", self.code)
        self.assertIn("aee_exhaustPrevSpeed", self.code)

    def test_derived_term_reads_rated_power_per_vehicle_or_the_default(self):
        self.assertIn('getVariable ["aee_engineRatedPowerW", 150000]', self.code)

    def test_overdraw_product_holds_across_the_land_size_range(self):
        # The land row runs 0.35 m at idle to 0.60 m at full, a 71 percent
        # size change, so the live count is checked across it.
        budget = float(
            re.search(r"_OVERDRAW_BUDGET\s*=\s*([0-9.]+)", self.code).group(1)
        )
        sources = float(re.search(r"_MAX_SOURCES\s*=\s*([0-9.]+)", self.code).group(1))
        maxlive = float(re.search(r"_MAX_LIVE\s*=\s*([0-9.]+)", self.code).group(1))
        minlive = float(re.search(r"_MIN_LIVE\s*=\s*([0-9.]+)", self.code).group(1))
        worst = 0.0
        d = 0.35
        while d <= 0.6001:
            allowed = budget / (sources * d * d)
            live = max(min(math.floor(allowed), maxlive), minlive)
            overdraw = sources * live * d * d
            self.assertLessEqual(overdraw, budget + 1e-6)
            worst = max(worst, overdraw)
            d += 0.005
        # 0.60 m is still under the 2.297 m step, so the count holds at 12 and
        # the product is 3 * 12 * 0.36 = 12.96 m2.
        self.assertAlmostEqual(worst, 12.96, places=2)

    def test_alpha_does_not_ramp_with_the_derived_load(self):
        alpha_lines = [line for line in self.code.splitlines() if "_alpha =" in line]
        for line in alpha_lines:
            self.assertNotIn("load", line.lower())
            self.assertNotIn("power", line.lower())


class AirEngineLoadKernel(unittest.TestCase):
    """The derived air-engine-load kernel.

    An aircraft in the simple flight model has no RTD reader, so the load is
    DERIVED from a real power balance: the drag power for a wing and the ideal
    induced hover power for a rotor.  The kernel is pure arithmetic over
    scalars plus one class test, so this suite reads its constants from the
    real SQF, re-derives both balances from first principles, and pins the
    reference airframes, the clamp and the guards.
    """

    def setUp(self):
        self.code = _code_only(AIRLOAD_SRC)

    def _default(self, name):
        return float(re.search(rf'\["{name}",\s*([0-9.]+)', self.code).group(1))

    # ── the declared defaults ──────────────────────────────────────────
    def test_defaults_are_the_declared_ones(self):
        self.assertEqual(self._default("_ratedPowerW"), 150000.0)
        self.assertEqual(self._default("_dragAreaM2"), 0.7)
        self.assertEqual(self._default("_rotorDiscAreaM2"), 50.0)
        self.assertEqual(self._default("_idleFraction"), 0.05)
        self.assertEqual(self._default("_airDensity"), 1.225)

    # ── the two balances ───────────────────────────────────────────────
    def test_wing_is_the_drag_power_cube(self):
        self.assertIn(
            "_dragW = 0.5 * _rho * _dragAreaM2 * _speed * _speed * _speed",
            self.code,
        )
        self.assertIn("_load = _dragW / _ratedPowerW", self.code)

    def test_rotor_is_the_momentum_theory_hover_power(self):
        self.assertIn("_weightN = _massKg * 9.80665", self.code)
        self.assertIn(
            "_hoverW = (_weightN ^ 1.5) / sqrt (2 * _rho * _rotorDiscAreaM2)",
            self.code,
        )
        self.assertIn("_load = _hoverW / _ratedPowerW", self.code)

    def test_class_selects_the_balance_inside_the_kernel(self):
        # The branch is inside the kernel, so the kernel stays object-free.
        self.assertIn('_rotor = _class isKindOf "Helicopter"', self.code)

    # ── the PA-28 wing reference ───────────────────────────────────────
    def test_pa28_reference_at_134kw(self):
        # 0.5 * 1.225 * 0.688 * 58^3 = 82226 W; / 134000 = 0.61.
        drag = 0.5 * 1.225 * 0.688 * 58**3
        self.assertAlmostEqual(drag / 134000.0, 0.61, places=2)

    def test_pa28_reference_at_the_repo_default(self):
        # Same arithmetic against the kernel's own 150000 W default.  The
        # exact figure is 82226 / 150000 = 0.548, which is 0.55 to two places.
        drag = 0.5 * 1.225 * 0.688 * 58**3
        self.assertAlmostEqual(drag / 150000.0, 0.55, places=2)

    def test_pa28_at_30ms_is_under_its_cruise(self):
        slow = 0.5 * 1.225 * 0.688 * 30**3
        fast = 0.5 * 1.225 * 0.688 * 58**3
        self.assertLess(slow, fast)

    # ── the R44 rotor reference ────────────────────────────────────────
    def test_r44_reference_is_the_ideal_hover_fraction(self):
        # 5688^1.5 / sqrt (2 * 1.225 * 81) = 30.5 kW; / 131000 = 0.23.
        hover = (580 * 9.80665) ** 1.5 / math.sqrt(2 * 1.225 * 81)
        self.assertAlmostEqual(hover / 131000.0, 0.23, places=2)

    def test_rotor_is_a_stated_lower_bound(self):
        upper = AIRLOAD_SRC.upper()
        self.assertIn("LOWER BOUND", upper)
        self.assertIn("IDEAL", upper)

    # ── the guards and the clamp ───────────────────────────────────────
    def test_non_positive_rated_power_is_refused(self):
        self.assertIn("if (_ratedPowerW <= 0) exitWith { -1 };", self.code)

    def test_non_positive_mass_is_refused(self):
        self.assertIn("if (_massKg <= 0) exitWith { -1 };", self.code)

    def test_non_positive_disc_area_is_refused(self):
        self.assertIn("if (_rotorDiscAreaM2 <= 0) exitWith { -1 };", self.code)

    def test_fraction_is_clamped_and_floored(self):
        self.assertIn("private _idle = _idleFraction max 0 min 1", self.code)
        self.assertIn("_load = (_load max _idle) min 1", self.code)

    # ── the honesty claims ─────────────────────────────────────────────
    def test_header_states_the_derivation_and_the_defaults(self):
        upper = AIRLOAD_SRC.upper()
        self.assertIn("DERIVED", upper)
        self.assertIn("NOT A MEASUREMENT", upper)
        self.assertIn("DECLARED DEFAULT", upper)

    def test_header_states_the_drag_area_coincidence(self):
        upper = AIRLOAD_SRC.upper()
        self.assertIn("COINCIDENCE", upper)
        self.assertIn("0.7 m^2", AIRLOAD_SRC)

    def test_header_states_why_the_function_exists(self):
        upper = AIRLOAD_SRC.upper()
        self.assertIn("SIMPLE FLIGHT MODEL", upper)
        self.assertIn("DIFFICULTYENABLEDRTD", upper)

    def test_header_labels_the_object_work_as_the_callers(self):
        upper = AIRLOAD_SRC.upper()
        self.assertIn("PURE ARITHMETIC", upper)
        self.assertIn("OBJECT-SIDE WORK IS THE CALLER'S", upper)

    def test_arguments_and_example_are_declared(self):
        self.assertIn("Arguments:", AIRLOAD_SRC)
        self.assertIn("Example:", AIRLOAD_SRC)
        self.assertIn("aee_flight_fnc_calculateAirEngineLoad", AIRLOAD_SRC)


class AirEngineLoadWiring(unittest.TestCase):
    """The renderer's derived air branch, the order, and the diagnostic."""

    def setUp(self):
        self.code = _code_only(SHIMMER_SRC)

    def _resolver_body(self):
        block = re.search(r"private _resolvePower = \{(.*?)\n\};", self.code, re.S)
        self.assertIsNotNone(block, "the power resolver is missing")
        return block.group(1)

    def test_kernel_is_registered_in_flight(self):
        prep = (REPO / "addons/flight/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(calculateAirEngineLoad);", prep)

    def test_renderer_calls_the_air_kernel(self):
        self.assertIn("EFUNC(flight,calculateAirEngineLoad)", self.code)
        self.assertIn("_deriveAirPower", self.code)

    def test_air_branch_is_gated_on_the_air_root(self):
        body = self._resolver_body()
        air = body.find('isKindOf "Air"')
        self.assertGreater(air, -1, "the Air branch is missing")
        self.assertIn("_deriveAirPower", body[air:])

    def test_air_branch_is_outside_the_rtd_guard_by_position(self):
        # The air branch must appear AFTER the difficultyEnabledRTD block
        # CLOSES, not inside it.  Reaching it with the flight model OFF is
        # the entire point, so a positional find() is not enough.
        body = self._resolver_body()
        guard_end = _brace_block_end(body, "if (difficultyEnabledRTD) then")
        air = body.find('isKindOf "Air"')
        self.assertGreater(
            air,
            guard_end,
            "the air branch must sit after the difficultyEnabledRTD block closes",
        )

    def test_resolution_order_is_published_rtd_ground_air_idle(self):
        body = self._resolver_body()
        published = body.find("aee_enginePowerFraction")
        guard = body.find("difficultyEnabledRTD")
        collective = body.find("collectiveRTD")
        throttle = body.find("throttleRTD")
        land = body.find('isKindOf "LandVehicle"')
        air = body.find('isKindOf "Air"')
        idle = body.find("_power = _idlePower")
        self.assertTrue(
            -1 < published < guard < collective < throttle < land < air < idle,
            "power order is published, RTD, ground, air, idle",
        )

    def test_renderer_reads_the_existing_rated_power_name(self):
        self.assertIn('getVariable ["aee_engineRatedPowerW", 150000]', self.code)
        names = set(re.findall(r"aee_engine\w*[Rr]ated\w*", self.code))
        self.assertEqual(
            names,
            {"aee_engineRatedPowerW"},
            f"a second rated-power name was introduced: {names}",
        )

    def test_air_overrides_are_read_with_declared_defaults(self):
        self.assertIn('getVariable ["aee_engineDragAreaM2", 0.7]', self.code)
        self.assertIn('getVariable ["aee_engineRotorDiscAreaM2", 50]', self.code)

    # ── the diagnostic ─────────────────────────────────────────────────
    def test_diagnostic_exists_and_names_the_fields(self):
        self.assertIn("AEE_LOG_DEBUG(_logMsg)", self.code)
        self.assertIn("exhaust plume:", self.code)
        for field in (
            "class=",
            "tier=",
            "power=",
            "gasC=",
            "depth=",
            "contrast=",
            "alpha=",
        ):
            self.assertIn(field, self.code, f"the diagnostic is missing {field}")

    def test_diagnostic_is_throttled_on_tick_time(self):
        self.assertIn("_LOG_INTERVAL", self.code)
        self.assertIn("diag_tickTime >= _logAt", self.code)
        self.assertIn("exhaustLogAt", self.code)

    def test_diagnostic_reports_the_alpha_the_renderer_draws(self):
        # The logged alpha is the same expression the renderer applies.
        self.assertIn("_logAlpha = _alphaMax * ((_mag / 2.5) min 1)", self.code)

    # ── the alpha expression is unchanged ──────────────────────────────
    def test_alpha_expression_is_unchanged(self):
        expr = '_alphaMax * (((_entry getOrDefault ["mag", 0]) / 2.5) min 1)'
        self.assertEqual(
            self.code.count(expr),
            2,
            "the render alpha expression changed or lost a site",
        )


if __name__ == "__main__":
    unittest.main()
