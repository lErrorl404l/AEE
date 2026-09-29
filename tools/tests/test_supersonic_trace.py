#!/usr/bin/env python3
"""Supersonic trace kernel verification (issue #217).

Verifies fnc_calculateSupersonicTrace.sqf.  Per the note in
tools/tests/sqf_lite.py a hand-transcribed Python mirror is NOT acceptable,
because a mirror once replicated the SQF's own bugs and drifted from the
source without detection.  So this test PARSES the real SQF and reads every
constant from the file it tests, then re-derives the physics here from first
principles.  A wrong constant in either place fails.

The kernel models the REFRACTIVE component of the trace.  A supersonic round
steps the air density across its bow shock, and the index of refraction of air
tracks density (Gladstone-Dale), so the density step bends light.

The kernel returns an UPPER BOUND, not a prediction.  It applies the NORMAL
shock relation.  A real bullet has a blunted nose, so its bow shock is oblique
over the forward face, and an oblique shock gives a smaller density rise at the
same Mach.  test_oblique_shock_never_exceeds_the_bound checks that claim
numerically, so the bound cannot quietly turn into a prediction.

Sources held for the constants:
  K = 2.26e-4 m^3/kg  Stone and Zimmerman, "Index of Refraction of Air",
                      NIST Engineering Metrology Toolbox, which publishes
                      the Edlen and Ciddor equations.
  gamma = 1.4         U.S. Standard Atmosphere 1976, NTRS 19770009539.
  local sound speed   a = 20.05 * sqrt(T + 273.15), the form
                      fnc_calculateBallisticDrag already uses.

Run: python3 -m unittest tools/tests/test_supersonic_trace.py
"""

import math
import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
KERNEL = REPO / "addons/ballistics/functions/fnc_calculateSupersonicTrace.sqf"
SOURCE = KERNEL.read_text(encoding="utf-8")


def sqf_number(pattern: str) -> float:
    """Read a numeric literal out of the real SQF, so this test cannot drift
    from the file it tests."""
    match = re.search(pattern, SOURCE)
    if not match:
        raise AssertionError(f"SQF no longer matches {pattern!r}")
    return float(match.group(1))


def normal_shock_ratio(mach: float, gamma: float = 1.4) -> float:
    """Rankine-Hugoniot density ratio across a normal shock, gamma = 1.4."""
    m2 = mach * mach
    return ((gamma + 1) * m2) / ((gamma - 1) * m2 + 2)


class SupersonicTraceKernel(unittest.TestCase):
    def setUp(self) -> None:
        self.gamma = sqf_number(r"private _gamma\s*=\s*([0-9.]+)\s*;")
        self.k = sqf_number(r"private _k\s*=\s*([0-9.]+)\s*;")
        self.rho0 = sqf_number(r"private _rhoAmbient\s*=\s*([0-9.]+)")
        self.sound_coeff = sqf_number(r"private _sound\s*=\s*([0-9.]+)")

    def contrast(self, mach: float, rho_rel: float = 1.0) -> float:
        """The kernel result in its reported units, re-derived here."""
        ratio = normal_shock_ratio(mach, self.gamma)
        return self.k * self.rho0 * rho_rel * (ratio - 1.0) / 0.0001

    def ambient_index(self, rho_rel: float = 1.0) -> float:
        """K * rho, the index step of the undisturbed air itself."""
        return self.k * self.rho0 * rho_rel / 0.0001

    # ── the constants are the sourced ones ──────────────────────────────
    def test_gamma_matches_us_standard_atmosphere(self) -> None:
        self.assertEqual(self.gamma, 1.4)

    def test_gladstone_dale_coefficient(self) -> None:
        self.assertAlmostEqual(self.k, 0.000226, places=9)

    def test_sea_level_index_matches_the_standard_value(self) -> None:
        # K is defined by (n - 1) / rho.  At 15 C and 101.325 kPa the standard
        # index for air is n - 1 = 2.77e-4, so K * rho0 must land there.  This
        # ties the SQF constant to a published number for standard air.
        self.assertAlmostEqual(self.k * self.rho0, 2.77e-4, places=6)

    def test_ambient_density_is_isa_sea_level(self) -> None:
        self.assertEqual(self.rho0, 1.225)

    def test_speed_of_sound_form(self) -> None:
        self.assertEqual(self.sound_coeff, 20.05)
        # 20.05 * sqrt(288.15) is 340.34 m/s, the ISA sea level value.
        self.assertAlmostEqual(20.05 * math.sqrt(288.15), 340.29, delta=0.1)

    # ── the algebra the SQF implements, re-derived here ────────────────
    def test_density_ratio_vanishes_at_unity(self) -> None:
        # The relation returns exactly 1 at M = 1, so the shock and the trace
        # vanish there.  This is the subsonic guard.
        self.assertAlmostEqual(normal_shock_ratio(1.0, self.gamma), 1.0, places=12)

    def test_density_ratio_against_normal_shock_table(self) -> None:
        # Textbook normal shock density ratios for gamma = 1.4.
        expected = {
            1.0: 1.0,
            1.5: 1.8621,
            2.0: 2.6667,
            2.5: 3.3333,
            3.0: 3.8571,
        }
        for mach, want in expected.items():
            self.assertAlmostEqual(
                normal_shock_ratio(mach, self.gamma), want, places=3, msg=f"M={mach}"
            )

    def test_contrast_grows_with_mach(self) -> None:
        seq = [self.contrast(m) for m in (1.0, 1.2, 1.5, 2.0, 2.6, 3.0, 4.0)]
        for i in range(len(seq) - 1):
            self.assertLess(seq[i], seq[i + 1], f"not monotone at index {i}")

    def test_contrast_scales_with_rho_rel(self) -> None:
        # Denser air carries a larger index step for the same Mach.
        self.assertGreater(self.contrast(2.6, 1.2), self.contrast(2.6, 1.0))
        self.assertGreater(self.contrast(2.6, 1.0), self.contrast(2.6, 0.8))

    def test_contrast_against_the_index_of_the_air_itself(self) -> None:
        # The trace competes with the index of the air it sits in, so compare
        # the two.  Just supersonic, the shock step is a small fraction of it.
        # At rifle Mach it is larger than the whole atmospheric index step.
        self.assertLess(self.contrast(1.2), self.ambient_index())
        self.assertGreater(self.contrast(2.6), 2.4 * self.ambient_index())
        self.assertGreater(self.contrast(2.6), self.contrast(2.0))

    # ── the result is a bound, and must stay labelled one ──────────────
    def test_oblique_shock_never_exceeds_the_bound(self) -> None:
        # An oblique shock has a normal Mach number M sin(beta), which is
        # strictly below M for any beta below 90 degrees.  The normal shock
        # ratio rises with Mach, so the oblique ratio is always strictly below
        # the normal shock ratio the kernel returns.  If this fails, the
        # "upper bound" wording in the header is a lie.
        for mach in (1.2, 1.5, 2.0, 2.6, 3.0, 4.0):
            bound = normal_shock_ratio(mach, self.gamma)
            for beta_deg in range(20, 90, 5):
                m_normal = mach * math.sin(math.radians(beta_deg))
                if m_normal <= 1.0:
                    continue
                self.assertLess(
                    normal_shock_ratio(m_normal, self.gamma),
                    bound,
                    msg=f"M={mach} beta={beta_deg}",
                )

    def test_header_states_the_ceiling_and_its_attainment(self) -> None:
        # The value is an upper bound over every shape. NACA 1135 p. 621
        # gives the reduction rule that makes the density ratio a function
        # of the normal Mach number alone, with no shape term. A round with
        # a finite tip radius attains the bound. A perfectly sharp body
        # does not, so a single unconditional "exact maximum" overreaches.
        self.assertIn("EXACT UPPER BOUND", SOURCE.upper())
        self.assertIn("ANY NOSE SHAPE", SOURCE.upper())
        self.assertIn("ATTAINED MAXIMUM", SOURCE.upper())
        self.assertIn("FINITE TIP RADIUS", SOURCE.upper())
        self.assertIn("PERFECTLY SHARP", SOURCE.upper())
        self.assertIn("1135", SOURCE)
        self.assertIn("p. 621", SOURCE)
        self.assertIn("stagnation streamline", SOURCE.lower())
        self.assertNotIn("EXACT MAXIMUM", SOURCE.upper())

    def test_header_records_the_refused_floor_and_why(self) -> None:
        # A floor would need theta-beta-M, which is an ATTACHED-shock
        # relation. A meplat forces detachment, so the floor is refused.
        # NACA 1135 p. 624 gives the attachment limit for the wedge and for
        # the cone, both at infinite Mach, so a finite Mach accepts less.
        # The meplat turn is far above either.
        self.assertIn("NO FLOOR IS RETURNED", SOURCE)
        self.assertIn("DETACHED", SOURCE.upper())
        self.assertIn("45.6", SOURCE)
        self.assertIn("57.5", SOURCE)
        self.assertIn("infinite Mach", SOURCE)
        self.assertIn("90 degrees", SOURCE)
        # The finite-Mach wedge angles argued a wedge around a body of
        # revolution. NACA 1135 p. 624 bounds both families instead.
        for gone in ("22.97", "30.81", "34.07"):
            self.assertNotIn(gone, SOURCE, msg=f"stale wedge angle {gone}")

    def test_header_closes_the_wedge_versus_cone_question(self) -> None:
        # The attached solution for a body of revolution is conical
        # Taylor-Maccoll, not the wedge relation. That difference changes
        # the shock angle at a fixed surface turn, so it would change a
        # point value or a floor. It does not change the density ratio at a
        # fixed shock angle. The ceiling sits at beta = 90 degrees, where
        # the planar and the conical case coincide. The question is closed,
        # so the header no longer records it as undetermined.
        self.assertIn("Taylor-Maccoll", SOURCE)
        self.assertIn("fixed shock angle", SOURCE)
        self.assertIn("coincide", SOURCE)
        self.assertIn("irrelevant", SOURCE)
        self.assertNotIn("not determined", SOURCE.lower())

    def test_ceiling_is_invariant_to_nose_geometry(self) -> None:
        # The reduction rule makes the local density ratio a function of
        # M sin(beta) alone, so no nose geometry enters it. The scan below
        # walks the shock angle: the ratio peaks at beta = 90 degrees, which
        # is the single value the kernel returns. A nose shape only selects
        # beta, so it cannot change the ceiling. That a blunt tip attains
        # the ceiling is a geometry fact, not arithmetic, so this test does
        # not assert it.
        for mach in (1.2, 1.5, 2.0, 2.6, 3.0, 4.0):
            bound = normal_shock_ratio(mach, self.gamma)
            peak = 0.0
            for b in range(1, 901):
                beta = math.radians(b / 10.0)
                ratio = normal_shock_ratio(mach * math.sin(beta), self.gamma)
                peak = max(peak, ratio)
            self.assertAlmostEqual(peak, bound, places=9, msg=f"M={mach}")
        # A shape term would have to enter as an argument. None does, so the
        # returned value cannot vary with the nose.
        params_block = SOURCE.split("params [", 1)[1].split("];", 1)[0]
        for shape_word in ("nose", "ogive", "meplat", "radius", "shape", "cone"):
            self.assertNotIn(shape_word, params_block.lower())

    def test_header_records_the_muzzle_only_publish(self) -> None:
        # The handler publishes one value at the muzzle. Nothing in the
        # repository reads it, so no per-frame tracker exists. A caller
        # recomputes at range by passing the current velocity, argument 0.
        self.assertIn("A SINGLE MUZZLE VALUE", SOURCE.upper())
        self.assertIn("at the muzzle", SOURCE)
        self.assertIn("no reader", SOURCE)
        self.assertIn("argument 0", SOURCE)

    def test_header_keeps_the_radio_constant_separate(self) -> None:
        # fnc_calculateRefraction holds the ITU-R P.453 RADIO refractivity.
        # Its wavelength is not the visible one, so its constant must not be
        # read as the optical Gladstone-Dale K.
        self.assertIn("ITU-R", SOURCE)
        self.assertIn("radio", SOURCE.lower())

    def test_header_does_not_claim_to_exclude_condensation(self) -> None:
        # The kernel models refraction only.  It must not claim a droplet
        # cloud is impossible, because that claim is not established.
        self.assertIn("neither models", SOURCE)

    # ── the guards the SQF must keep ───────────────────────────────────
    def test_no_trace_below_mach_one(self) -> None:
        self.assertRegex(SOURCE, r"if \(_mach\s*<=\s*1\)\s*exitWith \{\s*0\s*\}")
        self.assertRegex(SOURCE, r"if \(_velocity\s*<=\s*0\)\s*exitWith")
        self.assertRegex(SOURCE, r"if \(_rhoRel\s*<=\s*0\)\s*exitWith")

    def test_no_strength_override(self) -> None:
        # An override would let a trace appear where the air does not support
        # one.  The function must not scale its result, and must not publish a
        # multiplier setting.
        self.assertNotIn("settingsConfigFile", SOURCE)
        self.assertNotIn("missionNamespace setVariable", SOURCE)
        self.assertNotIn("GVAR(", SOURCE.split("Arguments:")[0])
        # The only scaling is the reporting unit, and it is a pure division.
        body = SOURCE.split("private _contrast =")[-1]
        self.assertIn("_contrast / 0.0001", body)

    def test_declares_params_and_return(self) -> None:
        # CONTRIBUTING requires the standard header: params, return, example.
        self.assertIn("params [", SOURCE)
        self.assertIn("Arguments:", SOURCE)
        self.assertIn("Returns the refractive index contrast", SOURCE)


class SupersonicTraceWiring(unittest.TestCase):
    """The kernel must be reached from the Fired handler.

    A registered function that nothing calls is dead code, not a feature.
    The kernel was first committed with no caller, so this guards that.
    """

    def setUp(self) -> None:
        # Comments are stripped.  These tests assert that a construct is
        # ABSENT from the init file, and the idempotency guard added to every
        # init file explains itself in prose that names addPerFrameHandler.  A
        # search that can see comments is a check a sentence can satisfy.
        self.post_init = "\n".join(
            (ln if ln.find("//") < 0 else ln[: ln.find("//")])
            for ln in (REPO / "addons/ballistics/XEH_postInit.sqf")
            .read_text(encoding="utf-8")
            .split("\n")
        )
        self.annex = (
            REPO / "docs/wiki/annexes/annex-c-variable-reference.qmd"
        ).read_text(encoding="utf-8")

    def test_kernel_is_called_not_only_registered(self) -> None:
        self.assertRegex(self.post_init, r"call FUNC\(calculateSupersonicTrace\)")
        # A PREP registration alone must never satisfy this gate.
        prep = (REPO / "addons/ballistics/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(calculateSupersonicTrace);", prep)

    def test_kernel_is_called_once_and_not_from_a_per_frame_tracker(self) -> None:
        # The published value is the muzzle value. Nothing reads it, so a
        # per-frame update would cost every machine for no consumer. The
        # kernel is called exactly once, on the Fired path.
        calls = re.findall(r"call FUNC\(calculateSupersonicTrace\)", self.post_init)
        self.assertEqual(len(calls), 1)
        for token in ("addPerFrameHandler", "EachFrame", "diag_tickTime"):
            self.assertNotIn(token, self.post_init)

    def test_wired_from_the_fired_handler_not_a_test(self) -> None:
        # The only production shot path is the "fired" event handler.
        self.assertIn('"Fired"', self.post_init)
        self.assertIn("call FUNC(resolveShot)", self.post_init)

    def test_published_value_is_not_scaled_at_the_call_site(self) -> None:
        # A scale factor here would force a trace the air does not support.
        call = re.search(r"call FUNC\(calculateSupersonicTrace\);", self.post_init)
        self.assertIsNotNone(call)
        tail = self.post_init[call.end() : call.end() + 120]
        self.assertIn("setVariable", tail)
        self.assertNotRegex(tail, r"\*\s*[0-9]")

    def test_published_variable_is_documented_in_annex_c(self) -> None:
        # validate_cba_settings.py fails on an undocumented orphan write, so
        # the published name must carry an Annex C row.
        self.assertIn("aee_ballistics_supersonicTrace", self.annex)

    def test_annex_c_row_states_the_corrected_ceiling(self) -> None:
        # The row must document the corrected claim and the muzzle-only
        # publish, because validate_cba_settings.py fails on an undocumented
        # orphan write.
        row = re.search(r"`aee_ballistics_supersonicTrace`[^\n]*", self.annex)
        self.assertIsNotNone(row)
        text = row.group(0)
        self.assertIn("upper bound", text)
        self.assertIn("finite tip radius", text)
        self.assertIn("argument 0", text)

    def test_wiring_uses_resolved_inputs_not_constants(self) -> None:
        # The call must use the resolved muzzle velocity and live
        # environment, not a hard-coded velocity that cannot decay.
        call = re.search(
            r"\[([^\]]*)\]\s*call FUNC\(calculateSupersonicTrace\);", self.post_init
        )
        self.assertIsNotNone(call)
        args = call.group(1)
        self.assertIn("_initSpeed", args)
        self.assertIn("_rhoRel", args)
        self.assertIn("_tempC", args)
        for bad in ("905", "343", "1.0,"):
            self.assertNotIn(bad, args)


# ─── Mach cone geometry and the renderer contract (#217 follow-on) ─────────
CONE = REPO / "addons/ballistics/functions/fnc_calculateMachCone.sqf"
RENDERER = REPO / "addons/fx/functions/particle/fnc_renderSupersonicTrace.sqf"
FX_POST = REPO / "addons/fx/XEH_postInit.sqf"
BALLISTICS_PREP = REPO / "addons/ballistics/XEH_PREP.hpp"
PROBE = REPO / "tests/docker/missions/aee_test.Stratis/aee_p65_trace_probe.sqf"


def _code_only(text: str) -> str:
    """Blank out SQF comments so a token that appears only in the prose that
    explains it cannot satisfy an absence assertion.  The renderer header
    names the superseded expression, so a raw search finds the explanation
    before the code it is meant to compare against."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


def _literal(text: str, name: str) -> float:
    """Read a literal numeric constant, and refuse an expression in its place."""
    m = re.search(rf"_{name}\s*=\s*([0-9.]+)\s*;", text)
    if m is None:
        raise AssertionError(f"literal _{name} not found")
    return float(m.group(1))


def _expr(text: str, name: str) -> str:
    """Read the right-hand side of a `_name = <expr>;` declaration."""
    m = re.search(rf"_{name}\s*=\s*([^;]+);", text)
    if m is None:
        raise AssertionError(f"constant _{name} not found")
    return m.group(1).strip()


def _sqf_expr(expr: str, env: dict) -> float:
    """Evaluate the small arithmetic subset the renderer derivations use.

    The tests read the real expression out of the SQF and evaluate it over the
    constants parsed from the same file, so a wrong operator fails without a
    hand-copied mirror.
    """
    return eval(re.sub(r"\bsqrt\b", "math.sqrt", expr), {"math": math}, dict(env))


def _renderer_geometry(text: str) -> dict:
    """Parse the renderer's budget and visibility derivation into numbers."""
    env = {
        "_OVERDRAW_BUDGET_M2": _literal(text, "OVERDRAW_BUDGET_M2"),
        "_MAX_TRACES": _literal(text, "MAX_TRACES"),
        "_TRAIL_WIDTHS": _literal(text, "TRAIL_WIDTHS"),
        "_MIN_SIZE": _literal(text, "MIN_SIZE"),
        "_MIN_DROP": _literal(text, "MIN_DROP"),
        "_FOCAL_LENGTH_PX": _literal(text, "FOCAL_LENGTH_PX"),
        "_TARGET_PX": _literal(text, "TARGET_PX"),
        "_REF_RANGE_M": _literal(text, "REF_RANGE_M"),
        "_REF_MACH": _literal(text, "REF_MACH"),
        "_REF_CALIBRE_M": _literal(text, "REF_CALIBRE_M"),
    }
    env["_LIVE_SPRITES"] = _sqf_expr(_expr(text, "LIVE_SPRITES"), env)
    env["_REF_CONE_M"] = _sqf_expr(_expr(text, "REF_CONE_M"), env)
    env["_MAX_SIZE"] = _sqf_expr(_expr(text, "MAX_SIZE"), env)
    env["_VISIBILITY"] = _sqf_expr(_expr(text, "VISIBILITY"), env)
    return env


class MachConeKernel(unittest.TestCase):
    """fnc_calculateMachCone is exact cone geometry for a slender body."""

    def setUp(self) -> None:
        self.cone = CONE.read_text(encoding="utf-8")
        self.code = _code_only(self.cone)

    def test_registered_in_prep(self) -> None:
        self.assertIn(
            "PREP(calculateMachCone);",
            BALLISTICS_PREP.read_text(encoding="utf-8"),
        )

    def test_half_angle_is_asin_of_the_reciprocal_mach(self) -> None:
        self.assertIn("asin (1 / _mach)", self.code)

    def test_values_match_the_exact_geometry(self) -> None:
        # The same table the P65 probe asserts.
        table = {
            1.1: 65.38,
            1.2: 56.44,
            1.5: 41.81,
            2.0: 30.00,
            2.7: 21.74,
            3.5: 16.60,
            4.0: 14.48,
        }
        for mach, want in table.items():
            got = math.degrees(math.asin(1.0 / mach))
            self.assertAlmostEqual(got, want, places=1, msg=f"M={mach}")

    def test_tangent_is_the_algebraic_form(self) -> None:
        # tan(asin(1/M)) = 1 / sqrt(M^2 - 1), so no degree round trip.
        self.assertIn("1 / sqrt ((_mach * _mach) - 1)", self.code)

    def test_returns_half_angle_and_half_and_full_width(self) -> None:
        self.assertRegex(self.code, r"\[_muDeg, 0\.5 \* _fullWidth, _fullWidth\]")

    def test_the_cone_narrows_as_the_round_accelerates(self) -> None:
        # width = 8 * calibre * tan(mu), and tan(mu) falls with Mach.
        widths = [8 * 0.00556 / math.sqrt(m * m - 1) for m in (1.5, 2.0, 2.7, 3.5, 4.0)]
        for i in range(len(widths) - 1):
            self.assertGreater(widths[i], widths[i + 1])

    def test_width_scales_with_calibre(self) -> None:
        def width(calibre_mm: float) -> float:
            return 8 * (calibre_mm / 1000) / math.sqrt(2.7**2 - 1)

        self.assertAlmostEqual(width(12.7) / width(5.56), 12.7 / 5.56, places=6)
        self.assertGreater(width(12.7), width(5.56))

    def test_subsonic_returns_zeros(self) -> None:
        self.assertIn("if (_mach <= 1) exitWith { [0, 0, 0] };", self.code)

    def test_geometry_constant_names_the_two_ell(self) -> None:
        self.assertIn("_APERTURE = 2 * _BODY_CALIBRES;", self.code)

    def test_header_states_the_slender_body_standoff(self) -> None:
        # Header prose wraps, so collapse the whitespace before matching a
        # phrase that may be split across two lines.
        prose = re.sub(r"\s+", " ", self.cone).upper()
        for phrase in ("SLENDER", "NOSE RADIUS", "SPHERE", "NOT APPLICABLE"):
            self.assertIn(phrase, prose, msg=f"missing header phrase: {phrase}")

    def test_header_states_the_sign_error_it_corrects(self) -> None:
        prose = self.cone.upper()
        self.assertIn("SIGN ERROR", prose)
        self.assertIn("NARROWS", prose)


class RendererConeContract(unittest.TestCase):
    """The renderer sizes the sprite from the cone, not from legibility."""

    def setUp(self) -> None:
        self.renderer = RENDERER.read_text(encoding="utf-8")
        self.code = _code_only(self.renderer)

    def test_calls_the_cone_kernel(self) -> None:
        self.assertRegex(self.code, r"call EFUNC\(ballistics,calculateMachCone\)")

    def test_old_legibility_size_expression_is_gone(self) -> None:
        # The old size came from contrast.  It must not survive in code, only
        # in the header that explains its removal.
        self.assertNotRegex(self.code, r"0\.2\s*\+\s*1\.4\s*\*\s*_legibility")
        self.assertNotIn("_size = 0.2", self.code)

    def test_hardcoded_sprite_width_is_gone(self) -> None:
        # The superseded size array began with a fixed 0.05, so a 5.56 and a
        # 12.7 mm round drew the identical width.
        self.assertNotIn("[0.05,", self.code)

    def test_both_size_array_entries_carry_the_cone_width(self) -> None:
        self.assertIn("[_size, _size],", self.code)

    def test_visibility_constant_is_derived_from_a_pixel_target(self) -> None:
        # The factor is no longer a picked 50.  It is computed from a stated
        # pixel target at a stated reference range, so the derivation is
        # visible in code and the old literal is absent.
        expr = re.search(r"_VISIBILITY\s*=\s*([^;]+);", self.code)
        self.assertIsNotNone(expr, "_VISIBILITY not declared")
        self.assertIn("_TARGET_PX", expr.group(1))
        self.assertIn("_REF_RANGE_M", expr.group(1))
        self.assertNotRegex(self.code, r"_VISIBILITY\s*=\s*50\s*;")
        prose = self.renderer.upper()
        self.assertIn("RENDERING DECISION", prose)
        self.assertIn("NOT PHYSICS", prose)

    def test_cap_is_derived_from_the_overdraw_budget(self) -> None:
        # The cap is a RENDERING-BUDGET limit computed from the measured
        # overdraw budget and the worst-case sprite count, not the picked
        # literal 1.4.
        expr = re.search(r"_MAX_SIZE\s*=\s*([^;]+);", self.code)
        self.assertIsNotNone(expr, "_MAX_SIZE not declared")
        body = expr.group(1)
        self.assertIn("_OVERDRAW_BUDGET_M2", body)
        self.assertIn("_MAX_TRACES", body)
        self.assertIn("_LIVE_SPRITES", body)
        self.assertNotIn("1.4", body)
        self.assertNotIn("1.4", self.code)
        self.assertRegex(self.code, r"_MIN_SIZE\s*=\s*[0-9.]+;")
        prose = re.sub(r"\s+", " ", self.renderer).upper()
        self.assertIn("DIVERGES", prose)
        self.assertIn("SUB-PIXEL", prose)
        self.assertIn("RENDERING-BUDGET LIMIT", prose)
        self.assertIn("NOT A PHYSICAL ONE", prose)

    def test_derived_cap_is_the_sqrt_of_the_budget(self) -> None:
        env = _renderer_geometry(self.code)
        want = math.sqrt(
            env["_OVERDRAW_BUDGET_M2"] / (env["_MAX_TRACES"] * env["_LIVE_SPRITES"])
        )
        self.assertAlmostEqual(env["_MAX_SIZE"], want, places=9)
        # The value the expression evaluates to, so a wrong operator fails.
        self.assertAlmostEqual(env["_MAX_SIZE"], 2.4369, places=3)

    def test_five_five_six_round_clears_the_visual_floor(self) -> None:
        # The user confirmed the 5.56 mm trace visible by eye, so the derived
        # factor must not shrink it below the 0.8 m regression floor.
        env = _renderer_geometry(self.code)
        physical = 8 * 0.00556 / math.sqrt((2.76 * 2.76) - 1)
        self.assertGreaterEqual(physical * env["_VISIBILITY"], 0.8)

    def test_lifetime_sits_in_the_lifetime_slot(self) -> None:
        # Index 4 of setParticleParams is the lifetime.  The superseded
        # version left a fixed 0.4 there and mis-filed the derived value in
        # the rotation-velocity and weight slots.
        self.assertIn("1, _ttl,", self.code)
        self.assertNotIn("1, 0.4,", self.code)

    def test_live_count_and_rate_are_bounded(self) -> None:
        self.assertRegex(self.code, r"_TRAIL_WIDTHS\s*=\s*[0-9]+;")
        self.assertRegex(self.code, r"_LIVE_SPRITES\s*=\s*2 \* _TRAIL_WIDTHS;")
        self.assertRegex(self.code, r"_MIN_DROP\s*=\s*[0-9.]+;")
        self.assertRegex(self.code, r"_ttl\s*=\s*_LIVE_SPRITES \* _dropPhysical;")

    def test_alpha_floor_is_unchanged(self) -> None:
        self.assertIn("0.20 + (0.55 * _legibility)", self.code)

    def test_params_take_the_projectile_and_the_ammunition(self) -> None:
        block = self.code.split("params [", 1)[1].split("];", 1)[0]
        self.assertIn('["_projectile"', block)
        self.assertIn('["_ammo"', block)

    def test_calibre_is_not_the_engine_caliber_value(self) -> None:
        # CfgAmmo "caliber" is a normalised penetration multiplier, not mm.
        self.assertNotIn('"caliber"', self.code)
        self.assertIn("getCartridgeData", self.code)
        self.assertIn("parseCaliber", self.code)
        self.assertRegex(self.code, r"_DEFAULT_CALIBRE_MM\s*=\s*7\.62;")


class FiredHandlerScans(unittest.TestCase):
    """The ammunition is found by content; the round comes from the proven slot.

    A previous version took the round as the first OBJECT that was not the
    shooter, guarded by

        _x isEqualType "OBJECT"

    and pinned that design with two tests in this class, one of which asserted
    the corrected form was ABSENT.  The live RPT at 13:59:54 on 29 Sep proved
    the design wrong: "isnull: Type String, expected Object" at
    addons/fx/XEH_postInit.sqf line 92, four times in three seconds.
    isEqualType compares the left value against the TYPE OF its right-hand
    argument, so the string literal "OBJECT" is a String and the guard really
    asked "is _x a String".  It accepted the WEAPON CLASS at slot 1, and isNull
    then rejected it.  The guard was also the same predicate as the ammunition
    scan below it, so the two branches could not tell a weapon class from an
    ammunition class apart.

    Slot 6 is the round, and the ballistics and optics fired handlers in this
    build already read it from there and both work in game.  The ammunition is
    still found by content, because that is where a content check adds real
    robustness: a weapon class is a String too, and the config lookup is what
    separates it from an ammunition class.
    """

    def setUp(self) -> None:
        self.post = _code_only(FX_POST.read_text(encoding="utf-8"))

    def test_ammo_is_found_as_a_cfgammo_class(self) -> None:
        self.assertIn('isClass (configFile >> "CfgAmmo" >> _x)', self.post)

    def test_round_comes_from_the_slot_the_working_handlers_read(self) -> None:
        # Same event, same build: ballistics and optics both read the round
        # from slot 6 and both work in game.
        self.assertIn('params ["_unit", "", "", "", "", "", "_projectile"]', self.post)

    def test_the_quoted_type_name_guard_is_gone(self) -> None:
        # A quoted type NAME is a String, not a request for the OBJECT type.
        # If this comes back, the guard has returned to testing for a String.
        self.assertNotIn('isEqualType "OBJECT"', self.post)

    def test_round_is_guarded_before_use(self) -> None:
        self.assertIn("if (isNull _projectile) exitWith {}", self.post)

    def test_renderer_receives_the_ammo_class(self) -> None:
        self.assertRegex(
            self.post, r"\[_projectile, _ammo\] call FUNC\(renderSupersonicTrace\);"
        )


class ProbeMirrorsTheRenderer(unittest.TestCase):
    """The P65 probe recomputes the renderer geometry, so its mirrored
    constants and its derivation must equal the renderer's, or the headless
    check drifts."""

    def test_probe_ingredients_match_the_renderer(self) -> None:
        renderer = _renderer_geometry(_code_only(RENDERER.read_text(encoding="utf-8")))
        probe = _renderer_geometry(_code_only(PROBE.read_text(encoding="utf-8")))
        for name in (
            "_OVERDRAW_BUDGET_M2",
            "_MAX_TRACES",
            "_TRAIL_WIDTHS",
            "_LIVE_SPRITES",
            "_MIN_SIZE",
            "_MIN_DROP",
            "_FOCAL_LENGTH_PX",
            "_TARGET_PX",
            "_REF_RANGE_M",
            "_REF_MACH",
            "_REF_CALIBRE_M",
        ):
            self.assertEqual(renderer[name], probe[name], f"_{name} mirror drifted")

    def test_probe_derived_values_match_the_renderer(self) -> None:
        renderer = _renderer_geometry(_code_only(RENDERER.read_text(encoding="utf-8")))
        probe = _renderer_geometry(_code_only(PROBE.read_text(encoding="utf-8")))
        for name in ("_REF_CONE_M", "_MAX_SIZE", "_VISIBILITY"):
            self.assertAlmostEqual(
                renderer[name],
                probe[name],
                places=9,
                msg=f"the probe's {name} mirror has drifted from the renderer",
            )


if __name__ == "__main__":
    unittest.main()
