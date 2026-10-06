#!/usr/bin/env python3
"""Shared loader for the device corpus (night vision, thermal and optic).

The loader reads ``data/device/sources.json`` and
``data/device/catalogue/*.json`` and returns typed records. The generator
and the tests share it, so the corpus has one read path. The loader reads
corpus data only. It reads no game config and it invents no value.

Rules it enforces:

- A ``device_id`` is unique in the corpus. The loader keeps the first
  record and reports the duplicate as an error.
- A ``family`` is one of ``nvg``, ``thermal`` or ``optic``.
- Every held value is an object with a value, a unit, a source, a locator,
  a state and a grade. A value with a missing key is an error.
- Every value names a source that exists in the registry. A value whose
  source is absent is an error.
- A grade is one of ``standard``, ``documented``, ``claimed``, ``derived``
  or ``absent``. A tier 5 compilation is ``claimed`` only.

Run: imported by ``tools/validation/gen_device_data.py`` and the tests. No
command-line entry point.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# The device families the runtime projection supports.
FAMILIES = frozenset({"nvg", "thermal", "optic"})

# The real-world source types. Only these can carry a device value.
REAL_SOURCE_TYPES = frozenset(
    {"standard", "manual", "measurement", "manufacturer", "compilation"}
)

# The grade vocabulary of a resolved runtime field. ``absent`` means the
# corpus holds no value and no derivation applies. The row still emits.
GRADES = frozenset({"standard", "documented", "claimed", "derived", "absent"})

# The six keys a complete held value object carries beside its value.
VALUE_META_KEYS = ("unit", "source", "locator", "state", "grade")

# The fixed unit of every runtime field.
RUNTIME_FIELD_UNITS: dict[str, str] = {
    "output_colour": "enum",
    "resolution_lpmm": "lp/mm",
    "snr": "ratio",
    "halo_mm": "mm",
    "netd_c": "C",
    "resolution_x": "count",
    "resolution_y": "count",
    "refresh_hz": "Hz",
    "cooled": "enum",
    "weight_kg": "kg",
    "band": "enum",
    "magnification": "ratio",
    "objective_mm": "mm",
    "fov_deg": "deg",
    "exit_pupil_mm": "mm",
    "active": "enum",
}

# The runtime inputs per family, in projection order. The tube row carries
# the image-intensifier figures. The thermal row carries the detector
# figures. The optic row carries the sight geometry.
REQUIRED_RUNTIME_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "nvg": ("output_colour", "resolution_lpmm", "snr", "halo_mm"),
    "thermal": (
        "netd_c",
        "resolution_x",
        "resolution_y",
        "refresh_hz",
        "cooled",
        "weight_kg",
        "band",
    ),
    "optic": (
        "magnification",
        "objective_mm",
        "fov_deg",
        "weight_kg",
        "exit_pupil_mm",
        "active",
    ),
}

# The runtime fields that carry a word, not a number.
TEXT_RUNTIME_FIELDS = frozenset({"output_colour", "cooled", "active", "band"})

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


def _key_list(value: object) -> tuple[str, ...]:
    """Return the deduplicated normalised keys of an alias or class array."""
    items = _sequence(value)
    if items is None:
        return ()
    keys: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        key = normalise(item)
        if key and key not in keys:
            keys.append(key)
    return tuple(keys)


@dataclass(frozen=True)
class SourceRecord:
    """One held source document."""

    source_id: str
    tier: int
    type: str
    title: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "tier": self.tier,
            "type": self.type,
            "title": self.title,
        }


@dataclass(frozen=True)
class DeviceEntry:
    """One real-world device, loaded and normalised."""

    device_id: str
    canonical_name: str
    family: str
    maker: str
    country: str
    class_names: tuple[str, ...]
    aliases: tuple[str, ...]
    keywords: tuple[str, ...]
    values: dict[str, object]
    source_file: str

    def resolved_fields(self) -> dict[str, ResolvedField]:
        """Resolve the runtime fields of this device for the projection."""
        return resolve_fields(self.family, self.values)

    def to_mapping(self) -> dict[str, object]:
        return {
            "device_id": self.device_id,
            "canonical_name": self.canonical_name,
            "family": self.family,
            "maker": self.maker,
            "country": self.country,
            "class_names": list(self.class_names),
            "aliases": list(self.aliases),
            "keywords": list(self.keywords),
            "values": self.values,
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
        return {
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "locator": self.locator,
            "state": self.state,
            "grade": self.grade,
        }


@dataclass(frozen=True)
class DeviceLoad:
    """The loaded corpus: the source registry and the device entries."""

    sources: dict[str, SourceRecord]
    entries: list[DeviceEntry]
    errors: list[str]


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
    """A field no held value reaches: a labelled zero or empty string."""
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


def resolve_field(values: dict[str, object], field: str) -> ResolvedField:
    """Resolve one runtime field: a held value, else a labelled absent."""
    held = held_value(values, field)
    if held is not None:
        return _from_held(field, held)
    return _absent(field)


def resolve_fields(family: str, values: dict[str, object]) -> dict[str, ResolvedField]:
    """Resolve every runtime field of one family, in projection order."""
    required = REQUIRED_RUNTIME_BY_FAMILY.get(family, ())
    return {field: resolve_field(values, field) for field in required}


def _load_sources(path: Path, errors: list[str]) -> dict[str, SourceRecord]:
    if not path.is_file():
        errors.append(f"{path}: the source registry is missing")
        return {}
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: {exc}")
        return {}
    if not isinstance(loaded, list):
        errors.append(f"{path}: the source registry must be a top-level array")
        return {}
    sources: dict[str, SourceRecord] = {}
    for raw in loaded:
        record = _mapping(raw)
        if record is None:
            errors.append(f"{path}: a source record is not an object")
            continue
        source_id = _text(record.get("source_id"))
        tier = record.get("tier")
        source_type = _text(record.get("type"))
        if source_id is None or not isinstance(tier, int) or source_type is None:
            errors.append(f"{path}: a source record is incomplete")
            continue
        sources[source_id] = SourceRecord(
            source_id=source_id,
            tier=tier,
            type=source_type,
            title=str(record.get("title", "")),
        )
    return sources


def _validate_value(
    where: str,
    field: str,
    entry: dict[str, object],
    sources: dict[str, SourceRecord],
    errors: list[str],
) -> None:
    if entry.get("value") in (None, ""):
        return
    for key in VALUE_META_KEYS:
        if entry.get(key) in (None, ""):
            errors.append(f"{where}: {field} is missing {key}")
    grade = entry.get("grade")
    if grade not in GRADES:
        errors.append(f"{where}: {field} grade {grade!r} is not allowed")
    source_id = entry.get("source")
    if not isinstance(source_id, str) or source_id not in sources:
        errors.append(f"{where}: {field} names an unknown source {source_id!r}")
        return
    unit = entry.get("unit")
    expected = RUNTIME_FIELD_UNITS.get(field)
    if expected is not None and unit != expected:
        errors.append(f"{where}: {field} unit {unit!r} does not match {expected!r}")
    source = sources[source_id]
    if source.tier >= 5 and grade != "claimed":
        errors.append(f"{where}: {field} is tier 5 and must be claimed, not {grade!r}")


def _load_catalogue(
    data_dir: Path,
    sources: dict[str, SourceRecord],
    errors: list[str],
) -> list[DeviceEntry]:
    catalogue_dir = data_dir / "catalogue"
    if not catalogue_dir.is_dir():
        errors.append(f"{catalogue_dir}: the catalogue directory is missing")
        return []
    entries: list[DeviceEntry] = []
    seen: set[str] = set()
    for path in sorted(catalogue_dir.glob("*.json")):
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        document = _mapping(loaded)
        if document is None:
            errors.append(f"{path}: the capture is not an object")
            continue
        records = _sequence(document.get("entries"))
        if records is None:
            errors.append(f"{path}: the capture holds no entries array")
            continue
        for raw in records:
            record = _mapping(raw)
            if record is None:
                errors.append(f"{path}: an entry is not an object")
                continue
            device_id = _text(record.get("device_id"))
            family = record.get("family")
            if device_id is None or family not in FAMILIES:
                errors.append(f"{path}: an entry has no id or a bad family")
                continue
            where = f"{path.name}:{device_id}"
            if device_id in seen:
                errors.append(f"{where}: duplicate device id")
                continue
            seen.add(device_id)
            values = _mapping(record.get("values"))
            values = values if values is not None else {}
            for field, value in values.items():
                entry = _mapping(value)
                if entry is None:
                    errors.append(f"{where}: {field} is not a value object")
                    continue
                _validate_value(where, field, entry, sources, errors)
            entries.append(
                DeviceEntry(
                    device_id=device_id,
                    canonical_name=str(record.get("canonical_name", "")),
                    family=str(family),
                    maker=str(record.get("maker", "")),
                    country=str(record.get("country", "")),
                    class_names=_key_list(record.get("class_names")),
                    aliases=_key_list(record.get("aliases")),
                    keywords=_key_list(record.get("keywords")),
                    values=values,
                    source_file=path.name,
                )
            )
    return entries


def load(data_dir: Path) -> DeviceLoad:
    """Read the source registry and the device catalogue."""
    errors: list[str] = []
    sources = _load_sources(data_dir / "sources.json", errors)
    entries = _load_catalogue(data_dir, sources, errors)
    return DeviceLoad(sources=sources, entries=entries, errors=errors)
