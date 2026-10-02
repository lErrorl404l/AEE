#!/usr/bin/env python3
"""The identity matchers localise only a $STR key.

A class displayName holds either a stringtable key (``$STR_...``) or plain
text (``AH-9 Pawnee``). ``localize`` is valid only on the key. When a
matcher passes plain text to ``localize`` the engine raises
``String <name> not found``. The identity ladder runs every frame from the
traction classifier, so the error repeats without limit.

Each matcher must run ``localize`` only when the raw value starts with
``$``, and pass any other value through unchanged. The generated files are
pinned to that exact guard, and each generator is pinned to the same
template so a regeneration cannot reintroduce the unguarded call. The
equipment item-mass generator holds no ``localize`` call at all.

Run: python3 -m unittest tools.tests.test_localize_guard -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]

# The exact expression every matcher carries. A plain-text displayName is
# returned unchanged, a $STR key is localised, an empty value stays empty.
GUARD = (
    'private _localName = if ((_rawName select [0,1]) == "$") '
    "then { localize _rawName } else { _rawName };"
)

# (generator, generated matcher, identity line that must survive)
MATCHERS = (
    (
        REPO / "tools/validation/gen_vehicle_data.py",
        REPO / "addons/mobility/functions/fnc_getVehicleMatch.sqf",
        '_identity = _className + " " + _rawName + " " + _localName',
    ),
    (
        REPO / "tools/validation/gen_runtime_weapons.py",
        REPO / "addons/ballistics/functions/fnc_getWeaponData.sqf",
        '_identity = _weapon + " " + _rawName + " " + _localName',
    ),
    (
        REPO / "tools/validation/gen_runtime_cartridges.py",
        REPO / "addons/ballistics/functions/fnc_getCartridgeData.sqf",
        '[_ammo + " " + _rawName + " " + _localName]',
    ),
    (
        REPO / "tools/validation/gen_runtime_projectiles.py",
        REPO / "addons/ballistics/functions/fnc_getProjectileData.sqf",
        '[_ammo + " " + _rawName + " " + _localName]',
    ),
    (
        REPO / "tools/validation/gen_device_data.py",
        REPO / "addons/nightvision/functions/fnc_getDeviceMatch.sqf",
        '_identity = _className + " " + _rawName + " " + _localName',
    ),
)

# The unguarded call: localise anything. This is the defect shape.
OLD_SHAPE = "else { localize _rawName }"
# But the guard itself contains `else { _rawName }`, so the old shape is the
# empty-check tail, which the guard replaces.
OLD_EMPTY_CHECK = 'if (_rawName == "") then { "" } else { localize _rawName }'


def localise(raw: str, localize) -> str:
    """Mirror of the guard. `localize` records the call and returns text.

    A value that starts with "$" is a stringtable key and is localised.
    Any other value, including an empty value, is returned unchanged.
    """
    if raw[0:1] == "$":
        return localize(raw)
    return raw


class TestGuardMirror(unittest.TestCase):
    """The branch rule: plain text is never passed to localize."""

    def setUp(self):
        self.calls: list[str] = []

        def _localize(key: str) -> str:
            self.calls.append(key)
            return "LOCALISED"

        self.localize = _localize

    def test_plain_text_is_not_localised(self):
        self.assertEqual(localise("AH-9 Pawnee", self.localize), "AH-9 Pawnee")
        self.assertEqual(self.calls, [])

    def test_a_str_key_is_localised(self):
        self.assertEqual(localise("$STR_A3_Pawnee", self.localize), "LOCALISED")
        self.assertEqual(self.calls, ["$STR_A3_Pawnee"])

    def test_an_empty_value_is_an_empty_string(self):
        self.assertEqual(localise("", self.localize), "")
        self.assertEqual(self.calls, [])


class TestGeneratedMatchers(unittest.TestCase):
    """Every committed matcher carries the guard and keeps its identity."""

    def check(self, generator: Path, matcher: Path, identity: str):
        text = matcher.read_text(encoding="utf-8")
        self.assertIn(GUARD, text, f"{matcher.name} has no $STR guard")
        self.assertNotIn(OLD_SHAPE, text, f"{matcher.name} has an unguarded localize")
        self.assertNotIn(
            OLD_EMPTY_CHECK, text, f"{matcher.name} has the empty-check localize"
        )
        self.assertIn(identity, text, f"{matcher.name} lost its identity text")
        # One localize site per matcher, inside the guard.
        self.assertEqual(
            len(re.findall(r"\blocalize\b", text)),
            1,
            f"{matcher.name} has more than one localize",
        )

    def test_vehicle(self):
        self.check(*MATCHERS[0])

    def test_weapons(self):
        self.check(*MATCHERS[1])

    def test_cartridges(self):
        self.check(*MATCHERS[2])

    def test_projectiles(self):
        self.check(*MATCHERS[3])

    def test_the_equipment_path_does_not_localise(self):
        # The clothing/equipment item-mass resolver reads a classname only and
        # never calls localize. Pin it so a later change cannot add one
        # without this guard.
        text = (
            REPO / "addons/physiology/functions/clothing/fnc_getItemMass.sqf"
        ).read_text(encoding="utf-8")
        self.assertNotIn("localize", text)


class TestGeneratorsCarryTheGuard(unittest.TestCase):
    """A regeneration cannot reintroduce the unguarded call."""

    def test_each_generator_holds_the_guard(self):
        for generator, _matcher, _identity in MATCHERS:
            text = generator.read_text(encoding="utf-8")
            self.assertIn(GUARD, text, f"{generator.name} has no $STR guard")
            self.assertNotIn(
                OLD_EMPTY_CHECK,
                text,
                f"{generator.name} holds the empty-check localize",
            )

    def test_the_equipment_generator_does_not_localise(self):
        text = (REPO / "tools/validation/gen_equipment_data.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("localize", text)


class TestNoProvenance(unittest.TestCase):
    """No agent, model or tooling provenance is committed in the test target."""

    def test_no_provenance(self):
        marked = ("Agent:", "opencode-go", "deepseek", "glm-", "anthropic", "claude")
        for _generator, matcher, _identity in MATCHERS:
            text = matcher.read_text(encoding="utf-8").lower()
            for marker in marked:
                self.assertNotIn(
                    marker.lower(), text, f"{matcher.name} carries {marker}"
                )


if __name__ == "__main__":
    unittest.main()
