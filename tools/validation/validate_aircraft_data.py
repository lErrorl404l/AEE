#!/usr/bin/env python3
"""Gate for the aircraft research corpus.

The contract: a real aircraft value enters the corpus only with a unit, a
source, a locator, a state and a grade. An engine source is identity
evidence. It never carries a numeric or categorical value. A runtime-ready
record must hold every runtime input for its aircraft type. Two sources are
never averaged.

The validator reads the source registry, the held source bytes, the capture
files under ``records/`` and ``catalogue/``, the class map, the class
bindings and the conflicts. It applies the tier and grade coupling, the
type-aware runtime sets and the held-source digest check. A class binding
needs a real-world or class-table source and a unique game class. A value
from an unheld source is a lead: it carries grade claimed, its state starts
with the marker UNSOURCED and it never fills a runtime-required field.
It reads no network resource.

Run:  python3 tools/validation/validate_aircraft_data.py
      python3 tools/validation/validate_aircraft_data.py --data-dir PATH
      python3 tools/validation/validate_aircraft_data.py --self-check
Exit: 0 when the corpus obeys the contract, 1 when it does not.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

# A package import (tests) and a direct script run both resolve the sibling
# source-holding tool. The repository root goes on the path first.
_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation import vehicle_catalogue  # noqa: E402
from tools.validation.fetch_vehicle_sources import (  # noqa: E402
    held_filename,
    sha256_file,
)

DEFAULT_DATA = Path(__file__).parents[2] / "data" / "aircraft"

# One exact grade string per schema section 6.
GRADES = frozenset({"standard", "documented", "claimed", "derived"})

# Real-world evidence types, then the three engine types.
REAL_SOURCE_TYPES = frozenset(
    {
        "standard",
        "manual",
        "poh",
        "tcds",
        "measurement",
        "manufacturer",
        "compilation",
    }
)
ENGINE_SOURCE_TYPES = frozenset({"engine_geometry", "engine_config", "class_table"})
SOURCE_TYPES = REAL_SOURCE_TYPES | ENGINE_SOURCE_TYPES

# An engine type is identity evidence only. It never carries a value.
IDENTITY_ONLY_TYPES = frozenset({"engine_config", "class_table"})

# The unit vocabulary per schema section 9. The aircraft document adds W, kN,
# m/s and m^2 to the inherited vehicle vocabulary.
UNITS = frozenset(
    {
        "kg",
        "mm",
        "kPa",
        "kW",
        "hp",
        "L",
        "N m",
        "deg",
        "km/h",
        "km",
        "m",
        "count",
        "ratio",
        "enum",
        "text",
        "W",
        "kN",
        "m/s",
        "m^2",
    }
)
NON_NUMERIC_UNITS = frozenset({"enum", "text"})

# The fixed unit of every aircraft value field per schema section 3.
FIELD_UNITS: dict[str, str] = {
    # The four calculation inputs.
    "operating_weight_kg": "kg",
    "rated_power_w": "W",
    "drag_area_m2": "m^2",
    "rotor_disc_area_m2": "m^2",
    # The held derivation inputs.
    "empty_weight_kg": "kg",
    "max_takeoff_weight_kg": "kg",
    "net_power_kw": "kW",
    "published_power_hp": "hp",
    "thrust_kn": "kN",
    "reference_speed_ms": "m/s",
    "rotor_diameter_m": "m",
    "drag_coefficient": "ratio",
    "wing_area_m2": "m^2",
    # The reference-only airframe fields.
    "length_m": "m",
    "height_m": "m",
    "wing_span_m": "m",
    "max_speed_kmh": "km/h",
    "cruise_speed_kmh": "km/h",
    "range_km": "km",
    "service_ceiling_m": "m",
    "rate_of_climb_ms": "m/s",
    "payload_kg": "kg",
    "crew": "count",
    "capacity": "count",
    "engine_model": "text",
    "engine_count": "count",
    "first_flight": "text",
    "country": "text",
    "role": "enum",
    "propulsion": "enum",
}

# The runtime-required inputs per aircraft type. The shared loader owns the
# sets so the generator, the coverage guard and the validator resolve the same
# fields in the same order.
REQUIRED_RUNTIME_BY_TYPE: Mapping[str, tuple[str, ...]] = (
    vehicle_catalogue.AIRCRAFT_PROFILE.runtime_by_type
)

# The fixed-wing set stays under the former name for older callers.
REQUIRED_RUNTIME = REQUIRED_RUNTIME_BY_TYPE["fixed_wing"]

IDENTITY_FIELDS = (
    "variant_id",
    "game_class",
    "class_token",
    "identity_source",
    "maker",
    "model",
    "variant",
    "country",
    "era",
    "vehicle_type",
)

# The catalogue entry fields per schema section 6. ``vehicle_type`` and
# ``class_token`` are checked separately because one is an enum and the
# other may be empty.
CATALOGUE_IDENTITY_FIELDS = (
    "catalogue_id",
    "canonical_name",
    "maker",
    "model",
    "variant",
    "variant_id",
    "country",
    "era",
)

# The class-map and class-binding grade set per schema section 7.
CLASS_MAP_GRADES = frozenset({"documented", "claimed"})

# The aircraft type enum, read from the shared loader profile.
VEHICLE_TYPES = vehicle_catalogue.AIRCRAFT_PROFILE.vehicle_types

# The closed vocabularies the runtime projection depends on.
ENUM_VALUES: dict[str, frozenset[str]] = {
    "propulsion": frozenset(
        {
            "turbofan",
            "turbojet",
            "turboprop",
            "piston_prop",
            "turboshaft",
            "piston_rotor",
        }
    ),
    "role": frozenset(
        {
            "multirole",
            "interceptor",
            "attack",
            "bomber",
            "transport",
            "trainer",
            "recon",
            "utility",
            "gunship",
            "liaison",
        }
    ),
}

# A value from a source with ``primary_held: false`` must name its lead state.
UNSOURCED_MARKER = "UNSOURCED"


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _sequence(value: object) -> list[object] | None:
    if not isinstance(value, list):
        return None
    return list(value)


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _read_json(path: Path, errors: list[str]) -> object | None:
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: cannot parse JSON: {exc}")
        return None
    return loaded


def _is_fixtures_path(path: Path) -> bool:
    """True when the resolved path names the negative-test fixtures directory."""
    return any(part == "fixtures" for part in path.resolve().parts)


def validate_sources(
    sources: Sequence[object], errors: list[str]
) -> dict[str, dict[str, object]]:
    """Check the registry shape. Return the entries keyed by source_id."""
    by_id: dict[str, dict[str, object]] = {}
    for raw in sources:
        entry = _mapping(raw)
        if entry is None:
            errors.append("source entry: must be an object")
            continue
        sid = _text(entry.get("source_id"))
        if sid is None:
            errors.append("source entry: source_id is required")
            continue
        if sid in by_id:
            errors.append(f"source {sid}: duplicate source_id")
            continue
        by_id[sid] = entry

        tier = entry.get("tier")
        if (
            isinstance(tier, bool)
            or not isinstance(tier, int)
            or tier not in range(1, 6)
        ):
            errors.append(f"source {sid}: tier must be 1 to 5")
        source_type = entry.get("type")
        if not isinstance(source_type, str) or source_type not in SOURCE_TYPES:
            errors.append(f"source {sid}: type must be one of {sorted(SOURCE_TYPES)}")
        for field in ("title", "identifier", "retrieved"):
            if _text(entry.get(field)) is None:
                errors.append(f"source {sid}: {field} is required")
        if "primary_held" in entry and not isinstance(entry.get("primary_held"), bool):
            errors.append(f"source {sid}: primary_held must be true or false")
    return by_id


def validate_held_sources(sources: Sequence[object], sources_dir: Path) -> list[str]:
    """Verify the held bytes that are present; absent bytes are not an error.

    The documents are not vendored (they are gitignored, the same rule as the
    vehicle sources), so a fresh clone holds the register but not the bytes.  A
    held source whose file is absent is skipped here.  The explicit byte check
    is the fetch tool's ``--verify`` mode.
    """
    errors: list[str] = []
    for raw in sources:
        if not isinstance(raw, Mapping) or raw.get("primary_held") is not True:
            continue
        source_id = str(raw.get("source_id", "?"))
        path = sources_dir / held_filename(raw)
        if not path.exists():
            continue
        digest = raw.get("sha256")
        if not isinstance(digest, str) or not digest:
            errors.append(f"{source_id}: primary_held is true but sha256 is empty")
            continue
        actual = sha256_file(path)
        if actual != digest:
            errors.append(
                f"{source_id}: digest mismatch: recorded {digest}, on disk {actual}"
            )
    return errors


def _check_grade_coupling(
    where: str,
    field: str,
    grade: object,
    entry: dict[str, object],
    source: dict[str, object],
    errors: list[str],
) -> None:
    source_type = source.get("type")
    tier = source.get("tier")
    primary_held = source.get("primary_held") is True
    if grade == "standard":
        if not (tier == 1 and source_type == "standard" and primary_held):
            errors.append(
                f"{where}: grade standard needs a held tier 1 standard source"
            )
    elif grade == "documented":
        manual_ok = (
            tier in (2, 3) and source_type in ("manual", "measurement") and primary_held
        )
        if not manual_ok:
            errors.append(
                f"{where}: grade documented needs a held tier 2 or 3 manual or measurement source"
            )
    elif grade == "claimed":
        maker_ok = tier == 4 and source_type == "manufacturer"
        compilation_ok = tier == 5 and source_type == "compilation"
        if not (maker_ok or compilation_ok):
            errors.append(
                f"{where}: grade claimed needs a tier 4 manufacturer or a tier 5 compilation source"
            )
    elif grade == "derived":
        marker = vehicle_catalogue.AIRCRAFT_PROFILE.derivation_markers.get(field)
        state = _text(entry.get("state")) or ""
        if marker is None or marker not in state:
            errors.append(
                f"{where}: grade derived needs the named derivation marker in the state text"
            )


def validate_value(
    record_id: str,
    field: str,
    raw_entry: object,
    by_id: dict[str, dict[str, object]],
    errors: list[str],
    kind: str = "record",
) -> None:
    where = f"{kind} {record_id} field {field}"
    entry = _mapping(raw_entry)
    if entry is None:
        errors.append(f"{where}: value must be an object")
        return

    field_unit = FIELD_UNITS.get(field)
    if field_unit is None:
        errors.append(f"{where}: unknown value field")

    value = entry.get("value")
    if value is None or value == "":
        errors.append(f"{where}: value is required")

    unit = entry.get("unit")
    if not isinstance(unit, str) or not unit:
        errors.append(f"{where}: unit is required")
    elif unit not in UNITS:
        errors.append(f"{where}: unit {unit} is not in the vocabulary")
    elif field_unit is not None and unit != field_unit:
        errors.append(
            f"{where}: unit {unit} does not match the field unit {field_unit}"
        )

    source_id = _text(entry.get("source"))
    source = by_id.get(source_id) if source_id is not None else None
    if source_id is None:
        errors.append(f"{where}: source is required")
    elif source is None:
        errors.append(f"{where}: unknown source {source_id}")

    if _text(entry.get("locator")) is None:
        errors.append(f"{where}: locator is required")
    state = _text(entry.get("state"))
    if state is None:
        errors.append(f"{where}: state is required")

    grade = entry.get("grade")
    grade_ok = isinstance(grade, str) and grade in GRADES
    if not grade_ok:
        errors.append(f"{where}: grade must be one of {sorted(GRADES)}")

    if field_unit is not None and value is not None and value != "":
        if field_unit in NON_NUMERIC_UNITS:
            if not isinstance(value, str):
                errors.append(f"{where}: value must be a word for unit {field_unit}")
        elif not _is_number(value):
            errors.append(f"{where}: value must be a number for unit {field_unit}")

    if (
        field in ENUM_VALUES
        and isinstance(value, str)
        and value not in ENUM_VALUES[field]
    ):
        errors.append(
            f"{where}: value {value} is not one of {sorted(ENUM_VALUES[field])}"
        )

    if source is None:
        return

    source_type = source.get("type")
    if source_type in IDENTITY_ONLY_TYPES:
        errors.append(
            f"{where}: source {source_id} type {source_type} is forbidden for a value"
        )
        return

    if source_type == "engine_geometry":
        errors.append(
            f"{where}: source {source_id} type engine_geometry is identity or geometry evidence and never an aircraft value"
        )

    if (
        source.get("primary_held") is False
        and state is not None
        and not state.startswith(UNSOURCED_MARKER)
    ):
        errors.append(
            f"{where}: a source with primary_held false needs the state to start with {UNSOURCED_MARKER}"
        )

    if not grade_ok:
        return

    _check_grade_coupling(where, field, grade, entry, source, errors)

    tier = source.get("tier")
    if source_type in REAL_SOURCE_TYPES and tier == 5 and grade != "claimed":
        errors.append(f"{where}: tier 5 source needs grade claimed")


def _check_runtime_required(
    record_id: str,
    vehicle_type: object,
    values: dict[str, object],
    errors: list[str],
    kind: str = "record",
) -> None:
    """Report every required field a runtime-ready record fails to resolve.

    The check runs over the resolved fields, not the raw keys, so a runtime
    field that a named derivation supplies (operating weight from empty
    weight, rated power from thrust) counts as held.
    """
    resolved = vehicle_catalogue.resolve_fields(
        str(vehicle_type), values, vehicle_catalogue.AIRCRAFT_PROFILE
    )
    for field, entry in resolved.items():
        if entry.grade == "absent":
            errors.append(
                f"{kind} {record_id}: runtime_ready record misses required field {field}"
            )


def _reject_unsourced_runtime(
    record_id: str,
    vehicle_type: object,
    values: dict[str, object],
    by_id: dict[str, dict[str, object]],
    errors: list[str],
    kind: str = "record",
) -> None:
    """A runtime-required field never resolves from an unheld source."""
    if not isinstance(vehicle_type, str):
        return
    resolved = vehicle_catalogue.resolve_fields(
        vehicle_type, values, vehicle_catalogue.AIRCRAFT_PROFILE
    )
    for name, field in resolved.items():
        if field.grade == "absent" or not field.source:
            continue
        source = by_id.get(field.source)
        if source is not None and source.get("primary_held") is False:
            errors.append(
                f"{kind} {record_id}: runtime-required field {name} resolves from the unheld source {field.source}; an UNSOURCED value never fills a runtime field"
            )


def validate_record(
    raw: object,
    by_id: dict[str, dict[str, object]],
    seen: set[str],
    errors: list[str],
) -> None:
    record = _mapping(raw)
    if record is None:
        errors.append("record entry: must be an object")
        return

    record_id = _text(record.get("variant_id"))
    if record_id is None:
        errors.append("record entry: variant_id is required")
        record_id = "<none>"
    elif record_id in seen:
        errors.append(f"record {record_id}: duplicate variant_id")
    seen.add(record_id)

    for field in IDENTITY_FIELDS:
        if _text(record.get(field)) is None:
            errors.append(f"record {record_id}: identity field {field} is required")

    vehicle_type = record.get("vehicle_type")
    if not isinstance(vehicle_type, str) or vehicle_type not in VEHICLE_TYPES:
        errors.append(
            f"record {record_id}: vehicle_type must be one of {sorted(VEHICLE_TYPES)}"
        )

    identity_source = _text(record.get("identity_source"))
    if identity_source is not None and identity_source not in by_id:
        errors.append(f"record {record_id}: unknown identity_source {identity_source}")

    runtime_ready = record.get("runtime_ready")
    if not isinstance(runtime_ready, bool):
        errors.append(f"record {record_id}: runtime_ready must be true or false")
        runtime_ready = False

    values = _mapping(record.get("values"))
    if values is None:
        errors.append(f"record {record_id}: values must be an object")
        values = {}

    for field, raw_entry in values.items():
        validate_value(record_id, field, raw_entry, by_id, errors)

    _reject_unsourced_runtime(record_id, vehicle_type, values, by_id, errors)

    if runtime_ready:
        _check_runtime_required(record_id, vehicle_type, values, errors)


def validate_catalogue(
    entries: Sequence[object], by_id: dict[str, dict[str, object]]
) -> list[str]:
    """Validate the real-world catalogue entries. Return the errors."""
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_variants: set[str] = set()
    for raw in entries:
        entry = _mapping(raw)
        if entry is None:
            errors.append("catalogue entry: must be an object")
            continue

        cid = _text(entry.get("catalogue_id"))
        if cid is None:
            errors.append("catalogue entry: catalogue_id is required")
            cid = "<none>"
        elif cid in seen_ids:
            errors.append(f"catalogue {cid}: duplicate catalogue_id")
        seen_ids.add(cid)

        for field in CATALOGUE_IDENTITY_FIELDS:
            if _text(entry.get(field)) is None:
                errors.append(f"catalogue {cid}: identity field {field} is required")

        variant_id = _text(entry.get("variant_id"))
        if variant_id is not None:
            if variant_id in seen_variants:
                errors.append(f"catalogue {cid}: duplicate variant_id {variant_id}")
            seen_variants.add(variant_id)

        vehicle_type = entry.get("vehicle_type")
        if not isinstance(vehicle_type, str) or vehicle_type not in VEHICLE_TYPES:
            errors.append(
                f"catalogue {cid}: vehicle_type must be one of {sorted(VEHICLE_TYPES)}"
            )

        if not isinstance(entry.get("class_token"), str):
            errors.append(f"catalogue {cid}: class_token must be a string")

        runtime_ready = entry.get("runtime_ready")
        if not isinstance(runtime_ready, bool):
            errors.append(f"catalogue {cid}: runtime_ready must be true or false")
            runtime_ready = False

        for list_field in ("aliases", "keywords"):
            items = _sequence(entry.get(list_field))
            if items is None:
                errors.append(f"catalogue {cid}: {list_field} must be an array")
                continue
            for item in items:
                if not isinstance(item, str) or not item:
                    errors.append(
                        f"catalogue {cid}: {list_field} holds a non-string entry"
                    )
                elif item != item.lower():
                    errors.append(
                        f"catalogue {cid}: {list_field} entry {item} must be lowercase"
                    )

        values = _mapping(entry.get("values"))
        if values is None:
            errors.append(f"catalogue {cid}: values must be an object")
            values = {}

        for field, raw_entry in values.items():
            validate_value(cid, field, raw_entry, by_id, errors, kind="catalogue")

        _reject_unsourced_runtime(
            cid, vehicle_type, values, by_id, errors, kind="catalogue"
        )

        # A lead may resolve no runtime field (plan tasks 5 and 6): an absent
        # field is a labelled zero. A non-lead must hold every runtime field.
        vehicle_kind = vehicle_type if isinstance(vehicle_type, str) else ""
        resolved = vehicle_catalogue.resolve_fields(
            vehicle_kind, values, vehicle_catalogue.AIRCRAFT_PROFILE
        )
        if runtime_ready:
            _check_runtime_required(cid, vehicle_type, values, errors, "catalogue")
        for name, field in resolved.items():
            marker = vehicle_catalogue.AIRCRAFT_PROFILE.derivation_markers.get(name)
            if field.grade == "derived" and marker and marker not in field.state:
                errors.append(
                    f"catalogue {cid}: derived {name} must name its formula in the state text"
                )
    return errors


def validate_class_map(
    records: Sequence[object],
    catalogue_ids: set[str],
    by_id: dict[str, dict[str, object]],
) -> list[str]:
    """Validate the class-to-catalogue map. Return the errors.

    A mapping needs a real-world mapping source and its evidence. A
    token-only category guess never creates a mapping.
    """
    errors: list[str] = []
    seen_classes: set[str] = set()
    for raw in records:
        record = _mapping(raw)
        if record is None:
            errors.append("class map entry: must be an object")
            continue

        game_class = _text(record.get("game_class"))
        where = f"class map {game_class or '<none>'}"
        if game_class is None:
            errors.append(
                f"{where}: game_class is required; a category guess cannot create a class map"
            )
        elif game_class in seen_classes:
            errors.append(
                f"{where}: duplicate game_class; one game class maps to one catalogue entry"
            )
        seen_classes.add(game_class or "<none>")

        if not isinstance(record.get("class_token"), str):
            errors.append(f"{where}: class_token must be a string")

        cid = _text(record.get("catalogue_id"))
        if cid is None:
            errors.append(f"{where}: catalogue_id is required")
        elif cid not in catalogue_ids:
            errors.append(f"{where}: unknown catalogue_id {cid}")

        evidence = _text(record.get("identity_evidence"))
        if evidence is None:
            errors.append(
                f"{where}: identity_evidence is required; name the words or locator that link the class to the entry"
            )

        grade = record.get("grade")
        grade_ok = isinstance(grade, str) and grade in CLASS_MAP_GRADES
        if not grade_ok:
            errors.append(f"{where}: grade must be one of {sorted(CLASS_MAP_GRADES)}")

        source_id = _text(record.get("identity_source"))
        source = by_id.get(source_id) if source_id is not None else None
        if source_id is None:
            errors.append(
                f"{where}: identity_source is required; a category guess cannot create a class map"
            )
        elif source is None:
            errors.append(f"{where}: unknown identity_source {source_id}")

        if not grade_ok:
            continue

        source_type = source.get("type") if source is not None else None
        tier = source.get("tier") if source is not None else None
        if source_type in vehicle_catalogue.ENGINE_MAPPING_SOURCE_TYPES:
            # A class table or an engine config binds a class only at grade
            # claimed, and the evidence must name the concrete token or kind.
            if grade != "claimed":
                errors.append(
                    f"{where}: identity_source {source_id} is engine evidence; a category guess cannot create a class map"
                )
            else:
                token = record.get("class_token")
                if not isinstance(token, str) or not token:
                    errors.append(
                        f"{where}: a claimed engine mapping must carry the class token it binds"
                    )
                elif evidence is None or token not in evidence:
                    errors.append(
                        f"{where}: a claimed engine mapping must name the concrete token {token} in the identity evidence"
                    )
        elif source_type in REAL_SOURCE_TYPES:
            if grade == "documented" and tier not in (2, 3):
                errors.append(
                    f"{where}: grade documented needs a tier 2 or tier 3 real-world source"
                )
            elif grade == "claimed" and tier not in (4, 5):
                errors.append(
                    f"{where}: grade claimed needs a tier 4 or tier 5 real-world source"
                )
        elif source is not None:
            errors.append(
                f"{where}: identity_source {source_id} is engine evidence; a category guess cannot create a class map"
            )
    return errors


def validate_class_bindings(
    records: Sequence[object],
    catalogue_ids: set[str],
    by_id: dict[str, dict[str, object]],
) -> list[str]:
    """Validate the concrete class bindings. Return the errors.

    A binding is finer than a class map. It needs a real-world or class-table
    source, its evidence and a unique concrete game class.
    """
    errors: list[str] = []
    seen_classes: set[str] = set()
    for raw in records:
        record = _mapping(raw)
        if record is None:
            errors.append("class binding entry: must be an object")
            continue

        game_class = _text(record.get("game_class"))
        where = f"class binding {game_class or '<none>'}"
        if game_class is None:
            errors.append(f"{where}: game_class is required")
        elif game_class in seen_classes:
            errors.append(
                f"{where}: duplicate game_class; one game class binds to one catalogue entry"
            )
        seen_classes.add(game_class or "<none>")

        if not isinstance(record.get("class_token"), str):
            errors.append(f"{where}: class_token must be a string")

        cid = _text(record.get("catalogue_id"))
        if cid is None:
            errors.append(f"{where}: catalogue_id is required")
        elif cid not in catalogue_ids:
            errors.append(f"{where}: unknown catalogue_id {cid}")

        evidence = _text(record.get("identity_evidence"))
        if evidence is None:
            errors.append(f"{where}: identity_evidence is required")

        grade = record.get("grade")
        grade_ok = isinstance(grade, str) and grade in CLASS_MAP_GRADES
        if not grade_ok:
            errors.append(f"{where}: grade must be one of {sorted(CLASS_MAP_GRADES)}")

        source_id = _text(record.get("identity_source"))
        source = by_id.get(source_id) if source_id is not None else None
        if source_id is None:
            errors.append(
                f"{where}: identity_source is required; a binding needs a real-world or class-table source"
            )
        elif source is None:
            errors.append(f"{where}: unknown identity_source {source_id}")

        if not grade_ok:
            continue

        source_type = source.get("type") if source is not None else None
        tier = source.get("tier") if source is not None else None
        if source_type in vehicle_catalogue.ENGINE_MAPPING_SOURCE_TYPES:
            if grade != "claimed":
                errors.append(
                    f"{where}: identity_source {source_id} is class-table evidence; a binding needs grade claimed"
                )
            else:
                token = record.get("class_token")
                if not isinstance(token, str) or not token:
                    errors.append(
                        f"{where}: a claimed class-table binding must carry the class token it binds"
                    )
                elif evidence is None or token not in evidence:
                    errors.append(
                        f"{where}: a claimed class-table binding must name the concrete token {token} in the identity evidence"
                    )
        elif source_type in REAL_SOURCE_TYPES:
            if grade == "documented" and tier not in (2, 3):
                errors.append(
                    f"{where}: grade documented needs a tier 2 or tier 3 real-world source"
                )
            elif grade == "claimed" and tier not in (4, 5):
                errors.append(
                    f"{where}: grade claimed needs a tier 4 or tier 5 real-world source"
                )
        elif source is not None:
            errors.append(
                f"{where}: identity_source {source_id} is not a real-world or class-table source"
            )
    return errors


def validate_conflict(
    raw: object, by_id: dict[str, dict[str, object]], errors: list[str]
) -> None:
    conflict = _mapping(raw)
    if conflict is None:
        errors.append("conflict entry: must be an object")
        return

    entity = _text(conflict.get("entity")) or "<none>"
    field = _text(conflict.get("field"))
    where = f"conflict {entity} field {field or '<none>'}"

    if field is None:
        errors.append(f"{where}: field is required")
    for key in ("value_a", "value_b"):
        value = conflict.get(key)
        if value is None or value == "":
            errors.append(f"{where}: {key} is required, keep both values")
    for key in ("source_a", "source_b"):
        sid = _text(conflict.get(key))
        if sid is None:
            errors.append(f"{where}: {key} is required")
        elif sid not in by_id:
            errors.append(f"{where}: unknown source {sid}")
    for key in ("resolution", "rule_applied", "date"):
        if _text(conflict.get(key)) is None:
            errors.append(f"{where}: {key} is required")

    # The resolution states how the record keeps both values. An averaged
    # resolution is an error. The rule text may name the ban on averaging.
    resolution = _text(conflict.get("resolution")) or ""
    if "averag" in resolution.lower():
        errors.append(f"{where}: an averaged conflict is forbidden, keep both values")


def validate_corpus(sources: object, records: object, conflicts: object) -> list[str]:
    """Validate a whole corpus of records. Return the list of errors."""
    errors: list[str] = []

    source_list = _sequence(sources)
    if source_list is None:
        errors.append("sources: must be an array")
        source_list = []
    by_id = validate_sources(source_list, errors)

    record_list = _sequence(records)
    if record_list is None:
        errors.append("records: must be an array")
        record_list = []
    seen: set[str] = set()
    for raw in record_list:
        validate_record(raw, by_id, seen, errors)

    conflict_list = _sequence(conflicts)
    if conflict_list is None:
        errors.append("conflicts: must be an array")
        conflict_list = []
    for raw in conflict_list:
        validate_conflict(raw, by_id, errors)
    return errors


def _check_capture_sources(
    path: Path, capture: dict[str, object], errors: list[str]
) -> None:
    """Reject a non-empty retired capture-level ``sources`` array."""
    inline = capture.get("sources")
    if inline is not None and inline != []:
        errors.append(
            f"capture file {path.name}: the retired capture-level sources array must stay empty; register sources in sources.json"
        )


def _load_capture_records(
    data_dir: Path, errors: list[str]
) -> tuple[list[object], list[object]]:
    """Read records/ and conflicts from every capture file."""
    records: list[object] = []
    conflicts: list[object] = []
    record_dir = data_dir / "records"
    if not record_dir.is_dir():
        return records, conflicts
    for path in sorted(record_dir.glob("*.json")):
        capture = _read_json(path, errors)
        if capture is None:
            continue
        entry = _mapping(capture)
        if entry is None:
            errors.append(f"capture file {path.name}: must be an object")
            continue
        _check_capture_sources(path, entry, errors)
        file_records = _sequence(entry.get("records"))
        if file_records is None:
            errors.append(f"capture file {path.name}: records must be an array")
        else:
            records.extend(file_records)
        file_conflicts = _sequence(entry.get("conflicts"))
        if file_conflicts is not None:
            conflicts.extend(file_conflicts)
    return records, conflicts


def run(data_dir: Path) -> list[str]:
    """Read one corpus directory and return every contract error."""
    if _is_fixtures_path(data_dir):
        return [
            f"data-dir {data_dir}: the fixtures path is a negative-test corpus; the validator never treats it as production"
        ]

    errors: list[str] = []
    sources: list[object] = []

    registry = data_dir / "sources.json"
    if not registry.is_file():
        errors.append(f"missing source registry: {registry}")
    else:
        loaded = _read_json(registry, errors)
        registry_list = _sequence(loaded)
        if registry_list is None:
            if loaded is not None:
                errors.append("sources.json: must be a top-level array")
        else:
            sources.extend(registry_list)

    records, conflicts = _load_capture_records(data_dir, errors)
    catalogue_load = vehicle_catalogue.load(
        data_dir, profile=vehicle_catalogue.AIRCRAFT_PROFILE
    )
    errors.extend(catalogue_load.errors)
    catalogue = [entry.to_mapping() for entry in catalogue_load.entries]
    class_map = [mapping.to_mapping() for mapping in catalogue_load.mappings]
    bindings = [binding.to_mapping() for binding in catalogue_load.bindings]
    catalogue_ids = {entry.catalogue_id for entry in catalogue_load.entries}

    conflicts_file = data_dir / "conflicts.json"
    if conflicts_file.is_file():
        loaded = _read_json(conflicts_file, errors)
        file_conflicts = _sequence(loaded)
        if file_conflicts is None:
            wrapper = _mapping(loaded)
            nested = _sequence(wrapper.get("conflicts")) if wrapper else None
            if nested is None:
                errors.append(
                    "conflicts.json: must be an array or hold a conflicts array"
                )
            else:
                conflicts.extend(nested)
        else:
            conflicts.extend(file_conflicts)

    errors.extend(validate_held_sources(sources, data_dir / "sources"))
    errors.extend(validate_corpus(sources, records, conflicts))

    by_id = validate_sources(sources, [])
    if catalogue:
        errors.extend(validate_catalogue(catalogue, by_id))
    errors.extend(validate_class_map(class_map, catalogue_ids, by_id))
    errors.extend(validate_class_bindings(bindings, catalogue_ids, by_id))
    return errors


def _self_source(
    source_id: str,
    tier: int,
    source_type: str,
    primary_held: bool = False,
    sha256: str = "",
) -> dict[str, object]:
    return {
        "source_id": source_id,
        "tier": tier,
        "type": source_type,
        "title": "FIXTURE source, not a held document",
        "identifier": "FIXTURE",
        "retrieved": "2026-10-05",
        "primary_held": primary_held,
        "sha256": sha256,
    }


def _self_sources() -> list[object]:
    return [
        _self_source("fx_standard", 1, "standard", True, sha256="0" * 64),
        _self_source("fx_manual", 2, "manual", True, sha256="1" * 64),
        _self_source("fx_measure", 3, "measurement", True, sha256="2" * 64),
        _self_source("fx_manufacturer", 4, "manufacturer"),
        _self_source("fx_compilation", 5, "compilation"),
        _self_source("fx_geometry", 5, "engine_geometry"),
        _self_source("fx_engine_config", 5, "engine_config"),
        _self_source("fx_class_table", 5, "class_table"),
    ]


def _self_by_id() -> dict[str, dict[str, object]]:
    by_id: dict[str, dict[str, object]] = {}
    for raw in _self_sources():
        entry = _mapping(raw)
        if entry is not None:
            by_id[str(entry.get("source_id"))] = entry
    return by_id


def _self_value(
    value: object, unit: str, source: str, grade: str, **extra: object
) -> dict[str, object]:
    entry: dict[str, object] = {
        "value": value,
        "unit": unit,
        "source": source,
        "locator": "fixture locator",
        "state": "fixture state",
        "grade": grade,
    }
    entry.update(extra)
    return entry


def _self_record() -> dict[str, object]:
    return {
        "variant_id": "fixture_variant",
        "game_class": "FIXTURE_CLASS",
        "class_token": "Plane",
        "identity_source": "fx_manual",
        "maker": "FIXTURE",
        "model": "FIXTURE",
        "variant": "FIXTURE",
        "country": "NONE",
        "era": "none",
        "vehicle_type": "fixed_wing",
        "runtime_ready": True,
        "values": {
            "operating_weight_kg": _self_value(1, "kg", "fx_manual", "documented"),
            "rated_power_w": _self_value(1, "W", "fx_manual", "documented"),
            "drag_area_m2": _self_value(1, "m^2", "fx_manual", "documented"),
            "length_m": _self_value(1, "m", "fx_standard", "standard"),
        },
    }


def _self_rotary_record() -> dict[str, object]:
    record = _self_record()
    record["variant_id"] = "fixture_rotary_variant"
    record["class_token"] = "Helicopter"
    record["vehicle_type"] = "rotary_wing"
    values = _self_values(record)
    values["rotor_disc_area_m2"] = _self_value(1, "m^2", "fx_manual", "documented")
    values["rotor_diameter_m"] = _self_value(1, "m", "fx_manual", "documented")
    return record


def _self_catalogue_entry() -> dict[str, object]:
    return {
        "catalogue_id": "fixture_cat",
        "canonical_name": "FIXTURE",
        "maker": "FIXTURE",
        "model": "FIXTURE",
        "variant": "FIXTURE",
        "variant_id": "fixture_cat_variant",
        "vehicle_type": "fixed_wing",
        "class_token": "Plane",
        "country": "NONE",
        "era": "none",
        "aliases": ["fixture"],
        "keywords": ["fixture"],
        "runtime_ready": False,
        "values": {
            "operating_weight_kg": _self_value(1, "kg", "fx_manual", "documented"),
            "rated_power_w": _self_value(1, "W", "fx_manual", "documented"),
        },
    }


def _self_derived_catalogue_entry() -> dict[str, object]:
    """A jet entry whose rated power derives from thrust at a reference speed."""
    entry = _self_catalogue_entry()
    entry["catalogue_id"] = "fixture_derived_cat"
    entry["variant_id"] = "fixture_derived_variant"
    values = _self_values(entry)
    del values["rated_power_w"]
    values["thrust_kn"] = _self_value(1, "kN", "fx_manual", "documented")
    values["reference_speed_ms"] = _self_value(1, "m/s", "fx_manual", "documented")
    return entry


def _self_binding(
    identity_source: str = "fx_manual",
    game_class: str = "FIXTURE_CLASS",
    catalogue_id: str = "fixture_cat",
) -> dict[str, object]:
    return {
        "game_class": game_class,
        "class_token": "Plane",
        "catalogue_id": catalogue_id,
        "identity_source": identity_source,
        "identity_evidence": "fixture evidence text names Plane",
        "grade": "documented",
        "note": "fixture binding",
    }


def _self_values(record: dict[str, object]) -> dict[str, object]:
    values = record.get("values")
    if not isinstance(values, dict):
        raise TypeError("self-check record has no values")
    return cast("dict[str, object]", values)


def _self_field(record: dict[str, object], name: str) -> dict[str, object]:
    entry = _self_values(record).get(name)
    if not isinstance(entry, dict):
        raise KeyError(name)
    return cast("dict[str, object]", entry)


def _self_conflict() -> dict[str, object]:
    return {
        "entity": "fixture_variant",
        "field": "operating_weight_kg",
        "value_a": 1,
        "source_a": "fx_manual",
        "value_b": 2,
        "source_b": "fx_measure",
        "resolution": "keep both values, keyed by state",
        "rule_applied": "record both, never average",
        "date": "2026-10-05",
    }


def _self_held_check(failures: list[str]) -> None:
    """Exercise the held-source digest check against a temporary directory."""
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        data = b"self-check held bytes"
        (dest / "fx_standard.bin").write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        held = [_self_source("fx_standard", 1, "standard", True, sha256=digest)]
        if validate_held_sources(held, dest):
            failures.append("self-check held source: matching bytes were rejected")
        held[0]["sha256"] = "0" * 64
        if not any(
            "fx_standard" in error for error in validate_held_sources(held, dest)
        ):
            failures.append("self-check held digest: mismatch did not name fx_standard")


def self_check() -> list[str]:
    """Exercise the validator on in-memory fixtures. No network, no corpus."""
    failures: list[str] = []
    good = validate_corpus(_self_sources(), [_self_record(), _self_rotary_record()], [])
    if good:
        return ["self-check good corpus is not clean: " + "; ".join(good)]
    if validate_catalogue([_self_catalogue_entry()], _self_by_id()):
        failures.append("self-check good catalogue: a valid entry was rejected")
    if validate_catalogue([_self_derived_catalogue_entry()], _self_by_id()):
        failures.append("self-check derived catalogue: a named derivation was rejected")
    if validate_class_bindings([_self_binding()], {"fixture_cat"}, _self_by_id()):
        failures.append("self-check good binding: a valid binding was rejected")

    def check(
        label: str, needle: str, sources: object, records: object, conflicts: object
    ) -> None:
        errors = validate_corpus(sources, records, conflicts)
        if not any(needle in error for error in errors):
            failures.append(f"self-check {label}: expected an error naming {needle!r}")

    record = _self_rotary_record()
    del _self_values(record)["rotor_disc_area_m2"]
    del _self_values(record)["rotor_diameter_m"]
    check(
        "rotary missing disc area",
        "misses required field rotor_disc_area_m2",
        _self_sources(),
        [record],
        [],
    )

    record = _self_record()
    del _self_field(record, "operating_weight_kg")["source"]
    check("missing source", "source is required", _self_sources(), [record], [])

    record = _self_record()
    _self_field(record, "operating_weight_kg")["source"] = "ghost"
    check("unknown source", "unknown source ghost", _self_sources(), [record], [])

    record = _self_record()
    _self_field(record, "length_m")["grade"] = "guessed"
    check("invalid grade", "grade must be one of", _self_sources(), [record], [])

    record = _self_record()
    del _self_field(record, "operating_weight_kg")["unit"]
    check("missing unit", "unit is required", _self_sources(), [record], [])

    record = _self_record()
    del _self_field(record, "operating_weight_kg")["state"]
    check("missing state", "state is required", _self_sources(), [record], [])

    record = _self_record()
    sources = _self_sources()
    for raw in sources:
        if isinstance(raw, dict) and raw.get("source_id") == "fx_manual":
            cast("dict[str, object]", raw)["primary_held"] = False
    check(
        "documented not held",
        "needs a held tier 2 or 3 manual",
        sources,
        [record],
        [],
    )

    record = _self_record()
    _self_field(record, "operating_weight_kg")["source"] = "fx_engine_config"
    check(
        "forbidden engine_config",
        "forbidden for a value",
        _self_sources(),
        [record],
        [],
    )

    record = _self_record()
    _self_field(record, "rated_power_w")["source"] = "fx_class_table"
    check(
        "forbidden class_table",
        "forbidden for a value",
        _self_sources(),
        [record],
        [],
    )

    record = _self_record()
    _self_field(record, "operating_weight_kg")["source"] = "fx_geometry"
    check(
        "forbidden engine_geometry",
        "never an aircraft value",
        _self_sources(),
        [record],
        [],
    )

    record = _self_record()
    del _self_values(record)["rated_power_w"]
    check(
        "incomplete runtime-ready",
        "misses required field rated_power_w",
        _self_sources(),
        [record],
        [],
    )

    record = _self_record()
    entry = _self_field(record, "operating_weight_kg")
    entry["source"] = "fx_compilation"
    entry["grade"] = "claimed"
    check(
        "unheld source without UNSOURCED state",
        "needs the state to start with UNSOURCED",
        _self_sources(),
        [record],
        [],
    )

    record = _self_record()
    entry = _self_field(record, "operating_weight_kg")
    entry["source"] = "fx_compilation"
    entry["grade"] = "claimed"
    entry["state"] = "UNSOURCED fixture lead"
    check(
        "UNSOURCED runtime field",
        "never fills a runtime field",
        _self_sources(),
        [record],
        [],
    )

    record = _self_record()
    entry = _self_field(record, "operating_weight_kg")
    entry["source"] = "fx_compilation"
    entry["grade"] = "standard"
    check(
        "tier 5 wrong grade",
        "tier 5 source needs grade claimed",
        _self_sources(),
        [record],
        [],
    )

    record = _self_record()
    entry = _self_field(record, "rated_power_w")
    entry["grade"] = "derived"
    check(
        "derived without marker",
        "needs the named derivation marker",
        _self_sources(),
        [record],
        [],
    )

    conflict = _self_conflict()
    conflict["resolution"] = "averaged to one value"
    check(
        "averaged conflict",
        "averaged conflict is forbidden",
        _self_sources(),
        [_self_record()],
        [conflict],
    )

    catalogue = [_self_catalogue_entry(), _self_catalogue_entry()]
    if not any(
        "duplicate catalogue_id" in error
        for error in validate_catalogue(catalogue, _self_by_id())
    ):
        failures.append("self-check catalogue: duplicate catalogue_id was accepted")

    class_map = [
        {
            "game_class": "FIXTURE_CLASS",
            "class_token": "Plane",
            "catalogue_id": "fixture_cat",
            "identity_source": "fx_engine_config",
            "identity_evidence": "fixture evidence",
            "grade": "documented",
        }
    ]
    if not any(
        "category guess cannot create a class map" in error
        for error in validate_class_map(class_map, {"fixture_cat"}, _self_by_id())
    ):
        failures.append("self-check class map: an engine identity source was accepted")

    if not any(
        "duplicate game_class" in error
        for error in validate_class_bindings(
            [_self_binding(), _self_binding()], {"fixture_cat"}, _self_by_id()
        )
    ):
        failures.append("self-check binding: a duplicate game_class was accepted")

    if not any(
        "unknown catalogue_id ghost_cat" in error
        for error in validate_class_bindings(
            [_self_binding(catalogue_id="ghost_cat")], {"fixture_cat"}, _self_by_id()
        )
    ):
        failures.append("self-check binding: an unknown catalogue_id was accepted")

    if not any(
        "a binding needs grade claimed" in error
        for error in validate_class_bindings(
            [_self_binding(identity_source="fx_class_table")],
            {"fixture_cat"},
            _self_by_id(),
        )
    ):
        failures.append(
            "self-check binding: a class-table source was accepted unclaimed"
        )

    _self_held_check(failures)
    return failures


def _parse_args(argv: Sequence[str]) -> tuple[bool, str]:
    data_dir = str(DEFAULT_DATA)
    self_check_enabled = False
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--self-check":
            self_check_enabled = True
        elif arg == "--data-dir":
            index += 1
            if index >= len(argv):
                raise SystemExit("--data-dir needs a path")
            data_dir = argv[index]
        elif arg in ("-h", "--help"):
            print("usage: validate_aircraft_data.py [--data-dir PATH] [--self-check]")
            raise SystemExit(0)
        else:
            raise SystemExit(f"unknown argument: {arg}")
        index += 1
    return self_check_enabled, data_dir


def main(argv: Sequence[str] | None = None) -> int:
    self_check_enabled, data_dir = _parse_args(sys.argv[1:] if argv is None else argv)

    if self_check_enabled:
        failures = self_check()
        if failures:
            print("aircraft data gate: FAIL")
            for failure in failures:
                print(f"  {failure}")
            return 1
        print("aircraft data gate: PASS (self-check)")
        return 0

    errors = run(Path(data_dir))
    if errors:
        print("aircraft data gate: FAIL")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"aircraft data gate: PASS ({data_dir})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
