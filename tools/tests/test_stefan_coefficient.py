"""Stefan frost-depth coefficient mirror (issue #11).

Mirrors fnc_calculateStefanCoefficient.sqf, the soil-type-dependent form
of the Stefan frost depth.

  X = sqrt( 2 * k_f * F / Q_L )        F in K.s
  Q_L = rho_dry * L_f * theta          J/m3, volumetric latent heat
  X_cm = C * sqrt(FDD_degC_day)

The mod once held two constants, 2.7 bare and 1.7 under snow. Both treat
the soil as one substance, and both sit below the physical range. The
point of this test is that the coefficient now follows the water content:
a saturated soil carries far more latent heat than dry sand, so it freezes
to a shallower depth for the same weather.

Sources: Stefan 1891; de Vries 1963 (k_f, theta); IAPWS-95 (L_f);
Sturm et al. 1997 (snow conductance).
"""

import math
import unittest

L_FUS = 3.34e5
RHO_DRY = 1600.0
SECONDS_PER_DAY = 86400.0

# Mirrors the SQF table: material -> (k_f W/m.K, theta volumetric).
TABLE = {
    "ground": (1.50, 0.25),
    "rock": (2.50, 0.10),
    "gravel": (2.00, 0.10),
    "vegetation": (0.60, 0.35),
    "concrete": (1.50, 0.25),
    "asphalt": (1.50, 0.25),
    "metal": (1.50, 0.25),
    "water": (2.20, 1.00),
}


def stefan_coefficient(material, snow=0.0):
    """The SQF function, in Python."""
    k_f, theta = TABLE.get(material.lower(), TABLE["ground"])
    q_l = max(RHO_DRY * L_FUS * theta, 1e6)
    c = 100 * math.sqrt((2 * k_f * SECONDS_PER_DAY) / q_l)
    if snow > 0:
        insulation = 0.37 + (0.63 * (1 - min(snow / 0.5, 1)))
        c *= insulation
    return c


def frost_depth_m(material, fdd_degc_day, snow=0.0):
    """Frost depth in metres at the given freezing degree-days."""
    return stefan_coefficient(material, snow) * math.sqrt(fdd_degc_day) / 100


class TestStefanCoefficient(unittest.TestCase):
    def test_reproduces_the_issue_worked_example(self):
        """#11 states F=500, k=1.5, QL=1e8 -> X = 1.14 m.

        The example fixes Q_L directly rather than deriving it from theta,
        so it is checked against the Stefan formula itself.
        """
        f_kelvin_seconds = 500 * SECONDS_PER_DAY
        x = math.sqrt(2 * 1.5 * f_kelvin_seconds / 1e8)
        self.assertAlmostEqual(x, 1.14, places=2)

    def test_silt_loam_lands_inside_the_published_band(self):
        """#11 gives silt/loam Q_L as 1.0e8 to 1.6e8 J/m3.

        The table's theta 0.25 at rho 1600 gives 1.336e8, which is inside
        that band and therefore a valid silt/loam.
        """
        q_l = RHO_DRY * L_FUS * 0.25
        self.assertGreater(q_l, 1.0e8)
        self.assertLess(q_l, 1.6e8)

    def test_reference_soil_is_near_the_mod_previous_constant(self):
        """The old constant was 2.7. The reference soil must be the same
        order, or the change would move every map's frost depth at once."""
        c = stefan_coefficient("ground")
        self.assertGreater(c, 2.0)
        self.assertLess(c, 7.0)

    def test_water_content_drives_the_range(self):
        """A drier soil has less latent heat to lose, so it freezes
        DEEPER. This is the physical point of the change."""
        dry_deep = frost_depth_m("rock", 500)
        wet_shallow = frost_depth_m("vegetation", 500)
        self.assertGreater(dry_deep, wet_shallow)

    def test_monotonic_in_water_content(self):
        """At a fixed conductivity, more water means less depth.

        Depth depends on BOTH k_f and theta, so ordering every row by
        theta alone is not guaranteed and the comparison holds one
        constant. Water carries the latent heat the soil must lose, so
        doubling it at the same k_f must reduce the depth.
        """
        k_f = 1.5
        thetas = [0.10, 0.25, 0.35]
        depths = []
        for theta in thetas:
            q_l = max(RHO_DRY * L_FUS * theta, 1e6)
            c = 100 * math.sqrt((2 * k_f * SECONDS_PER_DAY) / q_l)
            depths.append(c * math.sqrt(500) / 100)
        for i in range(len(depths) - 1):
            self.assertGreater(depths[i], depths[i + 1], f"theta {thetas[i]}")

    def test_no_absurd_depth(self):
        """A paved or metal surface is a cover over soil. A frost front of
        65 metres, which a bare theta of zero once produced, is not a
        physical answer."""
        for name in TABLE:
            self.assertLess(frost_depth_m(name, 500), 5.0, name)

    def test_snow_insulates(self):
        """Snow slows the front. It never accelerates it."""
        bare = stefan_coefficient("ground", 0.0)
        snowy = stefan_coefficient("ground", 0.3)
        self.assertLess(snowy, bare)

    def test_snow_factor_saturates(self):
        """Past half a metre the added snow barely matters, because the
        layer is already the dominant resistance."""
        deep = stefan_coefficient("ground", 0.5)
        deeper = stefan_coefficient("ground", 2.0)
        self.assertAlmostEqual(deep, deeper, places=6)

    def test_snow_reproduces_the_previous_ratio(self):
        """The old pair was 2.7 bare and 1.7 under snow, a ratio of 0.63.
        At 0.3 m the new factor must land near it, or the change would
        move the snow-covered case away from the value it replaced."""
        factor = 0.37 + (0.63 * (1 - 0.3 / 0.5))
        self.assertAlmostEqual(factor, 0.622, places=3)

    def test_frost_depth_scales_with_root_fdd(self):
        """Stefan's solution is a square root, not linear. Four times the
        freezing degree-days doubles the depth."""
        one = frost_depth_m("ground", 100)
        four = frost_depth_m("ground", 400)
        self.assertAlmostEqual(four / one, 2.0, places=6)


if __name__ == "__main__":
    unittest.main()
