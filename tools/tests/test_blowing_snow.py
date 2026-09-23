"""Blowing-snow and blowing-dust visibility mirrors (issue #106).

Mirrors:
  addons/environmental/functions/warnings/fnc_calculateBlowingSnowVisibility.sqf
  addons/environmental/functions/warnings/fnc_calculateDustVisibility.sqf

Snow chain, Li and Pomeroy 1997a, Pomeroy and Gray 1990, Li and Pomeroy
1997b:

  U_t10  = 6.9 + 0.0033 * (T_a + 27.27)^2
  u*     = U_10 * kappa / ln(10 / z0)          kappa = 0.4
  Q_salt = 0.68 * (rho_a / g) * u*_t * (u*^2 - u*_t^2)
  h_salt = 0.8 * u*^2 / g
  V_km   = 0.027 / Q_susp

Dust, Baddock et al. 2014:

  V_km = 0.5 / C                               C in mg/m3

Koschmieder 1924:

  V = 3.912 / sigma

Test vector 1 note.  The issue states U_t10(-20 C) = 7.08 m/s.  The
published form gives 6.9 + 0.0033 * (27.27 - 20)^2 = 7.0744, which is
7.07 at two decimal places.  The issue asks for the published form to be
implemented exactly, so this test asserts the value that form yields.

Test vector 2 note.  The issue states U_t10(0 C) = 9.4 m/s.  The published
form gives 9.3541, which is 9.4 at one decimal place.  The test asserts the
issue's one-decimal value and the exact form value.
"""

import math
import re
import unittest
from pathlib import Path

KAPPA = 0.4
G = 9.81
RHO_A = 1.225
Z0_DEFAULT = 0.001
SUSP_SHARE = 0.20
CLEAR_KM = 300.0
LP_INTERCEPT = 6.9
LP_SLOPE = 0.0033
LP_OFFSET = 27.27

REPO = Path(__file__).resolve().parents[2]
WARNINGS = REPO / "addons" / "environmental" / "functions" / "warnings"
SNOW_SQF = WARNINGS / "fnc_calculateBlowingSnowVisibility.sqf"
DUST_SQF = WARNINGS / "fnc_calculateDustVisibility.sqf"
SEVERE_SQF = WARNINGS / "fnc_calculateSevereWeather.sqf"


def threshold_wind_10(temp_c):
    """Li and Pomeroy 1997a threshold wind speed at 10 m, m/s."""
    return 6.9 + 0.0033 * (temp_c + 27.27) ** 2


def friction_velocity(wind_10, z0=Z0_DEFAULT, kappa=KAPPA):
    """Log wind profile: u* = U_10 kappa / ln(10 / z0), m/s."""
    z0 = min(max(z0, 0.0001), 0.01)
    return wind_10 * kappa / math.log(10.0 / z0)


def saltation_flux(u_star, u_star_t, rho_a=RHO_A, g=G):
    """Pomeroy and Gray 1990 saltation flux, kg/m/s.  Zero below threshold."""
    if u_star <= u_star_t:
        return 0.0
    return 0.68 * (rho_a / g) * u_star_t * (u_star**2 - u_star_t**2)


def saltation_height(u_star, g=G):
    """Saltation layer height h_salt = 0.8 u*^2 / g, m."""
    return 0.8 * u_star**2 / g


def snow_visibility_km(q_susp):
    """Li and Pomeroy 1997b visibility, km.  Clear when there is no flux."""
    if q_susp <= 0:
        return CLEAR_KM
    return 0.027 / q_susp


def snow_state(vis_km):
    """The issue's snow visibility states."""
    if vis_km < 0.1:
        return "whiteout"
    if vis_km < 0.5:
        return "heavy"
    if vis_km < 1:
        return "moderate"
    if vis_km < 10:
        return "light"
    return "none"


def snow_intensity(vis_km):
    """The SQF intensity mapping.

    The bands are MUTUALLY EXCLUSIVE. Written as independent `if` statements
    the third branch fired for anything under 1 km and used the heavy-band
    span, so intensity jumped backwards at the 1 km boundary (0.40 -> 0.33)
    and recovered. That reads as a flicker in the weather FX as visibility
    crosses the band, and the first version of this mirror reproduced the
    bug, so the test passed while the code was wrong.
    """
    if 1 <= vis_km < 10:
        value = 0.4 * (10 - vis_km) / 9
    elif 0.5 <= vis_km < 1:
        value = 0.4 + (0.3 * (1 - vis_km) / 0.5)
    elif 0.1 <= vis_km < 0.5:
        value = 0.7 + (0.3 * (0.5 - vis_km) / 0.4)
    elif vis_km < 0.1:
        value = 1.0
    else:
        value = 0.0
    return min(max(value, 0.0), 1.0)


def dust_visibility_km(concentration):
    """Baddock et al. 2014 visibility, km.  Clear when the air is clean."""
    if concentration <= 0:
        return CLEAR_KM
    return 0.5 / concentration


def dust_state(vis_km):
    """The issue's dust visibility states."""
    if vis_km < 0.05:
        return "extreme"
    if vis_km < 0.5:
        return "severe"
    if vis_km < 5:
        return "moderate"
    return "none"


def dust_intensity(vis_km):
    """The SQF intensity mapping, anchored on the state boundaries."""
    value = 0.0
    if vis_km < 5:
        value = 0.5 * (5 - vis_km) / 4.5
    if vis_km < 0.5:
        value = 0.5 + (0.5 * (0.5 - vis_km) / 0.45)
    return min(max(value, 0.0), 1.0)


def koschmieder_visibility(sigma):
    """Koschmieder 1924: V = 3.912 / sigma, in the unit of 1/sigma."""
    return 3.912 / sigma


class TestSnowThreshold(unittest.TestCase):
    def test_vector_1_threshold_at_minus_20(self):
        """Vector 1: U_t10(-20 C).

        The issue states 7.08 m/s.  The published form yields 7.0744, which
        is 7.07 at two decimal places.  The issue asks for the published
        form, so the form's value is asserted.
        """
        self.assertAlmostEqual(threshold_wind_10(-20), 7.07, places=2)

    def test_vector_2_threshold_at_reference_temperatures(self):
        """Vector 2: 6.9 m/s at -27.3 C and 9.4 m/s at 0 C."""
        self.assertAlmostEqual(threshold_wind_10(-27.3), 6.9, places=2)
        # The form gives 9.3541, which the issue rounds to one decimal.
        self.assertAlmostEqual(threshold_wind_10(0), 9.4, places=1)
        self.assertAlmostEqual(threshold_wind_10(0), 9.354, places=3)

    def test_threshold_falls_as_snow_gets_colder(self):
        """Cold dry snow is mobile, so its threshold is lower."""
        self.assertLess(threshold_wind_10(-30), threshold_wind_10(-10))
        self.assertLess(threshold_wind_10(-10), threshold_wind_10(0))


class TestSaltation(unittest.TestCase):
    def test_vector_3_saltation_height(self):
        """Vector 3: h_salt = 0.02 m at u* = 0.5 m/s."""
        self.assertAlmostEqual(saltation_height(0.5), 0.02, places=2)

    def test_friction_velocity_matches_profile(self):
        self.assertAlmostEqual(
            friction_velocity(10), 10 * 0.4 / math.log(10000), places=6
        )

    def test_friction_velocity_uses_the_z0_band(self):
        """A rougher surface gives a larger friction velocity."""
        self.assertLess(friction_velocity(10, 0.0001), friction_velocity(10, 0.01))

    def test_threshold_friction_velocity_matches_clifton(self):
        """The issue quotes u*_t = 0.30 m/s (Clifton et al. 2006).

        At the Li and Pomeroy reference threshold 6.9 m/s and the default
        z0 = 0.001 m the profile gives 0.30 m/s, so the default roughness
        reproduces the issue's own friction-velocity anchor.
        """
        self.assertAlmostEqual(
            friction_velocity(threshold_wind_10(-27.3), Z0_DEFAULT),
            0.30,
            places=2,
        )

    def test_flux_zero_below_threshold(self):
        self.assertEqual(saltation_flux(0.3, 0.3), 0.0)
        self.assertEqual(saltation_flux(0.2, 0.3), 0.0)

    def test_flux_positive_above_threshold(self):
        self.assertGreater(saltation_flux(0.5, 0.3), 0.0)

    def test_flux_rises_with_friction_velocity(self):
        self.assertLess(saltation_flux(0.4, 0.3), saltation_flux(0.6, 0.3))

    def test_flux_scales_with_air_density(self):
        self.assertLess(
            saltation_flux(0.5, 0.3, rho_a=0.9),
            saltation_flux(0.5, 0.3, rho_a=RHO_A),
        )


class TestSnowVisibility(unittest.TestCase):
    def test_vector_4_visibility(self):
        """Vector 4: Q_susp = 0.05 kg/m/s gives V = 0.54 km."""
        self.assertAlmostEqual(snow_visibility_km(0.05), 0.54, places=2)

    def test_vector_4_boundary(self):
        """The moderate/heavy boundary is 0.5 km, at Q_susp = 0.054.

        The issue rounds 0.054 to 0.05, which gives 0.54 km.  Just above
        the boundary the state is moderate, just below it is heavy.
        """
        self.assertAlmostEqual(snow_visibility_km(0.054), 0.5, places=3)
        self.assertEqual(snow_state(0.54), "moderate")
        self.assertEqual(snow_state(0.5), "moderate")
        self.assertEqual(snow_state(0.49), "heavy")

    def test_state_bands(self):
        self.assertEqual(snow_state(20), "none")
        self.assertEqual(snow_state(5), "light")
        self.assertEqual(snow_state(0.7), "moderate")
        self.assertEqual(snow_state(0.3), "heavy")
        self.assertEqual(snow_state(0.05), "whiteout")

    def test_no_transport_is_clear(self):
        self.assertEqual(snow_visibility_km(0.0), CLEAR_KM)

    def test_intensity_rises_as_visibility_falls(self):
        values = [snow_intensity(v) for v in (20, 10, 5, 1, 0.5, 0.1, 0.05)]
        for earlier, later in zip(values, values[1:]):
            self.assertLessEqual(earlier, later)

    def test_intensity_in_range(self):
        for vis in (300, 10, 5, 1, 0.5, 0.1, 0.01):
            self.assertGreaterEqual(snow_intensity(vis), 0.0)
            self.assertLessEqual(snow_intensity(vis), 1.0)

    def test_intensity_anchors(self):
        self.assertEqual(snow_intensity(10), 0.0)
        self.assertAlmostEqual(snow_intensity(1), 0.4, places=6)
        self.assertAlmostEqual(snow_intensity(0.5), 0.7, places=6)
        self.assertAlmostEqual(snow_intensity(0.1), 1.0, places=6)

    def test_intensity_is_continuous_at_every_band_edge(self):
        """The curve must not step backwards as visibility falls.

        The first implementation used independent `if` statements instead of
        mutually exclusive bands. The heavy branch then fired for anything
        under 1 km and used the heavy span, so intensity jumped backwards at
        the 1 km edge: 0.40 at 1.0 km, 0.33 at 0.99 km. That reads as a
        flicker in the weather FX. The anchors above and the sampled
        monotonicity test both passed while the curve was wrong, so this
        check walks every edge and every interval between them.
        """
        edges = (10.0, 1.0, 0.5, 0.1)
        for edge in edges:
            below = snow_intensity(edge)
            above = snow_intensity(edge - 1e-6)
            self.assertAlmostEqual(
                below,
                above,
                delta=1e-4,
                msg=f"discontinuity at {edge} km: {below:.4f} -> {above:.4f}",
            )

        # And no backwards step anywhere on the descent.
        previous = 0.0
        steps = 20000
        for index in range(steps + 1):
            vis = 10.0 - (10.0 * index / steps)
            value = snow_intensity(vis)
            self.assertGreaterEqual(
                value,
                previous - 1e-9,
                msg=f"intensity fell at {vis:.4f} km",
            )
            previous = value


class TestDustVisibility(unittest.TestCase):
    def test_vector_5_visibility(self):
        """Vector 5: C = 0.5 mg/m3 gives 1.0 km, C = 10 gives 50 m."""
        self.assertAlmostEqual(dust_visibility_km(0.5), 1.0, places=6)
        self.assertAlmostEqual(dust_visibility_km(10), 0.05, places=6)
        self.assertAlmostEqual(dust_visibility_km(10) * 1000, 50.0, places=3)

    def test_state_bands(self):
        self.assertEqual(dust_state(10), "none")
        self.assertEqual(dust_state(1.0), "moderate")
        self.assertEqual(dust_state(0.2), "severe")
        self.assertEqual(dust_state(0.04), "extreme")

    def test_intensity_rises_as_visibility_falls(self):
        values = [dust_intensity(v) for v in (10, 5, 1, 0.5, 0.05, 0.01)]
        for earlier, later in zip(values, values[1:]):
            self.assertLessEqual(earlier, later)

    def test_clean_air_is_clear(self):
        self.assertEqual(dust_visibility_km(0.0), CLEAR_KM)
        self.assertEqual(dust_state(CLEAR_KM), "none")


class TestKoschmieder(unittest.TestCase):
    def test_vector_6(self):
        """Vector 6: sigma = 0.039 gives V = 100 m.

        The relation is V = 3.912 / sigma (Koschmieder).  The issue labels
        sigma as km^-1 and V as metres, which is inconsistent: 3.912/0.039
        is 100.3 only when sigma is per metre.  The number 100 m is the
        intended one, so the mirror treats sigma as per metre here.  The
        mod's other visibility code uses sigma in km^-1 and V in km.
        """
        self.assertAlmostEqual(koschmieder_visibility(0.039), 100, places=0)
        self.assertAlmostEqual(koschmieder_visibility(0.039), 100.3, places=1)


class TestSnowIntensityInSource(unittest.TestCase):
    """Evaluate the SQF intensity branch structure, not the Python mirror.

    A mirror compared against itself proves nothing: when the mirror encoded
    the same wrong branch shape as the SQF, both the anchors and the sampled
    monotonicity test passed while the shipped curve stepped backwards at
    the 1 km edge. This class reads the branch conditions and assignment
    expressions out of the SQF text and evaluates them directly, so it fails
    when the source is wrong however the mirror is written.
    """

    def setUp(self):
        self.text = SNOW_SQF.read_text(encoding="utf-8")

    def _extract_intensity_forms(self):
        """Pull every (condition, expression) pair out of the intensity block."""
        start = self.text.index("private _intensity = 0;")
        end = self.text.index("_intensity = _intensity max 0 min 1;", start)
        block = self.text[start:end]

        pairs = []
        for cond, expr in re.findall(
            r"if\s*\((.*?)\)\s*then\s*\{\s*(?://[^\n]*\n\s*)*_intensity\s*=\s*([^;]+);",
            block,
        ):
            pairs.append((cond.strip(), expr.strip()))
        return pairs

    def test_conditions_are_mutually_exclusive(self):
        """Any two band conditions must not both hold at the same visibility."""
        pairs = self._extract_intensity_forms()
        self.assertGreaterEqual(len(pairs), 3, "expected the band branches")

        for vis in (10.0, 5.0, 1.0, 0.9, 0.5, 0.4, 0.1, 0.05):
            holding = [c for c, _ in pairs if self._eval_condition(c, vis)]
            self.assertLessEqual(
                len(holding),
                1,
                msg=f"at {vis} km these conditions all hold: {holding}",
            )

    def test_curve_is_continuous_and_monotonic(self):
        """Evaluate the SQF conditions directly across the descent."""
        pairs = self._extract_intensity_forms()

        def sqf_intensity(vis):
            value = 0.0
            for cond, expr in pairs:
                if self._eval_condition(cond, vis):
                    value = self._eval_expression(expr, vis)
            return min(max(value, 0.0), 1.0)

        previous = 0.0
        steps = 5000
        for index in range(steps + 1):
            vis = 10.0 - (10.0 * index / steps)
            value = sqf_intensity(vis)
            self.assertGreaterEqual(
                value,
                previous - 1e-9,
                msg=f"SQF intensity fell at {vis:.4f} km: {previous:.4f} -> {value:.4f}",
            )
            previous = value

        for edge in (1.0, 0.5, 0.1):
            self.assertAlmostEqual(
                sqf_intensity(edge),
                sqf_intensity(edge - 1e-6),
                delta=1e-4,
                msg=f"SQF intensity steps at the {edge} km edge",
            )

    def _eval_condition(self, condition, vis):
        """Evaluate a branch condition with _visKm bound to vis."""
        expression = condition.replace("_visKm", repr(float(vis)))
        expression = expression.replace("&&", " and ").replace("||", " or ")
        return bool(eval(expression, {"__builtins__": {}}, {}))

    def _eval_expression(self, expression, vis):
        """Evaluate a branch assignment with _visKm and _heavyTop bound."""
        source = expression.replace("_visKm", repr(float(vis)))
        source = source.replace("_heavyTop", "0.7")
        return float(eval(source, {"__builtins__": {}}, {}))


class TestSevereWeatherWiring(unittest.TestCase):
    """The severe-weather function must use the new models, not scalars."""

    def setUp(self):
        self.severe = SEVERE_SQF.read_text(encoding="utf-8")

    def test_old_wind_scalars_are_gone(self):
        self.assertNotIn("_windSpd / 20", self.severe)
        self.assertNotIn("_windSpd / 25", self.severe)

    def test_both_models_are_called(self):
        self.assertIn("calculateBlowingSnowVisibility", self.severe)
        self.assertIn("calculateDustVisibility", self.severe)


class TestSourceConstants(unittest.TestCase):
    """Guard against drift between this mirror and the SQF constants.

    A token that merely occurs somewhere in the file proves nothing: the
    mirror could read 0.027 while the SQF reads 0.026 and both would pass.
    These checks pull the constant out of the SQF expression and compare it
    with the Python mirror's own value.
    """

    def test_snow_source_constants(self):
        text = SNOW_SQF.read_text(encoding="utf-8")
        for token in ("6.9", "0.0033", "27.27", "0.68", "0.027", "3.912"):
            self.assertIn(token, text)

    def test_dust_source_constants(self):
        text = DUST_SQF.read_text(encoding="utf-8")
        for token in ("0.5", "3.912"):
            self.assertIn(token, text)

    def test_snow_threshold_constant_matches_mirror(self):
        """The Li and Pomeroy intercept and slope in the SQF and the mirror."""
        text = SNOW_SQF.read_text(encoding="utf-8")
        match = re.search(
            r"6\.9\s*\+\s*([0-9.]+)\s*\*\s*\(\(_temp\s*\+\s*([0-9.]+)\)", text
        )
        self.assertIsNotNone(match, "threshold expression not found in the SQF")
        slope, offset = float(match.group(1)), float(match.group(2))
        self.assertAlmostEqual(slope, LP_SLOPE, places=10)
        self.assertAlmostEqual(offset, LP_OFFSET, places=10)
        self.assertAlmostEqual(
            LP_INTERCEPT + slope * (-20 + offset) ** 2,
            threshold_wind_10(-20),
            places=10,
        )

    def test_suspension_share_matches_mirror(self):
        """The share of the saltation flux that the SQF treats as suspended.

        The share is a parameter default, so the check reads the parameter
        block rather than the expression. That is the real contract: the
        mirror must reproduce the default the function ships with.
        """
        text = SNOW_SQF.read_text(encoding="utf-8")
        match = re.search(r'\["_suspShare",\s*([0-9.]+)', text)
        self.assertIsNotNone(match, "suspension share parameter not found")
        self.assertAlmostEqual(float(match.group(1)), SUSP_SHARE, places=10)


if __name__ == "__main__":
    unittest.main()
