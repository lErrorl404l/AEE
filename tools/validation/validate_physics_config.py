#!/usr/bin/env python3
"""Validate the physics config-binding corpus.

``data/physics/config_bindings.json`` binds one engine config key on one
concrete game class to one held catalogue value through a named conversion.
The corpus is the input to a generated engine config override. It is the
guard for the rule that no config value exists without a held source.

A record carries eight required fields: ``game_class``, ``config_class``,
``key``, ``value``, ``unit``, ``value_source``, ``conversion`` and ``grade``.
The ``value_source`` object carries ``source_id``, ``locator`` and ``field``.

The gate checks:

  * every ``conversion`` is one the schema allowlist names;
  * every ``config_class`` and ``key`` is one the schema admits;
  * every ``game_class`` resolves in ``data/vehicle/class_bindings.json``;
  * every ``value_source.source_id`` exists in
    ``data/vehicle/sources.json`` and owns the named catalogue field;
  * every ``value`` reproduces from the named held field and conversion;
  * every ``grade`` is the held grade for a unit identity, else ``derived``;
  * no required field is empty.

Run:  python3 tools/validation/validate_physics_config.py
Exit: 0 on success, 1 on any binding error.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# A package import (tests) and a direct script run both resolve the sibling
# loader. The repository root goes on the path first.
_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

ROOT = _REPO
DEFAULT_DATA = ROOT / "data" / "physics"
DEFAULT_VEHICLE_DATA = ROOT / "data" / "vehicle"
DEFAULT_AIRCRAFT_DATA = ROOT / "data" / "aircraft"
BINDINGS_NAME = "config_bindings.json"
CLASS_BINDINGS_NAME = "class_bindings.json"
SOURCES_NAME = "sources.json"

# The eight required fields of one record, in schema order.
REQUIRED_FIELDS = (
    "game_class",
    "config_class",
    "key",
    "value",
    "unit",
    "value_source",
    "conversion",
    "grade",
)

# The three required fields of the value_source object, in schema order.
VALUE_SOURCE_FIELDS = ("source_id", "locator", "field")

# The engine config classes this schema version admits. A config class names
# identity only. It is never a value source.
CONFIG_CLASSES = frozenset({"CfgVehicles"})

# The engine config keys this schema version admits. ``maxSpeed`` is a land
# key. ``fuelCapacity`` is the aircraft fuel key, held in litres.
# ``fuelConsumptionRate`` is the aircraft structural-zero key: it disables the
# engine's own burn so the scripted burn is authoritative, and it is unitless.
# ``mass`` is the aircraft PhysX mass from the sourced operating weight, in
# kilograms. ``centerOfMass`` is the aircraft centre of gravity, in metres,
# emitted only where the engine accepts it. The remaining keys are the land
# carx/tankx/shipx physics surface from data/vehicle/SCHEMA.md section 17, each
# emitted only from a documented class identity and a documented held value.
# enginePower, peakTorque, torqueCurve and the gearbox ratios are deliberately
# absent until the in-engine probe resolves the enginePower unit.
CONFIG_KEYS = frozenset(
    {
        "maxSpeed",
        "fuelCapacity",
        "fuelConsumptionRate",
        "mass",
        "centerOfMass",
        "idleRpm",
        "redRpm",
        "maxOmega",
        "minOmega",
        "engineMOI",
        "clutchStrength",
        "switchTime",
        "changeGearType",
        "driveString",
        "neutralString",
        "reverseString",
        "moveOffGear",
        "differentialType",
        "frontRearSplit",
        "MOI",
        "maxBrakeTorque",
        "maxHandBrakeTorque",
        "maxCompression",
        "maxDroop",
        "sprungMass",
        "springStrength",
        "springDamperRate",
        "longitudinalStiffnessPerUnitGravity",
        "latStiffX",
        "latStiffY",
    }
)

# The documented config unit of each admitted key.
KEY_UNITS: dict[str, str] = {
    "maxSpeed": "km/h",
    "fuelCapacity": "L",
    "fuelConsumptionRate": "unitless",
    "mass": "kg",
    "centerOfMass": "m",
    "idleRpm": "rpm",
    "redRpm": "rpm",
    "maxOmega": "rad/s",
    "minOmega": "rad/s",
    "engineMOI": "kg m^2",
    "clutchStrength": "unitless",
    "switchTime": "s",
    "changeGearType": "text",
    "driveString": "text",
    "neutralString": "text",
    "reverseString": "text",
    "moveOffGear": "count",
    "differentialType": "text",
    "frontRearSplit": "unitless",
    "MOI": "kg m^2",
    "maxBrakeTorque": "N m",
    "maxHandBrakeTorque": "N m",
    "maxCompression": "m",
    "maxDroop": "m",
    "sprungMass": "kg",
    "springStrength": "N/m",
    "springDamperRate": "N m s/rad",
    "longitudinalStiffnessPerUnitGravity": "unitless",
    "latStiffX": "unitless",
    "latStiffY": "unitless",
}

# The grade vocabulary. A binding never carries ``absent``: a binding with no
# held source value is omitted, not recorded.
BINDING_GRADES = frozenset({"standard", "documented", "claimed", "derived"})

# A converted value is rounded to six decimal places.
CONVERSION_ROUND = 6


@dataclass(frozen=True)
class Conversion:
    """One named unit conversion from a held field to a config key."""

    source_unit: str | None
    target_unit: str | None
    factor: float
    basis: str


# The conversion allowlist. A conversion is a named formula over the held
# value. ``identity`` is the direct unit identity: source unit equals target
# unit and the value passes unchanged. The validator admits no other name.
CONVERSIONS: dict[str, Conversion] = {
    "identity": Conversion(
        source_unit=None,
        target_unit=None,
        factor=1.0,
        basis="the source unit and the target unit agree; the value is unchanged",
    ),
    "mph_to_kmh": Conversion(
        source_unit="mph",
        target_unit="km/h",
        factor=1.609344,
        basis="1 international mile = 1.609344 km (ISO 80000-3)",
    ),
    "mps_to_kmh": Conversion(
        source_unit="m/s",
        target_unit="km/h",
        factor=3.6,
        basis="1 m/s = 3.6 km/h (SI derived unit)",
    ),
    "structural_zero": Conversion(
        source_unit=None,
        target_unit=None,
        factor=0.0,
        basis=(
            "the key is a structural zero: the engine's own burn is disabled "
            "so the scripted burn from the sourced systems-row rate is "
            "authoritative and the two never double-count"
        ),
    ),
}


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _text(value: object) -> str | None:
    """Return a non-empty string, or None. An empty field is not a value."""
    if isinstance(value, str) and value.strip():
        return value
    return None


def _absent(value: object) -> bool:
    """True when a required field carries no value. A numeric zero is present."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def _number(value: object) -> float | None:
    """Return a number, or None. A boolean is not a number here."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def load_bindings(path: Path) -> list[object]:
    """Read the binding file. Raise ValueError when it is not an array."""
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"{path}: config bindings must be a top-level array")
    return list(loaded)


def class_binding_map(vehicle_dir: Path) -> dict[str, str]:
    """Return the concrete class layer keyed by game class."""
    path = vehicle_dir / CLASS_BINDINGS_NAME
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"{path}: class bindings must be a top-level array")
    mapping: dict[str, str] = {}
    for raw in loaded:
        record = _mapping(raw)
        if record is None:
            continue
        game_class = _text(record.get("game_class"))
        catalogue_id = _text(record.get("catalogue_id"))
        if game_class is not None and catalogue_id is not None:
            mapping[game_class] = catalogue_id
    return mapping


def sources_by_id(vehicle_dir: Path) -> dict[str, dict[str, object]]:
    """Return the source registry keyed by source_id."""
    path = vehicle_dir / SOURCES_NAME
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"{path}: the source registry must be a top-level array")
    registry: dict[str, dict[str, object]] = {}
    for raw in loaded:
        source = _mapping(raw)
        source_id = _text(source.get("source_id")) if source is not None else None
        if source is not None and source_id is not None:
            registry[source_id] = source
    return registry


def catalogue_by_id(
    data_dir: Path, *, profile: catalogue.Profile = catalogue.GROUND_PROFILE
) -> dict[str, catalogue.CatalogueEntry]:
    """Return the catalogue corpus keyed by catalogue_id.

    ``profile`` selects the family contract. It defaults to the ground profile,
    so every existing caller is unchanged. The aircraft corpus loads with the
    aircraft profile.
    """
    load = catalogue.load(data_dir, profile=profile)
    return {entry.catalogue_id: entry for entry in load.entries}


def _check_conversion(
    where: str,
    conversion: str | None,
    unit: str | None,
    held_unit: str | None,
    errors: list[str],
) -> Conversion | None:
    """Check the conversion name and its unit pair. Return the conversion."""
    conv = CONVERSIONS.get(conversion) if conversion is not None else None
    if conversion is not None and conv is None:
        errors.append(
            f"{where}: unknown conversion {conversion}; allowed: {sorted(CONVERSIONS)}"
        )
        return None
    if conv is None or unit is None:
        return conv
    if conversion == "structural_zero":
        # The key is a structural zero, not a unit identity. Its value is
        # fixed at zero by the conversion factor, so no held unit is compared.
        return conv
    if conv.source_unit is None:
        # A direct unit identity: the source unit equals the target unit.
        if held_unit is not None and held_unit != unit:
            errors.append(
                f"{where}: conversion {conversion} needs one unit; the held "
                f"unit is {held_unit} and the config unit is {unit}"
            )
    else:
        if held_unit is not None and held_unit != conv.source_unit:
            errors.append(
                f"{where}: conversion {conversion} needs a held unit "
                f"{conv.source_unit}, got {held_unit}"
            )
        if unit != conv.target_unit:
            errors.append(
                f"{where}: conversion {conversion} produces unit "
                f"{conv.target_unit}, got {unit}"
            )
    return conv


def _check_grade(
    where: str,
    grade: str | None,
    conversion: str | None,
    held_grade: str | None,
    errors: list[str],
) -> None:
    """Check the grade rule: identity keeps the held grade, else derived."""
    if grade is None or conversion is None:
        return
    if conversion == "identity":
        if held_grade is not None and grade != held_grade:
            errors.append(
                f"{where}: a unit identity keeps the held grade {held_grade}, "
                f"got {grade}"
            )
    elif grade != "derived":
        errors.append(
            f"{where}: a named conversion must be graded derived, got {grade}"
        )


def _check_value(
    where: str,
    record: dict[str, object],
    held: dict[str, object],
    field: str,
    conversion: str,
    conv: Conversion,
    errors: list[str],
) -> None:
    """Reproduce the value from the held field and the conversion."""
    held_number = _number(held.get("value"))
    value_number = _number(record.get("value"))
    if held_number is None:
        errors.append(f"{where}: the {field} value is not numeric")
        return
    if value_number is None:
        errors.append(f"{where}: value must be a number")
        return
    expected = round(held_number * conv.factor, CONVERSION_ROUND)
    if value_number != expected:
        errors.append(
            f"{where}: value {record.get('value')} does not reproduce from "
            f"{field} ({held.get('value')}) by conversion {conversion}; "
            f"expected {expected}"
        )


def validate_bindings(
    records: Sequence[object],
    catalogue_ids: dict[str, catalogue.CatalogueEntry],
    class_bindings: dict[str, str],
    sources: dict[str, dict[str, object]],
) -> list[str]:
    """Validate the config bindings. Return every error.

    A binding needs a concrete game class, a held catalogue field, its source
    and a value that reproduces from the field by the named conversion. An
    unknown conversion, an unresolved class, an unknown source and an
    irreproducible value are errors.
    """
    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(records):
        record = _mapping(raw)
        if record is None:
            errors.append(f"config binding[{index}]: must be an object")
            continue

        game_class = _text(record.get("game_class"))
        where = f"config binding {game_class or f'[{index}]'}"

        missing = [field for field in REQUIRED_FIELDS if _absent(record.get(field))]
        if missing:
            errors.append(
                f"{where}: required field is empty or missing: {', '.join(missing)}"
            )

        config_class = _text(record.get("config_class"))
        if config_class is not None and config_class not in CONFIG_CLASSES:
            errors.append(
                f"{where}: config_class must be one of {sorted(CONFIG_CLASSES)}"
            )

        key = _text(record.get("key"))
        if key is not None and key not in CONFIG_KEYS:
            errors.append(f"{where}: key must be one of {sorted(CONFIG_KEYS)}")

        # One class carries one value for one key. A repeat is an error.
        if game_class is not None and config_class is not None and key is not None:
            identity = (game_class, config_class, key)
            if identity in seen:
                errors.append(
                    f"{where}: duplicate binding for {config_class}.{key}; one "
                    "class carries one value for one key"
                )
            seen.add(identity)

        unit = _text(record.get("unit"))
        if key is not None and key in KEY_UNITS and unit is not None:
            if unit != KEY_UNITS[key]:
                errors.append(
                    f"{where}: key {key} is documented in {KEY_UNITS[key]}, "
                    f"got unit {unit}"
                )

        conversion = _text(record.get("conversion"))
        grade = record.get("grade")
        if not (isinstance(grade, str) and grade in BINDING_GRADES):
            errors.append(f"{where}: grade must be one of {sorted(BINDING_GRADES)}")

        source = _mapping(record.get("value_source"))
        if source is None:
            errors.append(f"{where}: value_source must be an object")
            continue

        source_missing = [
            field for field in VALUE_SOURCE_FIELDS if _absent(source.get(field))
        ]
        if source_missing:
            errors.append(
                f"{where}: value_source field is empty or missing: "
                f"{', '.join(source_missing)}"
            )

        catalogue_id = class_bindings.get(game_class) if game_class else None
        if game_class is not None and catalogue_id is None:
            errors.append(
                f"{where}: unknown game_class; no record in {CLASS_BINDINGS_NAME}"
            )

        entry = catalogue_ids.get(catalogue_id) if catalogue_id else None
        field = _text(source.get("field"))
        held = (
            catalogue.held_value(entry.values, field)
            if entry is not None and field is not None
            else None
        )
        if entry is not None and field is not None and held is None:
            errors.append(
                f"{where}: catalogue entry {catalogue_id} holds no value for "
                f"field {field}"
            )

        held_unit = _text(held.get("unit")) if held is not None else None
        held_grade = _text(held.get("grade")) if held is not None else None
        conv = _check_conversion(where, conversion, unit, held_unit, errors)

        source_id = _text(source.get("source_id"))
        if source_id is not None and source_id not in sources:
            errors.append(f"{where}: unknown source_id {source_id}")
        if held is not None and source_id is not None:
            held_source = _text(held.get("source"))
            if held_source is not None and held_source != source_id:
                errors.append(
                    f"{where}: source_id {source_id} does not own the {field} "
                    f"value; the held source is {held_source}"
                )

        if conv is not None and held is not None and field is not None:
            _check_value(where, record, held, field, conversion or "", conv, errors)

        _check_grade(
            where,
            grade if isinstance(grade, str) else None,
            conversion,
            held_grade,
            errors,
        )
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    paths = list(sys.argv[1:] if argv is None else argv)
    data_dir = DEFAULT_DATA
    vehicle_dir = DEFAULT_VEHICLE_DATA
    aircraft_dir = DEFAULT_AIRCRAFT_DATA
    index = 0
    while index < len(paths):
        flag = paths[index]
        if flag in ("--data-dir", "--vehicle-dir", "--aircraft-dir") and (
            index + 1 < len(paths)
        ):
            if flag == "--data-dir":
                data_dir = Path(paths[index + 1])
            elif flag == "--vehicle-dir":
                vehicle_dir = Path(paths[index + 1])
            else:
                aircraft_dir = Path(paths[index + 1])
            index += 2
            continue
        print(
            "usage: validate_physics_config.py "
            "[--data-dir PATH] [--vehicle-dir PATH] [--aircraft-dir PATH]"
        )
        return 2

    path = data_dir / BINDINGS_NAME
    try:
        records = load_bindings(path)
        catalogue_ids = catalogue_by_id(vehicle_dir)
        class_bindings = class_binding_map(vehicle_dir)
        sources = sources_by_id(vehicle_dir)
        # The aircraft family shares the config-key contract. Merge its class
        # bindings, sources and catalogue so a future aircraft fuelCapacity
        # record is not rejected as an unknown game_class.
        if aircraft_dir.is_dir():
            catalogue_ids.update(
                catalogue_by_id(aircraft_dir, profile=catalogue.AIRCRAFT_PROFILE)
            )
            class_bindings.update(class_binding_map(aircraft_dir))
            sources.update(sources_by_id(aircraft_dir))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"physics config bindings: FAIL\n  cannot read the corpus: {exc}")
        return 1

    errors = validate_bindings(records, catalogue_ids, class_bindings, sources)
    if errors:
        print("physics config bindings: FAIL")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"physics config bindings: {len(records)} bindings -> {path} (valid)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
