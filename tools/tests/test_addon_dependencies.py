"""Addon dependency guards (issue #203).

Two addons used to depend on each other: `environmental` called
`thermal.calculateStefanCoefficient` for its freeze/thaw and ice-load
models, while `thermal.updateTemperature` called four `environmental`
climate and terrain functions. Neither addon could then be built, loaded or
reasoned about independently, and a load-order change could break one of
them.

The coefficient is a soil property: it reads a surface class and a snow
depth and returns a value derived from the soil's conductivity, water
content and latent heat. It now lives in `material`, the leaf addon both
the others already depend on, so the cycle is gone.

These checks read the SOURCE. A mirror of the dependency graph would prove
nothing about the graph.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"

# EFUNC(component,name) in a call, or EGVAR(component,name) in a variable
# name, is the cross-addon edge.
CALL = re.compile(r"EFUNC\(\s*([a-z_]+)\s*,")
VAR = re.compile(r"[QE]?EGVAR\(\s*([a-z_]+)\s*,")


def dependencies(addon):
    """Components this addon reaches into, excluding itself.

    Compat addons are excluded: they load only when their host mod is
    present, and an optional read of a compat variable is not a graph edge
    in the core addon set.
    """
    found = set()
    for path in (ADDONS / addon).rglob("*.sqf"):
        text = path.read_text(encoding="utf-8", errors="replace")
        found.update(CALL.findall(text))
        found.update(VAR.findall(text))
    found.discard(addon)
    found = {d for d in found if not d.startswith("compat_")}
    return found


class TestNoCycle(unittest.TestCase):
    def test_environmental_does_not_depend_on_thermal(self):
        """The direction that closed the cycle must stay closed."""
        self.assertNotIn(
            "thermal",
            dependencies("environmental"),
            "environmental reaches into thermal again: the cycle is back",
        )

    def test_material_is_still_a_leaf(self):
        """The shared owner must depend on nothing but itself.

        The coefficient was moved here because both sides can depend on a
        leaf. If material ever gains a cross-addon edge, the cycle can
        return through the back door.
        """
        self.assertEqual(
            dependencies("material"),
            set(),
            "material is no longer a leaf; the cycle can return",
        )

    def test_the_coefficient_lives_in_material(self):
        self.assertTrue(
            (ADDONS / "material" / "functions" / "fnc_calculateStefanCoefficient.sqf").exists(),
            "the Stefan coefficient is not in material",
        )
        self.assertFalse(
            (ADDONS / "thermal" / "functions" / "ground" / "fnc_calculateStefanCoefficient.sqf").exists(),
            "the Stefan coefficient is still in thermal",
        )
        prep = (ADDONS / "material" / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(calculateStefanCoefficient)", prep)
        old_prep = (ADDONS / "thermal" / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertNotIn("calculateStefanCoefficient", old_prep)

    def test_callers_use_the_new_owner(self):
        """The call sites must name material, not thermal."""
        for name in ("fnc_calculateFreezeThawCycling.sqf", "fnc_calculateIceLoad.sqf"):
            text = (ADDONS / "environmental" / "functions" / "terrain" / name).read_text(
                encoding="utf-8"
            )
            self.assertIn("EFUNC(material,calculateStefanCoefficient)", text)
            self.assertNotIn("EFUNC(thermal,calculateStefanCoefficient)", text)
