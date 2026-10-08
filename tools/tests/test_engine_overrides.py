#!/usr/bin/env python3
"""Engine override tests.

The two implemented overrides are checked against their sources:

  * CfgMagazines initSpeed against data/ballistics/loads.json;
  * CfgAmmo airFriction against the held ballistic coefficient and the held
    standard drag curve, at the reference muzzle Mach.

The register, the generated headers and the generator are checked too, so a
stale header, a silent surface or a bare reopen fails the suite.

Run: python3 -m unittest tools.tests.test_engine_overrides -v
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.validation import gen_engine_overrides as gen  # noqa: E402
from tools.validation import validate_engine_overrides as validate  # noqa: E402

MAG_SRC = gen.MAG_OUT.read_text(encoding="utf-8")
AMMO_SRC = gen.AMMO_OUT.read_text(encoding="utf-8")

# The vanilla airFriction of the service ball rounds, read from the base game
# config (weapons_f.pbo). The derived value must sit near it, which shows the
# derivation is the engine's own drag form and not a wild guess.
VANILLA_AIRFRICTION = {
    "B_556x45_Ball": -0.0012,
    "B_762x51_Ball": -0.001,
}


def _emitted(text: str, key: str) -> dict[str, str]:
    """Return {class: value} for each emitted key in a generated header."""
    out: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        match = re.match(r"\s+class\s+([A-Za-z0-9_]+):\s*([A-Za-z0-9_]+)\s*\{", line)
        if match:
            current = match.group(1)
            continue
        value = re.match(rf"\s+{key}\s*=\s*(-?[0-9.]+);", line)
        if value and current is not None:
            out[current] = value.group(1)
    return out


class TestGeneratedFresh(unittest.TestCase):
    def test_headers_and_register_are_fresh(self) -> None:
        self.assertEqual(gen.check(), 0, "run the generator")

    def test_validator_passes(self) -> None:
        self.assertEqual(validate.main(), 0)


class TestMagazineInitSpeed(unittest.TestCase):
    def test_core_magazine_carries_the_service_velocity(self) -> None:
        # 5.56 NATO service round M855: 914.4 m/s (mil_specs, documented).
        emitted = _emitted(MAG_SRC, "initSpeed")
        self.assertIn("30Rnd_556x45_Stanag", emitted)
        self.assertAlmostEqual(float(emitted["30Rnd_556x45_Stanag"]), 914.4, places=3)

    def test_762_magazine_carries_the_service_velocity(self) -> None:
        # 7.62 NATO service round M80: 838.2 m/s (mil_specs, documented).
        emitted = _emitted(MAG_SRC, "initSpeed")
        self.assertIn("20Rnd_762x51_Mag", emitted)
        self.assertAlmostEqual(float(emitted["20Rnd_762x51_Mag"]), 838.2, places=3)

    def test_every_value_traces_to_loads_json(self) -> None:
        loads = gen.load_loads()
        projectiles = gen.load_projectiles()
        emitted = _emitted(MAG_SRC, "initSpeed")
        self.assertTrue(emitted)
        for binding in gen.load_magazine_bindings():
            velocity = gen.cartridge_muzzle_velocity(
                binding.cartridge_id, loads, projectiles
            )
            if velocity is None:
                self.assertNotIn(binding.game_class, emitted)
                continue
            self.assertIn(binding.game_class, emitted)
            self.assertAlmostEqual(
                float(emitted[binding.game_class]), velocity.value_ms, places=6
            )


class TestAmmoAirFriction(unittest.TestCase):
    def test_derivation_matches_the_formula(self) -> None:
        # Independent recomputation from the held coefficient and curve.
        projectiles = gen.load_projectiles()
        loads = gen.load_loads()
        velocity = gen.cartridge_muzzle_velocity("556x45_nato", loads, projectiles)
        assert velocity is not None
        bc = projectiles["apg_m855"]["values"]["bc_g7"]["value"]
        mach = velocity.value_ms / 340.29
        table = gen.load_drag_table("G7")
        cd = None
        for (m0, c0), (m1, c1) in zip(table, table[1:]):
            if m0 <= mach <= m1:
                cd = c0 + (c1 - c0) * (mach - m0) / (m1 - m0)
                break
        assert cd is not None
        expected = -0.00068418 * cd / bc
        emitted = _emitted(AMMO_SRC, "airFriction")
        self.assertAlmostEqual(float(emitted["B_556x45_Ball"]), expected, places=9)

    def test_derivation_corroborates_the_vanilla_value(self) -> None:
        emitted = _emitted(AMMO_SRC, "airFriction")
        for game_class, vanilla in VANILLA_AIRFRICTION.items():
            self.assertIn(game_class, emitted)
            derived = float(emitted[game_class])
            self.assertLess(
                abs(derived - vanilla) / abs(vanilla),
                0.10,
                f"{game_class}: derived {derived} vs vanilla {vanilla}",
            )

    def test_only_ball_rounds_are_bound(self) -> None:
        emitted = _emitted(AMMO_SRC, "airFriction")
        self.assertTrue(emitted)
        for game_class in emitted:
            self.assertIn("ball", game_class.lower())
            self.assertNotIn("tracer", game_class.lower())


class TestHeaderShape(unittest.TestCase):
    def test_no_bare_reopen(self) -> None:
        for text in (MAG_SRC, AMMO_SRC):
            for line in text.splitlines():
                self.assertIsNone(
                    validate._BARE_CLASS.match(line), f"bare reopen: {line.strip()}"
                )

    def test_withheld_magazines_are_named(self) -> None:
        # A withheld binding is recorded, never silent.
        self.assertIn("// Withheld bindings", MAG_SRC)


class TestRegister(unittest.TestCase):
    def test_reference_surfaces_are_present(self) -> None:
        ids = {record["id"] for record in gen.load_verdicts()}
        for expected in (
            "cfgmagazines-initspeed",
            "cfgammo-airfriction",
            "cfgmagazines-tracersevery",
            "cfglights",
            "cfgsurfaces-friction",
            "cfgenvsounds",
            "cfgvehicleicons",
        ):
            self.assertIn(expected, ids)

    def test_every_surface_states_a_reason(self) -> None:
        for record in gen.load_verdicts():
            self.assertTrue(str(record.get("reason", "")).strip(), record["id"])

    def test_reject_names_a_ceiling(self) -> None:
        for record in gen.load_verdicts():
            if record["verdict"] == "REJECT":
                self.assertTrue(str(record.get("ceiling", "")).strip(), record["id"])


if __name__ == "__main__":
    unittest.main()
