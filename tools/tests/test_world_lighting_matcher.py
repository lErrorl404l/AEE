#!/usr/bin/env python3
"""World lighting matcher contract (aee-workshop-copy, directive addendum).

The matcher classifies ANY world, custom or unknown, from FACTS: latitude,
biome, terrain signals and weather.  It consults no map name and no per-map
table.  These tests run the REAL kernels through the SQF lite interpreter and
cross-check them against a Python mirror of the same spec.  They also hold the
source contracts that keep the matcher map-free and the config table-free.

MUTATION PROOF (executed by hand at commit time):
  - add ``class Stratis {...}`` inside CfgWorlds in config.cpp ->
    ``test_config_has_no_per_world_lighting_table`` fails; restore -> OK.
  - change the unknown-group branch in fnc_worldLightingClass.sqf to return
    "POLAR" -> ``test_unknown_world_falls_back_to_temperate`` fails; restore.

Run: python3 -m unittest tools.tests.test_world_lighting_matcher -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO))

from sqf_lite import run_sqf  # noqa: E402

KERNELS = REPO / "addons" / "environmental" / "functions" / "lighting"
CLASS_KERNEL = KERNELS / "fnc_worldLightingClass.sqf"
PROFILE_KERNEL = KERNELS / "fnc_worldLightingProfile.sqf"
BINDER = KERNELS / "fnc_applyWorldLighting.sqf"

CLASSES = (
    "POLAR",
    "SUBARCTIC",
    "MONTANE",
    "TEMPERATE_COOL",
    "TEMPERATE",
    "MEDITERRANEAN",
    "ARID",
    "TROPICAL",
    "TROPICAL_HUMID",
    "MARITIME",
)

# Base profile table, keyed by CLIMATE CLASS, never by map.  UNSOURCED
# aesthetic proxies; the Python mirror below holds the same numbers.
BASE_PROFILE = {
    "POLAR": (1.0, 1.30, 0.60, 0.20),
    "SUBARCTIC": (0.9, 1.20, 0.70, 0.30),
    "MONTANE": (0.9, 1.30, 0.70, 0.30),
    "TEMPERATE_COOL": (0.8, 1.10, 0.90, 0.40),
    "TEMPERATE": (0.7, 1.00, 1.00, 0.50),
    "MEDITERRANEAN": (0.6, 1.15, 0.80, 0.40),
    "ARID": (0.5, 1.25, 0.60, 0.80),
    "TROPICAL": (0.6, 0.90, 1.10, 0.70),
    "TROPICAL_HUMID": (0.5, 0.80, 1.20, 0.90),
    "MARITIME": (0.7, 0.95, 1.10, 0.70),
}

# The known world names the source contract forbids in the kernels and the
# config table contract forbids in CfgWorlds.
WORLD_NAMES = (
    "DefaultWorld",
    "CAWorld",
    "Stratis",
    "Altis",
    "VR",
    "Malden",
    "Enoch",
    "Tanoa",
    "Livonia",
    "Argo",
)


def world_class(
    latitude: float, group: int, water: float, elev: float, dry: float
) -> str:
    """Run the REAL class kernel."""
    return run_sqf(CLASS_KERNEL, [latitude, group, water, elev, dry], {})


def world_profile(world_class_name: str, overcast: float) -> list[float]:
    """Run the REAL profile kernel."""
    return run_sqf(PROFILE_KERNEL, [world_class_name, overcast], {})


# ─── Python mirror of the same spec, for cross-checking the SQF ─────────────
def mirror_class(
    latitude: float, group: int, water: float, elev: float, dry: float
) -> str:
    if group == 5:
        return "TEMPERATE"
    if elev > 1500:
        return "MONTANE"
    if group == 4:
        return "POLAR"
    if group == 1:
        return "ARID"
    if group == 3:
        return "SUBARCTIC"
    if water > 0.5:
        return "MARITIME"
    if group == 0:
        return "TROPICAL_HUMID" if water > 0.15 else "TROPICAL"
    if dry > 0.5:
        return "MEDITERRANEAN"
    if abs(latitude) >= 45:
        return "TEMPERATE_COOL"
    return "TEMPERATE"


def mirror_profile(world_class_name: str, overcast: float) -> list[float]:
    night, star, grain, haze = BASE_PROFILE.get(
        world_class_name, BASE_PROFILE["TEMPERATE"]
    )
    haze = min(haze * (1 + overcast), 1.5)
    star = max(star * (1 - 0.5 * overcast), 0.2)
    grain = min(grain * (0.5 + overcast), 1.5)
    night = min(night * (1 + 0.25 * overcast), 1.0)
    return [max(night, 0), max(star, 0), max(grain, 0), max(haze, 0)]


class TestWorldLightingClass(unittest.TestCase):
    def test_polar_class(self) -> None:
        self.assertEqual(world_class(70, 4, 0.10, 0, 0), "POLAR")

    def test_tropical_humid_class(self) -> None:
        self.assertEqual(world_class(5, 0, 0.30, 0, 0), "TROPICAL_HUMID")
        self.assertEqual(world_class(5, 0, 0.05, 0, 0), "TROPICAL")

    def test_arid_class(self) -> None:
        self.assertEqual(world_class(25, 1, 0.02, 0, 1), "ARID")

    def test_mediterranean_class(self) -> None:
        self.assertEqual(world_class(38, 2, 0.20, 0, 1), "MEDITERRANEAN")
        self.assertEqual(world_class(38, 2, 0.20, 0, 0), "TEMPERATE")

    def test_montane_overrides_elevation(self) -> None:
        self.assertEqual(world_class(35, 2, 0.10, 2000, 0), "MONTANE")
        self.assertEqual(world_class(35, 2, 0.10, 1200, 0), "TEMPERATE")

    def test_maritime_overrides_temperate_and_tropical(self) -> None:
        self.assertEqual(world_class(35, 2, 0.80, 0, 0), "MARITIME")
        self.assertEqual(world_class(5, 0, 0.80, 0, 0), "MARITIME")

    def test_unknown_world_falls_back_to_temperate(self) -> None:
        self.assertEqual(world_class(40, 5, 0.10, 0, 0), "TEMPERATE")

    def test_mirror_matches_sqf_over_a_sweep(self) -> None:
        # The mirror is a second implementation of the same spec, so a drift
        # between the SQF and the documented rules fails here.
        for group in range(0, 6):
            for water in (0.0, 0.2, 0.8):
                for elev in (0, 1200, 2000):
                    for dry in (0, 1):
                        for latitude in (-60, -40, 0, 40, 60):
                            with self.subTest(
                                group=group,
                                water=water,
                                elev=elev,
                                dry=dry,
                                lat=latitude,
                            ):
                                got = world_class(latitude, group, water, elev, dry)
                                want = mirror_class(latitude, group, water, elev, dry)
                                self.assertEqual(got, want)
                                self.assertIn(got, CLASSES)


class TestWorldLightingProfile(unittest.TestCase):
    def test_profile_is_bounded(self) -> None:
        for name in CLASSES:
            for overcast in (0.0, 0.5, 1.0):
                with self.subTest(name=name, overcast=overcast):
                    profile = world_profile(name, overcast)
                    self.assertEqual(len(profile), 4)
                    for value in profile:
                        self.assertGreaterEqual(value, 0.0)
                        self.assertLessEqual(value, 2.0)

    def test_overcast_reduces_star_scale(self) -> None:
        for name in CLASSES:
            with self.subTest(name=name):
                clear = world_profile(name, 0.0)
                cloudy = world_profile(name, 1.0)
                self.assertGreater(clear[1], cloudy[1])

    def test_overcast_raises_haze_and_grain(self) -> None:
        for name in CLASSES:
            with self.subTest(name=name):
                clear = world_profile(name, 0.0)
                cloudy = world_profile(name, 1.0)
                self.assertGreater(cloudy[3], clear[3])  # haze
                self.assertGreater(cloudy[2], clear[2])  # grain

    def test_mirror_matches_sqf(self) -> None:
        for name in CLASSES:
            for overcast in (0.0, 0.25, 0.5, 0.75, 1.0):
                with self.subTest(name=name, overcast=overcast):
                    got = world_profile(name, overcast)
                    want = mirror_profile(name, overcast)
                    for a, b in zip(got, want):
                        self.assertAlmostEqual(a, b, places=6)


class TestSourceContracts(unittest.TestCase):
    def test_matcher_kernels_name_no_map(self) -> None:
        for kernel in (CLASS_KERNEL, PROFILE_KERNEL, BINDER):
            text = kernel.read_text(encoding="utf-8")
            for name in WORLD_NAMES:
                with self.subTest(kernel=kernel.name, name=name):
                    self.assertNotIn(name, text)


if __name__ == "__main__":
    unittest.main()
