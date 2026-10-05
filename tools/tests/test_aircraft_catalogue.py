#!/usr/bin/env python3
"""Aircraft catalogue and class-binding loader tests.

The aircraft corpus is a sibling of the vehicle corpus. It shares the read
path in ``tools/validation/vehicle_catalogue.py`` and selects the aircraft
behaviour through ``AIRCRAFT_PROFILE``: the type enum, the per-type runtime
sets and the named derivations. This module holds the loader-level contract.
The content tests live beside it and extend it.

The fixtures live in a temporary directory. They hold sentinel values only and
they are never written to the corpus.

Run: python3 -m unittest tools.tests.test_aircraft_catalogue -v
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import vehicle_catalogue as vc  # noqa: E402

JsonObject = dict[str, object]


def _value(value: object, unit: str, source: str = "fx_manual") -> JsonObject:
    """A complete held value object, as the schema requires."""
    return {
        "value": value,
        "unit": unit,
        "source": source,
        "locator": "FIXTURE locator",
        "state": "FIXTURE state",
        "grade": "documented",
    }


def _entry(catalogue_id: str, **overrides: object) -> JsonObject:
    entry: JsonObject = {
        "catalogue_id": catalogue_id,
        "canonical_name": catalogue_id.upper(),
        "maker": "FIXTURE",
        "model": "FIXTURE",
        "variant": "FIXTURE",
        "variant_id": f"{catalogue_id}_variant",
        "vehicle_type": "fixed_wing",
        "propulsion": "turbojet",
        "class_token": "Plane",
        "country": "NONE",
        "era": "none",
        "aliases": [],
        "keywords": [],
        "runtime_ready": False,
        "values": {},
    }
    entry.update(overrides)
    return entry


def _capture(entries: list[JsonObject]) -> JsonObject:
    return {
        "retrieved": "2026-10-05",
        "note": "FIXTURE capture, no real aircraft value",
        "sources": [],
        "entries": entries,
    }


def _binding(game_class: str = "FIXTURE_PLANE_F", **overrides: object) -> JsonObject:
    record: JsonObject = {
        "game_class": game_class,
        "class_token": "Plane",
        "catalogue_id": "fixture_plane",
        "identity_source": "aee_air_class_table",
        "identity_evidence": "FIXTURE evidence text",
        "grade": "claimed",
    }
    record.update(overrides)
    return record


def _source(source_id: str, source_type: str) -> JsonObject:
    return {
        "source_id": source_id,
        "tier": 5,
        "type": source_type,
        "title": "FIXTURE source, not a held document",
        "identifier": "FIXTURE",
        "retrieved": "2026-10-05",
    }


def _write(
    root: Path,
    captures: dict[str, JsonObject] | None = None,
    bindings: list[JsonObject] | None = None,
    sources: list[JsonObject] | None = None,
) -> Path:
    (root / "catalogue").mkdir(parents=True, exist_ok=True)
    for name, capture in (captures or {}).items():
        (root / "catalogue" / f"{name}.json").write_text(
            json.dumps(capture), encoding="utf-8"
        )
    if bindings is not None:
        (root / "class_bindings.json").write_text(
            json.dumps(bindings), encoding="utf-8"
        )
    if sources is not None:
        (root / "sources.json").write_text(json.dumps(sources), encoding="utf-8")
    return root


class AircraftLoaderTest(unittest.TestCase):
    def test_fixed_wing_rated_power_is_derived_from_thrust(self) -> None:
        entry = _entry(
            "fixture_plane",
            values={
                "operating_weight_kg": _value(1000, "kg"),
                "thrust_kn": _value(76.0, "kN"),
                "reference_speed_ms": _value(250.0, "m/s"),
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), captures={"fixture": _capture([entry])})
            loaded = vc.load(root, profile=vc.AIRCRAFT_PROFILE)
        self.assertEqual([], loaded.errors, loaded.errors)
        record = loaded.entries[0]
        self.assertIs(True, record.runtime_ready)
        resolved = record.resolved_fields()["rated_power_w"]
        self.assertEqual("derived", resolved.grade)
        self.assertEqual(76.0 * 1000.0 * 250.0, resolved.value)
        self.assertIn(
            "rated_power_w = thrust_kn * 1000 * reference_speed_ms", resolved.state
        )

    def test_fixed_wing_without_power_resolves_absent_zero(self) -> None:
        entry = _entry(
            "fixture_plane",
            values={"operating_weight_kg": _value(1000, "kg")},
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), captures={"fixture": _capture([entry])})
            loaded = vc.load(root, profile=vc.AIRCRAFT_PROFILE)
        record = loaded.entries[0]
        self.assertIs(False, record.runtime_ready)
        resolved = record.resolved_fields()["rated_power_w"]
        self.assertEqual("absent", resolved.grade)
        self.assertEqual(0, resolved.value)

    def test_rotary_wing_runtime_set_holds_the_rotor_disc(self) -> None:
        entry = _entry(
            "fixture_rotor",
            vehicle_type="rotary_wing",
            class_token="Helicopter",
            values={
                "operating_weight_kg": _value(1000, "kg"),
                "net_power_kw": _value(500.0, "kW"),
                "rotor_diameter_m": _value(10.0, "m"),
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), captures={"fixture": _capture([entry])})
            loaded = vc.load(root, profile=vc.AIRCRAFT_PROFILE)
        record = loaded.entries[0]
        self.assertIs(True, record.runtime_ready)
        resolved = record.resolved_fields()
        self.assertEqual(500000.0, resolved["rated_power_w"].value)
        self.assertEqual(
            round(math.pi * (10.0 / 2.0) ** 2, 6),
            resolved["rotor_disc_area_m2"].value,
        )


class ClassBindingReaderTest(unittest.TestCase):
    def test_binding_loads_at_claimed_from_a_class_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(
                Path(tmp),
                captures={"fixture": _capture([_entry("fixture_plane")])},
                bindings=[_binding()],
                sources=[_source("aee_air_class_table", "class_table")],
            )
            loaded = vc.load(root, profile=vc.AIRCRAFT_PROFILE)
        self.assertEqual([], loaded.errors, loaded.errors)
        self.assertEqual(1, len(loaded.bindings))
        binding = loaded.bindings[0]
        self.assertEqual("FIXTURE_PLANE_F", binding.game_class)
        self.assertEqual("fixture_plane", binding.catalogue_id)
        self.assertEqual("claimed", binding.grade)

    def test_unknown_catalogue_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(
                Path(tmp),
                captures={"fixture": _capture([_entry("fixture_plane")])},
                bindings=[_binding(catalogue_id="ghost")],
                sources=[_source("aee_air_class_table", "class_table")],
            )
            loaded = vc.load(root, profile=vc.AIRCRAFT_PROFILE)
        self.assertEqual([], loaded.bindings)
        self.assertTrue(
            any("unknown catalogue_id ghost" in e for e in loaded.errors),
            loaded.errors,
        )

    def test_duplicate_game_class_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(
                Path(tmp),
                captures={"fixture": _capture([_entry("fixture_plane")])},
                bindings=[_binding(), _binding()],
                sources=[_source("aee_air_class_table", "class_table")],
            )
            loaded = vc.load(root, profile=vc.AIRCRAFT_PROFILE)
        self.assertEqual(1, len(loaded.bindings))
        self.assertTrue(
            any("duplicate game_class" in e for e in loaded.errors), loaded.errors
        )

    def test_unknown_identity_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(
                Path(tmp),
                captures={"fixture": _capture([_entry("fixture_plane")])},
                bindings=[_binding(identity_source="made_up")],
                sources=[_source("aee_air_class_table", "class_table")],
            )
            loaded = vc.load(root, profile=vc.AIRCRAFT_PROFILE)
        self.assertEqual([], loaded.bindings)
        self.assertTrue(
            any("not a real-world or class-table source" in e for e in loaded.errors),
            loaded.errors,
        )


if __name__ == "__main__":
    unittest.main()
