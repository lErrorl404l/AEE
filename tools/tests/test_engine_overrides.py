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
            velocity, _reason = gen.nature_muzzle_velocity(binding, loads, projectiles)
            if velocity is None:
                self.assertNotIn(binding.game_class, emitted)
                continue
            self.assertIn(binding.game_class, emitted)
            self.assertAlmostEqual(
                float(emitted[binding.game_class]), velocity.value_ms, places=6
            )


# Published service velocities, independent of the corpus, for the natures
# the vanilla tank guns fire.  A gun fires each nature at its own velocity,
# so the M829 APFSDS figure must never reach a HEAT or HE magazine.
#   M829 APFSDS-T 1670 m/s, M830 HEAT-MP-T 1140 m/s (TM 43-0001-28)
#   M456 HEAT-T (105 mm M68) 1173 m/s (TM 43-0001-28)
REAL_SERVICE_VELOCITY = {
    "30Rnd_120mm_APFSDS_shells": (1670.0, 0.02),
    "20Rnd_120mm_HEAT_MP": (1140.0, 0.02),
    "20Rnd_105mm_HEAT_MP": (1173.0, 0.02),
    "30Rnd_556x45_Stanag": (914.0, 0.02),
    "20Rnd_762x51_Mag": (838.0, 0.02),
}

# Magazines whose initSpeed is not a single cartridge service velocity, or
# whose cartridge the corpus cannot identify, keep the vanilla value:
#   artillery/mortar (artilleryCharge[] scales initSpeed), the SDAR
#   underwater dart (270 m/s), the 30x173 mm cannons (GAU-8 and Mk44 hold no
#   documented nature load), and the 40 mm cannon (not the 40x46 grenade).
NEVER_OVERRIDDEN = (
    "6Rnd_155mm_Mo_smoke",
    "32Rnd_155mm_Mo_shells",
    "20Rnd_556x45_UW_mag",
    "1000Rnd_Gatling_30mm_Plane_CAS_01_F",
    "250Rnd_30mm_HE_shells",
    "60Rnd_30mm_APFSDS_shells",
    "140Rnd_30mm_MP_shells",
    "40Rnd_40mm_APFSDS_shells",
    "30Rnd_120mm_HE_shells",
    "PylonWeapon_500Rnd_127mm_HEIAP_belt_right",
)


class TestRealWorldTruth(unittest.TestCase):
    def test_each_nature_carries_its_own_service_velocity(self) -> None:
        emitted = _emitted(MAG_SRC, "initSpeed")
        for game_class, (real, tolerance) in REAL_SERVICE_VELOCITY.items():
            self.assertIn(game_class, emitted)
            value = float(emitted[game_class])
            self.assertLess(
                abs(value - real) / real, tolerance,
                f"{game_class}: {value} m/s vs published {real} m/s",
            )

    def test_engine_owned_and_unidentified_magazines_are_untouched(self) -> None:
        emitted = _emitted(MAG_SRC, "initSpeed")
        for game_class in NEVER_OVERRIDDEN:
            self.assertNotIn(game_class, emitted)

    def test_mass_is_written_in_the_engine_unit(self) -> None:
        # A loaded 30-round aluminium STANAG is ~0.49 kg; vanilla holds 8
        # (0.36 kg).  The engine unit is 0.1 lb, so kg written raw (0.51)
        # would make the magazine weigh 23 g.
        masses = _emitted(MAG_SRC, "mass")
        kg = float(masses["30Rnd_556x45_Stanag"]) * 0.045359237
        self.assertGreater(kg, 0.40)
        self.assertLess(kg, 0.60)

    def test_a_bare_calibre_token_never_binds(self) -> None:
        aliases = gen.cartridge_index()
        for token in ("30mm", "40mm", "120mm", "105mm", "155mm"):
            self.assertNotIn(token, aliases)
        self.assertIsNone(gen.resolve_cartridge(aliases, "Smoke_120mm_AMOS_White"))
        self.assertEqual(gen.ammo_nature("B_127x99_HEIAP_Tracer_Red"), "heiap")
        self.assertEqual(gen.ammo_nature("Sh_120mm_HEAT_MP"), "heat")
        self.assertEqual(gen.ammo_nature("B_762x51_Tracer_Green"), "ball")


class TestAmmoAirFriction(unittest.TestCase):
    """airFriction is the constant whose supersonic time of flight equals the
    real flight under the held BC and standard drag curve."""

    def _drop_errors(self, projectile_id: str, v0: float, k: float) -> list[float]:
        import math
        bc = gen.load_projectiles()[projectile_id]["values"]["bc_g7"]["value"]
        table = gen.load_drag_table("G7")
        x_end, _ = gen.supersonic_time_of_flight(table, bc, v0)
        errs, x, t, v = [], 0.0, 0.0, v0
        while x < x_end:
            kk = gen.DRAG_CONSTANT * gen.interpolate_cd(table, v / gen.SPEED_OF_SOUND_15C) / bc
            vn = v * math.exp(-kk * 0.5)
            t += 1.0 / (v + vn)
            v = vn
            x += 0.5
            tc = (math.exp(k * x) - 1) / (k * v0)
            errs.append(0.5 * 9.80665 * (tc * tc - t * t))
        return errs

    def test_drop_matches_the_real_curve_over_the_supersonic_range(self):
        emitted = _emitted(AMMO_SRC, "airFriction")
        for game_class, pid, v0, bound_m in (
            ("B_556x45_Ball", "apg_m855", 914.4, 0.06),
            ("B_762x51_Ball", "apg_m80", 838.2, 0.06),
            ("B_127x99_Ball", "apg_m33", 886.97, 0.25),
        ):
            k = -float(emitted[game_class])
            worst = max(abs(e) for e in self._drop_errors(pid, v0, k))
            self.assertLess(worst, bound_m, f"{game_class}: drop error {worst:.3f} m")

    def test_beats_the_muzzle_only_coefficient(self):
        # The old muzzle-Mach coefficient under-predicts drop by ~0.3 m at
        # 600 m for M80; the time-of-flight fit must do better everywhere.
        emitted = _emitted(AMMO_SRC, "airFriction")
        bc = gen.load_projectiles()["apg_m80"]["values"]["bc_g7"]["value"]
        cd = gen.interpolate_cd(gen.load_drag_table("G7"), 838.2 / gen.SPEED_OF_SOUND_15C)
        k_muzzle = gen.DRAG_CONSTANT * cd / bc
        fit = max(abs(e) for e in self._drop_errors("apg_m80", 838.2, -float(emitted["B_762x51_Ball"])))
        muzzle = max(abs(e) for e in self._drop_errors("apg_m80", 838.2, k_muzzle))
        self.assertLess(fit, muzzle / 3)

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
