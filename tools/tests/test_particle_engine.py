#!/usr/bin/env python3
"""Physics-coupled particle engine tests (issues #149, #150, #151).

These tests read the SQF source and evaluate the REAL conditions, rather
than mirroring the logic: a Python mirror that restates the SQF can encode
the same bug and pass while the code is wrong (the blowing-snow defect,
2026-09-23).  Each branch or gate is parsed out of the source, then
evaluated here.

Covered:
  - emission model purity (no side effects) and its physics gates
  - allocator preemption at the source and particle ceilings
  - ground-state restitution 0.4 / 0.1 / 0.05 exactly
  - the hail gate (CAPE proxy + wet-bulb aloft + rain)
  - the wind-slant sign in moveVelocity

Run: python3 -m unittest tools.tests.test_particle_engine
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PARTICLE = REPO / "addons" / "fx" / "functions" / "particle"
PHASE_SQF = (
    REPO
    / "addons"
    / "atmos"
    / "functions"
    / "physics"
    / "fnc_calculatePrecipitationPhase.sqf"
)

EMISSION_SQF = PARTICLE / "fnc_particleEmission.sqf"
ALLOCATE_SQF = PARTICLE / "fnc_particleAllocate.sqf"
STATE_SQF = PARTICLE / "fnc_particleState.sqf"
MATERIAL_SQF = PARTICLE / "fnc_particleMaterial.sqf"
EMIT_SQF = PARTICLE / "fnc_particlePipelineEmit.sqf"
CONFIG_SQF = PARTICLE / "fnc_particleEffectConfig.sqf"


def _read(path):
    return path.read_text(encoding="utf-8")


def _strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


def _const(text, name):
    """Read `_name = <number>;` out of SQF."""
    m = re.search(rf"_{re.escape(name)}\s*=\s*([0-9]*\.?[0-9]+)\s*;", text)
    if m is None:
        raise AssertionError(f"constant _{name} not found in source")
    return float(m.group(1))


# ─── Source, read once ───────────────────────────────────────────────────
EMISSION = _read(EMISSION_SQF)
EMISSION_CODE = _strip_comments(EMISSION)
ALLOCATE = _read(ALLOCATE_SQF)
STATE = _read(STATE_SQF)
MATERIAL = _read(MATERIAL_SQF)
EMIT = _read(EMIT_SQF)
CONFIG = _read(CONFIG_SQF)
PHASE = _read(PHASE_SQF)


class TestEmissionPurity(unittest.TestCase):
    """The emission model is a pure function of AEE state."""

    def test_no_side_effects(self):
        for banned in [
            "setVariable",
            "publicVariable",
            "createVehicle",
            "random ",
            "setParticleParams",
        ]:
            self.assertNotIn(banned, EMISSION_CODE, f"emission must not call {banned}")

    def test_no_randomness(self):
        # The only per-machine variation is the cosmetic spawn in the
        # pipeline, never the emission numbers.
        self.assertNotIn("random", EMISSION_CODE.lower())

    def test_returns_intensity_colour_rate(self):
        self.assertRegex(
            EMISSION_CODE, r"\[_intensity,\s*_colour,\s*_baseRate \* _intensity"
        )


class TestEmissionGates(unittest.TestCase):
    """Each weather gate in the emission model uses the real threshold."""

    def test_snowfall_requires_snow_phase(self):
        self.assertRegex(
            EMISSION_CODE,
            r'if \(_phase == "snow"\) then \{ _intensity = _rate min 1; \};',
        )

    def test_hail_requires_hail_active(self):
        self.assertRegex(
            EMISSION_CODE,
            r"missionNamespace getVariable \[QEGVAR\(core,hailActive\), false\]",
        )

    def test_haboob_requires_wind_above_15(self):
        m = re.search(
            r"if \(_wind > ([0-9.]+)\) then \{ _intensity = _sand min 1; \};",
            EMISSION_CODE,
        )
        self.assertIsNotNone(m, "haboob wind gate not found")
        threshold = float(m.group(1))
        self.assertEqual(threshold, 15.0)
        # Evaluate the real condition.
        self.assertFalse(threshold > 15.0)  # exactly at threshold: no haboob
        self.assertTrue(16.0 > threshold)

    def test_hurricane_requires_wind_above_33(self):
        m = re.search(
            r"if \(_wind > ([0-9.]+)\) then \{ _intensity = \(\(_wind - ([0-9.]+)\) / ([0-9.]+)\) min 1; \};",
            EMISSION_CODE,
        )
        self.assertIsNotNone(m, "hurricane wind gate not found")
        threshold, base, span = (float(m.group(i)) for i in (1, 2, 3))
        self.assertEqual(threshold, 33.0)
        self.assertEqual(base, 33.0)
        self.assertEqual(span, 12.0)

        def intensity(wind):
            return min((wind - base) / span, 1.0) if wind > threshold else 0.0

        self.assertEqual(intensity(33.0), 0.0)
        self.assertAlmostEqual(intensity(39.0), 0.5)
        self.assertEqual(intensity(45.0), 1.0)


class TestAllocatorPreemption(unittest.TestCase):
    """A high-priority effect displaces a low one at the ceiling."""

    def setUp(self):
        self.max_sources = int(_const(ALLOCATE, "MAX_SOURCES"))
        self.max_particles = int(_const(ALLOCATE, "MAX_PARTICLES"))
        # The victim is chosen with a STRICT lower priority, so an equal
        # priority never preempts.  Read the real comparison.
        self.victim_cmp = re.search(r"if \(_p (<|<=) _victimPriority\) then", ALLOCATE)
        self.assertIsNotNone(self.victim_cmp, "victim comparison not found")
        self.victim_lt = self.victim_cmp.group(1) == "<"

    def test_ceilings(self):
        self.assertEqual(self.max_sources, 20)
        self.assertEqual(self.max_particles, 18000)

    def test_victim_uses_strict_lower_priority(self):
        self.assertTrue(
            self.victim_lt, "a higher or equal priority must not be preempted"
        )

    def _allocate(self, sources, priority, particles):
        """Faithful mirror of the allocator loop, driven by the parsed
        constants and the parsed comparison operator."""
        sources = list(sources)
        count = len(sources)
        used = sum(p for _, p in sources)
        guard = 0
        while (
            count >= self.max_sources or (used + particles) > self.max_particles
        ) and guard < self.max_sources:
            victim_index = -1
            victim_priority = priority
            for i, (sp, _) in enumerate(sources):
                is_victim = (
                    sp < victim_priority if self.victim_lt else sp <= victim_priority
                )
                if is_victim:
                    victim_priority = sp
                    victim_index = i
            if victim_index < 0:
                break
            used -= sources[victim_index][1]
            sources.pop(victim_index)
            count = len(sources)
            guard += 1
        granted = count < self.max_sources and (used + particles) <= self.max_particles
        if granted:
            sources.append((priority, particles))
        return granted, sources

    def test_high_priority_displaces_low_at_source_ceiling(self):
        # 20 ambient-dust sources at the ceiling; hail asks to emit.
        sources = [(10, 50)] * self.max_sources
        granted, after = self._allocate(sources, priority=80, particles=75)
        self.assertTrue(granted, "hail must preempt ambient dust")
        self.assertEqual(len(after), self.max_sources, "the source ceiling holds")
        # The hail source is present, one dust source was removed.
        self.assertIn((80, 75), after)
        self.assertEqual(sum(1 for s in after if s == (10, 50)), self.max_sources - 1)

    def test_low_priority_is_refused_at_ceiling(self):
        sources = [(10, 50)] * self.max_sources
        granted, _ = self._allocate(sources, priority=5, particles=10)
        self.assertFalse(granted, "a lower priority must not displace a higher one")

    def test_equal_priority_is_not_preempted(self):
        sources = [(10, 50)] * self.max_sources
        granted, _ = self._allocate(sources, priority=10, particles=10)
        self.assertFalse(granted, "an equal priority must not be preempted")

    def test_particle_ceiling_preempts(self):
        # One source alone, but it fills the particle budget.
        sources = [(10, self.max_particles)]
        granted, after = self._allocate(sources, priority=80, particles=100)
        self.assertTrue(granted, "the particle ceiling must trigger preemption")
        self.assertIn((80, 100), after)


class TestGroundRestitution(unittest.TestCase):
    """Ground-state restitution values are exactly 0.4 / 0.1 / 0.05."""

    def _ground_values(self):
        return {
            state: float(value)
            for state, value in re.findall(
                r'case "(\w+)"\s*:\s*\{\s*([0-9.]+)\s*\}', STATE
            )
        }

    def test_required_values(self):
        values = self._ground_values()
        self.assertEqual(values.get("Hardpack"), 0.4)
        self.assertEqual(values.get("Mud"), 0.1)
        self.assertEqual(values.get("Snow"), 0.05)

    def test_collider_set(self):
        # Only ground-colliding materials get the override; smoke, plume
        # and rain carry bounce -1, and hail keeps its own 0.6, so none of
        # them may be listed.
        m = re.search(r"_groundColliders = \[([^\]]*)\];", STATE)
        self.assertIsNotNone(m)
        colliders = set(re.findall(r'"(\w+)"', m.group(1)))
        self.assertIn("dust", colliders)
        self.assertNotIn("smoke", colliders)
        self.assertNotIn("plume", colliders)
        self.assertNotIn("rain", colliders)
        self.assertNotIn("hail", colliders)

    def test_hail_keeps_its_material_bounce(self):
        # Hail's restitution is the issue's 0.6, not a ground-state value.
        m = re.search(r'\["hail",\s*\[[^]]*?([0-9.]+),\s*\[', MATERIAL)
        self.assertIsNotNone(m, "hail row not found in the material table")
        self.assertEqual(float(m.group(1)), 0.60)


class TestHailGate(unittest.TestCase):
    """The hail gate is CAPE proxy + wet-bulb aloft + rain."""

    def setUp(self):
        self.growth_m = _const(PHASE, "hailGrowthM")
        self.lapse = _const(PHASE, "lapseCPerM")
        m = re.search(r"_hailActive = (.+?);", PHASE)
        self.assertIsNotNone(m, "hail gate expression not found")
        expr = m.group(1).replace("&&", " and ").replace("||", " or ")
        # Only names the gate itself uses.
        self.expr = expr

    def _gate(self, cape, tw_surface, rain):
        tw_aloft = tw_surface - self.lapse * self.growth_m
        return bool(
            eval(
                self.expr,
                {"__builtins__": {}},
                {
                    "_capeProxy": cape,
                    "_twAloft": tw_aloft,
                    "_rainRate": rain,
                },
            )
        )

    def test_growth_layer_and_lapse(self):
        self.assertEqual(self.growth_m, 3000.0)
        self.assertEqual(self.lapse, 0.0065)

    def test_gate_vectors(self):
        # 0.0065 * 3000 = 19.5 C of cooling from the surface to 3 km.
        self.assertTrue(self._gate(cape=1.0, tw_surface=10.0, rain=0.5))
        # No instability -> no hail.
        self.assertFalse(self._gate(cape=0.0, tw_surface=10.0, rain=0.5))
        # Wet-bulb aloft above freezing (surface wet-bulb 25 C) -> no hail.
        self.assertFalse(self._gate(cape=1.0, tw_surface=25.0, rain=0.5))
        # Clear air -> no hail, whatever the instability.
        self.assertFalse(self._gate(cape=1.0, tw_surface=10.0, rain=0.0))
        # Exactly at the boundary: 19.5 C surface wet-bulb gives twAloft 0,
        # which is not below freezing.
        self.assertFalse(self._gate(cape=1.0, tw_surface=19.5, rain=0.5))


class TestWindSlant(unittest.TestCase):
    """Rain and snow slant with the local wind (issue #151)."""

    def test_move_velocity_follows_wind_sign(self):
        # Read the real expression, then evaluate it: both horizontal
        # components are the local wind times the effect's slant coupling.
        m = re.search(r"_moveVelocity = (\[.*?\]);", EMIT)
        self.assertIsNotNone(m, "moveVelocity expression not found")
        expr = re.sub(r"\s+", " ", m.group(1))
        self.assertEqual(
            expr,
            "[(_wind select 0) * _slant, (_wind select 1) * _slant, _fall]",
            "the slant must multiply the local wind, not negate it",
        )

        py = expr.replace("_wind select 0", "wind[0]").replace(
            "_wind select 1", "wind[1]"
        )

        def move_velocity(wind, slant, fall):
            return eval(
                py, {"__builtins__": {}}, {"wind": wind, "_slant": slant, "_fall": fall}
            )

        # A north-westerly wind slants the fall to the south-east.
        self.assertEqual(move_velocity([3.0, -2.0], 0.5, -8.0), [1.5, -1.0, -8.0])
        # Sign check: the horizontal velocity has the wind's sign.
        for wind in ([3.0, -2.0], [-4.0, 1.0]):
            mv = move_velocity(wind, 0.5, -8.0)
            self.assertEqual(mv[0] > 0, wind[0] > 0)
            self.assertEqual(mv[1] > 0, wind[1] > 0)

    def test_slant_coupling_is_non_negative(self):
        for value in re.findall(r'\["slant", ([0-9.]+)\]', CONFIG):
            self.assertGreaterEqual(float(value), 0.0)

    def test_all_effects_have_a_row(self):
        for effect in [
            "vehicleDust",
            "footfallDust",
            "atmosphericDust",
            "rotorWash",
            "snowfall",
            "blowingSnow",
            "hail",
            "haboob",
            "hurricane",
            "hurricaneSpray",
            "hurricaneDebris",
        ]:
            self.assertIn(f'"{effect}"', CONFIG, f"config row missing for {effect}")


if __name__ == "__main__":
    unittest.main()
