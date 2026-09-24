#!/usr/bin/env python3
"""Shared loader for the vehicle catalogue and the class-to-catalogue map.

The loader reads ``data/vehicle/catalogue/*.json`` and
``data/vehicle/class_map.json`` and returns typed records. The validator and
the generator share it, so the corpus has one read path. The loader stays
independent of the runtime SQF. It reads corpus data only, never a config,
and it invents no value.

Rules it enforces:

- A ``catalogue_id`` and a ``variant_id`` are unique in the corpus. The loader
  keeps the first record and drops a duplicate with an error.
- An alias and a keyword are normalised to the runtime match key: lowercase
  letters and digits only, as ``fnc_getWeaponData.sqf`` does.
- An alias claimed by two entries is not an identity signal. The loader drops
  it from the alias index and warns.
- A class map needs a real-world mapping source. A record with no mapping
  source, or with an engine source, is rejected.
- A catalogue capture keeps its retired ``sources`` array empty.

A held-source lead loads as a record with ``runtime_ready`` false. The loader
never marks a record runtime-ready.

Run: imported by ``tools/validation/validate_vehicle_data.py`` and the
generator. No command-line entry point.
"""

from __future__ import annotations

import json
import re
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

# The real-world source types. Only these can be a class-map mapping source.
REAL_SOURCE_TYPES = frozenset(
    {"standard", "manual", "measurement", "manufacturer", "compilation"}
)

# The class-map grade set per schema section 7.
CLASS_MAP_GRADES = frozenset({"documented", "claimed"})

# The vehicle types the runtime projection supports.
VEHICLE_TYPES = frozenset({"wheeled", "tracked"})

# The fixed unit of every runtime field. The wider field vocabulary lives in
# the validator; these are the seven NRMM inputs only.
RUNTIME_FIELD_UNITS: dict[str, str] = {
    "operating_weight_kg": "kg",
    "tyre_width_mm": "mm",
    "tyre_diameter_mm": "mm",
    "ground_clearance_mm": "mm",
    "net_power_kw": "kW",
    "transmission_type": "enum",
    "grousers_state": "enum",
    "track_shoe_width_mm": "mm",
    "track_pitch_mm": "mm",
}

# The seven NRMM inputs per vehicle type, in projection order. A tracked set
# carries the two track fields. It never requires a tyre field.
REQUIRED_RUNTIME_BY_TYPE: dict[str, tuple[str, ...]] = {
    "wheeled": (
        "operating_weight_kg",
        "tyre_width_mm",
        "tyre_diameter_mm",
        "ground_clearance_mm",
        "net_power_kw",
        "transmission_type",
        "grousers_state",
    ),
    "tracked": (
        "operating_weight_kg",
        "track_shoe_width_mm",
        "track_pitch_mm",
        "ground_clearance_mm",
        "net_power_kw",
        "transmission_type",
        "grousers_state",
    ),
}

# The runtime fields that carry a word, not a number.
TEXT_RUNTIME_FIELDS = frozenset({"transmission_type", "grousers_state"})

# The grade vocabulary of a resolved runtime field. ``absent`` means the
# corpus holds no value and no derivation applies. The row still emits.
RESOLVED_GRADES = frozenset({"standard", "documented", "claimed", "derived", "absent"})

# The five keys a complete held value object carries beside its value.
VALUE_META_KEYS = ("unit", "source", "locator", "state", "grade")

# Named derivations. Each formula is a citation, not a guess.
HP_TO_KW = 0.745699872
INCH_TO_MM = 25.4
POWER_ROUND = 6
TYRE_ROUND = 4

# A derived value must name its formula in the state text. The marker is the
# phrase the generator writes and the validator checks.
DERIVATION_STATE_MARKERS: dict[str, str] = {
    "operating_weight_kg": "derived operating weight",
    "net_power_kw": "1 hp = 745.699872 W",
    "tyre_width_mm": "derived from the size code",
    "tyre_diameter_mm": "derived from the size code",
}
DERIVATION_FIELDS = frozenset(DERIVATION_STATE_MARKERS)

# Engine identity sources. They can bind a game class only at grade
# ``claimed`` and only when the evidence names the concrete token or kind.
ENGINE_MAPPING_SOURCE_TYPES = frozenset({"engine_config", "class_table"})

_NON_KEY = re.compile(r"[^a-z0-9]+")


def normalise(text: str) -> str:
    """Return the runtime match key: lowercase letters and digits only."""
    return _NON_KEY.sub("", text.lower())


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


def _normalised_list(
    value: object, where: str, field_name: str, errors: list[str]
) -> tuple[str, ...]:
    """Return the deduplicated match keys of an alias or keyword array."""
    items = _sequence(value)
    if items is None:
        errors.append(f"{where}: {field_name} must be an array")
        return ()
    keys: list[str] = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{where}: {field_name} holds a non-string entry")
            continue
        key = normalise(item)
        if key and key not in keys:
            keys.append(key)
    return tuple(keys)


@dataclass(frozen=True)
class CatalogueEntry:
    """One real-world catalogue entry, loaded and normalised."""

    catalogue_id: str
    canonical_name: str
    maker: str
    model: str
    variant: str
    variant_id: str
    vehicle_type: str
    class_token: str
    country: str
    era: str
    aliases: tuple[str, ...]
    keywords: tuple[str, ...]
    runtime_ready: bool
    values: dict[str, object]
    source_file: str

    def identity_aliases(self) -> tuple[str, ...]:
        """Every token that names this entry: id, variant id and aliases."""
        tokens = [normalise(self.catalogue_id), normalise(self.variant_id)]
        tokens.extend(self.aliases)
        keys: list[str] = []
        for token in tokens:
            if token and token not in keys:
                keys.append(token)
        return tuple(keys)

    def resolved_fields(self) -> dict[str, ResolvedField]:
        """Resolve the runtime fields of this entry for the projection."""
        return resolve_fields(self.vehicle_type, self.values)

    def to_mapping(self) -> dict[str, object]:
        """Return the record as a plain mapping for the contract validator.

        ``values`` holds the held value objects only. ``resolved`` holds the
        graded runtime projection: one entry per runtime field, each resolved
        to a held value, a named derivation or a labelled absent zero.
        """
        return {
            "catalogue_id": self.catalogue_id,
            "canonical_name": self.canonical_name,
            "maker": self.maker,
            "model": self.model,
            "variant": self.variant,
            "variant_id": self.variant_id,
            "vehicle_type": self.vehicle_type,
            "class_token": self.class_token,
            "country": self.country,
            "era": self.era,
            "aliases": list(self.aliases),
            "keywords": list(self.keywords),
            "runtime_ready": self.runtime_ready,
            "values": self.values,
            "resolved": {
                name: field.to_mapping()
                for name, field in self.resolved_fields().items()
            },
        }


@dataclass(frozen=True)
class ClassMapping:
    """One game-class to catalogue mapping with its real-world evidence."""

    game_class: str
    class_token: str
    catalogue_id: str
    identity_source: str
    identity_evidence: str
    grade: str
    note: str
    source_file: str

    def to_mapping(self) -> dict[str, object]:
        """Return the mapping as a plain mapping for the contract validator."""
        return {
            "game_class": self.game_class,
            "class_token": self.class_token,
            "catalogue_id": self.catalogue_id,
            "identity_source": self.identity_source,
            "identity_evidence": self.identity_evidence,
            "grade": self.grade,
            "note": self.note,
        }


@dataclass(frozen=True)
class ResolvedField:
    """One runtime field after the graded resolution ladder."""

    name: str
    value: object
    unit: str
    source: str
    locator: str
    state: str
    grade: str

    def to_mapping(self) -> dict[str, object]:
        """Return the resolved field as a plain value object."""
        return {
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "locator": self.locator,
            "state": self.state,
            "grade": self.grade,
        }


def held_value(values: dict[str, object], field: str) -> dict[str, object] | None:
    """Return a complete held value object for one field, or None."""
    entry = _mapping(values.get(field))
    if entry is None:
        return None
    if entry.get("value") in (None, ""):
        return None
    for key in VALUE_META_KEYS:
        if entry.get(key) in (None, ""):
            return None
    return entry


def _from_held(field: str, entry: dict[str, object]) -> ResolvedField:
    return ResolvedField(
        name=field,
        value=entry.get("value"),
        unit=str(entry.get("unit", "")),
        source=str(entry.get("source", "")),
        locator=str(entry.get("locator", "")),
        state=str(entry.get("state", "")),
        grade=str(entry.get("grade", "")),
    )


def _absent(field: str) -> ResolvedField:
    """A field no held value and no derivation reaches: a labelled zero."""
    value: object = "" if field in TEXT_RUNTIME_FIELDS else 0
    return ResolvedField(
        name=field,
        value=value,
        unit=RUNTIME_FIELD_UNITS.get(field, ""),
        source="",
        locator="",
        state="no held value and no derivation applies",
        grade="absent",
    )


# The metric size code, for example 395/85R20. The inch form is handled after
# the imperial colon is folded to a decimal point.
_METRIC_TYRE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*R?\s*(\d+(?:\.\d+)?)\s*$"
)
_INCH_TYRE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[xX\-\s]+\s*R?\s*(\d+(?:\.\d+)?)\s*$")


def parse_tyre_size(code: str) -> tuple[float, float] | None:
    """Return ``(width_mm, diameter_mm)`` from a size code, or None.

    Metric ``395/85R20``: width is the first figure, the section height is
    ``width * aspect / 100`` and the diameter adds two sections to the rim.
    Inch ``14:00 x R20``, ``14.00-20`` or ``14x20``: the aspect is 100 by
    definition for a cross-ply truck tyre, so the section equals the width.
    """
    metric = _METRIC_TYRE.match(code)
    if metric is not None:
        width = float(metric.group(1))
        aspect = float(metric.group(2))
        rim = float(metric.group(3))
        section = width * aspect / 100.0
        return (
            round(width, TYRE_ROUND),
            round(rim * INCH_TO_MM + 2.0 * section, TYRE_ROUND),
        )
    inch = _INCH_TYRE.match(code.replace(":", "."))
    if inch is not None:
        width_in = float(inch.group(1))
        rim_in = float(inch.group(2))
        return (
            round(width_in * INCH_TO_MM, TYRE_ROUND),
            round((rim_in + 2.0 * width_in) * INCH_TO_MM, TYRE_ROUND),
        )
    return None


NET_POWER_STATE = (
    "brake horsepower converted by 1 hp = 745.699872 W (ISO 80000-4, "
    "mechanical horsepower); the source states brake, not net, power"
)


def _derive_operating_weight(values: dict[str, object]) -> ResolvedField | None:
    for basis in ("curb_weight_kg", "gross_weight_kg"):
        base = held_value(values, basis)
        if base is None:
            continue
        if basis == "curb_weight_kg":
            state = (
                "derived operating weight from the published curb weight; no "
                "operating weight is published, so the curb weight is the basis"
            )
        else:
            state = (
                "derived operating weight from the gross vehicle weight rating; "
                "no operating or curb weight is published, so the rating is the "
                "basis and it is a maximum, not a kerb weight"
            )
        return ResolvedField(
            name="operating_weight_kg",
            value=base.get("value"),
            unit="kg",
            source=str(base.get("source", "")),
            locator=str(base.get("locator", "")),
            state=state,
            grade="derived",
        )
    return None


def _derive_net_power(values: dict[str, object]) -> ResolvedField | None:
    base = held_value(values, "published_power_hp")
    if base is None:
        return None
    hp = base.get("value")
    if not isinstance(hp, (int, float)) or isinstance(hp, bool):
        return None
    return ResolvedField(
        name="net_power_kw",
        value=round(float(hp) * HP_TO_KW, POWER_ROUND),
        unit="kW",
        source=str(base.get("source", "")),
        locator=str(base.get("locator", "")),
        state=NET_POWER_STATE,
        grade="derived",
    )


def _derive_tyre(values: dict[str, object], field: str) -> ResolvedField | None:
    base = held_value(values, "tyre_size_text")
    if base is None:
        return None
    code = base.get("value")
    if not isinstance(code, str):
        return None
    parsed = parse_tyre_size(code)
    if parsed is None:
        return None
    width, diameter = parsed
    state = (
        f"derived from the size code {code} by W mm, section = W*A/100, "
        "diameter = rim*25.4 + 2*section (inch codes assume aspect 100)"
    )
    return ResolvedField(
        name=field,
        value=width if field == "tyre_width_mm" else diameter,
        unit="mm",
        source=str(base.get("source", "")),
        locator=str(base.get("locator", "")),
        state=state,
        grade="derived",
    )


def resolve_field(values: dict[str, object], field: str) -> ResolvedField:
    """Resolve one runtime field: held, then the named derivation, then zero."""
    held = held_value(values, field)
    if held is not None:
        return _from_held(field, held)
    if field == "operating_weight_kg":
        derived = _derive_operating_weight(values)
    elif field == "net_power_kw":
        derived = _derive_net_power(values)
    elif field in ("tyre_width_mm", "tyre_diameter_mm"):
        derived = _derive_tyre(values, field)
    else:
        derived = None
    if derived is not None:
        return derived
    return _absent(field)


def resolve_fields(
    vehicle_type: str, values: dict[str, object]
) -> dict[str, ResolvedField]:
    """Resolve every runtime field of one vehicle type, in projection order."""
    required = REQUIRED_RUNTIME_BY_TYPE.get(vehicle_type, ())
    return {field: resolve_field(values, field) for field in required}


def is_runtime_ready(vehicle_type: str, values: dict[str, object]) -> bool:
    """True when every runtime field resolves to a non-absent value."""
    required = REQUIRED_RUNTIME_BY_TYPE.get(vehicle_type)
    if not required:
        return False
    resolved = resolve_fields(vehicle_type, values)
    return all(field.grade != "absent" for field in resolved.values())


def source_record_id(vehicle_type: str, values: dict[str, object]) -> str:
    """The source id of the first field that resolved via a held value or a
    named derivation, or an empty string when every field is absent."""
    for field in REQUIRED_RUNTIME_BY_TYPE.get(vehicle_type, ()):
        resolved = resolve_field(values, field)
        if resolved.grade != "absent" and resolved.source:
            return resolved.source
    return ""


@dataclass
class CatalogueLoad:
    """The result of one load. Errors and warnings are explicit."""

    entries: list[CatalogueEntry]
    mappings: list[ClassMapping]
    alias_index: dict[str, str]
    warnings: list[str]
    errors: list[str]


def _read_json(path: Path, errors: list[str]) -> object | None:
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: cannot parse JSON: {exc}")
        return None
    return loaded


def _load_entry(
    raw: object,
    source_file: str,
    seen_ids: set[str],
    seen_variants: set[str],
    errors: list[str],
) -> CatalogueEntry | None:
    record = _mapping(raw)
    if record is None:
        errors.append(f"catalogue file {source_file}: entry must be an object")
        return None
    cid = _text(record.get("catalogue_id"))
    if cid is None:
        errors.append(f"catalogue file {source_file}: entry has no catalogue_id")
        return None
    where = f"catalogue {cid}"
    if cid in seen_ids:
        errors.append(f"{where}: duplicate catalogue_id")
        return None
    seen_ids.add(cid)

    variant_id = _text(record.get("variant_id")) or ""
    if variant_id:
        if variant_id in seen_variants:
            errors.append(f"{where}: duplicate variant_id {variant_id}")
            return None
        seen_variants.add(variant_id)

    declared_ready = record.get("runtime_ready")
    if not isinstance(declared_ready, bool):
        errors.append(f"{where}: runtime_ready must be true or false")

    values = _mapping(record.get("values"))
    if values is None:
        errors.append(f"{where}: values must be an object")
        values = {}

    vehicle_type = _text(record.get("vehicle_type")) or ""
    # The reported flag means every runtime field resolved to a non-absent
    # value. It never blocks a row.
    runtime_ready = is_runtime_ready(vehicle_type, values)

    aliases = _normalised_list(record.get("aliases"), where, "aliases", errors)
    keywords = _normalised_list(record.get("keywords"), where, "keywords", errors)

    return CatalogueEntry(
        catalogue_id=cid,
        canonical_name=_text(record.get("canonical_name")) or "",
        maker=_text(record.get("maker")) or "",
        model=_text(record.get("model")) or "",
        variant=_text(record.get("variant")) or "",
        variant_id=variant_id,
        vehicle_type=vehicle_type,
        class_token=_text(record.get("class_token")) or "",
        country=_text(record.get("country")) or "",
        era=_text(record.get("era")) or "",
        aliases=aliases,
        keywords=keywords,
        runtime_ready=runtime_ready,
        values=values,
        source_file=source_file,
    )


def _load_entries(data_dir: Path, errors: list[str]) -> list[CatalogueEntry]:
    entries: list[CatalogueEntry] = []
    seen_ids: set[str] = set()
    seen_variants: set[str] = set()
    catalogue_dir = data_dir / "catalogue"
    if not catalogue_dir.is_dir():
        return entries
    for path in sorted(catalogue_dir.glob("*.json")):
        capture = _mapping(_read_json(path, errors))
        if capture is None:
            errors.append(f"catalogue file {path.name}: must be an object")
            continue
        inline = capture.get("sources")
        if inline is not None and inline != []:
            errors.append(
                f"catalogue file {path.name}: the retired capture-level sources "
                "array must stay empty; register sources in sources.json"
            )
        raw_entries = _sequence(capture.get("entries"))
        if raw_entries is None:
            errors.append(f"catalogue file {path.name}: entries must be an array")
            continue
        for raw in raw_entries:
            entry = _load_entry(raw, path.name, seen_ids, seen_variants, errors)
            if entry is not None:
                entries.append(entry)
    return entries


def _build_alias_index(
    entries: list[CatalogueEntry], warnings: list[str]
) -> dict[str, str]:
    """Index unique identity tokens. Drop a shared token and warn."""
    owners: dict[str, list[str]] = {}
    for entry in entries:
        for token in entry.identity_aliases():
            owners.setdefault(token, []).append(entry.catalogue_id)
    index: dict[str, str] = {}
    for token, claiming in sorted(owners.items()):
        unique = sorted(set(claiming))
        if len(unique) > 1:
            warnings.append(
                f"alias {token} is claimed by {len(unique)} entries "
                f"({', '.join(unique)}) and is dropped from the alias index"
            )
            continue
        index[token] = unique[0]
    return index


def _real_source_ids(data_dir: Path, errors: list[str]) -> set[str]:
    """Read sources.json and return the real-world mapping source ids."""
    path = data_dir / "sources.json"
    if not path.is_file():
        return set()
    loaded = _sequence(_read_json(path, errors))
    if loaded is None:
        return set()
    ids: set[str] = set()
    for raw in loaded:
        source = _mapping(raw)
        if source is None:
            continue
        sid = _text(source.get("source_id"))
        if sid is not None and source.get("type") in REAL_SOURCE_TYPES:
            ids.add(sid)
    return ids


def _load_mapping(
    record: dict[str, object],
    catalogue_ids: set[str],
    real_source_ids: set[str],
    seen: set[str],
    errors: list[str],
) -> ClassMapping | None:
    game_class = _text(record.get("game_class"))
    where = f"class map {game_class or '<none>'}"
    ok = True

    if game_class is None:
        errors.append(
            f"{where}: game_class is required; a category guess cannot create a class map"
        )
        ok = False
    elif game_class in seen:
        errors.append(
            f"{where}: duplicate game_class; one game class maps to one catalogue entry"
        )
        return None
    else:
        seen.add(game_class)

    class_token = record.get("class_token")
    if not isinstance(class_token, str):
        errors.append(f"{where}: class_token must be a string")
        ok = False

    cid = _text(record.get("catalogue_id"))
    if cid is None:
        errors.append(f"{where}: catalogue_id is required")
        ok = False
    elif cid not in catalogue_ids:
        errors.append(f"{where}: unknown catalogue_id {cid}")
        ok = False

    grade = record.get("grade")
    grade_ok = isinstance(grade, str) and grade in CLASS_MAP_GRADES
    if not grade_ok:
        errors.append(f"{where}: grade must be one of {sorted(CLASS_MAP_GRADES)}")

    source_id = _text(record.get("identity_source"))
    if source_id is None:
        errors.append(
            f"{where}: identity_source is required; a real-world mapping source cannot be a guess"
        )
        ok = False
    elif source_id not in real_source_ids and grade != "claimed":
        # An engine class table or config can bind a class only at grade
        # claimed. A documented mapping needs a real-world source.
        errors.append(
            f"{where}: identity_source {source_id} is not a real-world mapping source"
        )
        ok = False

    evidence = _text(record.get("identity_evidence"))
    if evidence is None:
        errors.append(
            f"{where}: identity_evidence is required; name the words or locator that link the class to the entry"
        )
        ok = False

    if not grade_ok:
        ok = False

    if not ok:
        return None
    return ClassMapping(
        game_class=game_class or "",
        class_token=class_token if isinstance(class_token, str) else "",
        catalogue_id=cid or "",
        identity_source=source_id or "",
        identity_evidence=evidence or "",
        grade=grade if isinstance(grade, str) else "",
        note=_text(record.get("note")) or "",
        source_file="class_map.json",
    )


def _load_mappings(
    data_dir: Path,
    catalogue_ids: set[str],
    real_source_ids: set[str],
    errors: list[str],
) -> list[ClassMapping]:
    mappings: list[ClassMapping] = []
    path = data_dir / "class_map.json"
    if not path.is_file():
        return mappings
    loaded = _read_json(path, errors)
    records = _sequence(loaded)
    if records is None:
        if loaded is not None:
            errors.append("class_map.json: must be a top-level array")
        return mappings
    seen: set[str] = set()
    for raw in records:
        record = _mapping(raw)
        if record is None:
            errors.append("class map entry: must be an object")
            continue
        mapping = _load_mapping(record, catalogue_ids, real_source_ids, seen, errors)
        if mapping is not None:
            mappings.append(mapping)
    return mappings


def load(
    data_dir: Path, *, real_source_ids: Collection[str] | None = None
) -> CatalogueLoad:
    """Load the catalogue and the class map. Return typed records.

    ``real_source_ids`` names the source ids that can act as a mapping source.
    When it is None, the loader reads ``sources.json`` and takes the real-world
    types. A missing catalogue directory or class map loads as an empty list.
    """
    errors: list[str] = []
    warnings: list[str] = []
    entries = _load_entries(data_dir, errors)
    catalogue_ids = {entry.catalogue_id for entry in entries}
    if real_source_ids is None:
        real_ids = _real_source_ids(data_dir, errors)
    else:
        real_ids = set(real_source_ids)
    mappings = _load_mappings(data_dir, catalogue_ids, real_ids, errors)
    alias_index = _build_alias_index(entries, warnings)
    return CatalogueLoad(entries, mappings, alias_index, warnings, errors)
