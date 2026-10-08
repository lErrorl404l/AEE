#!/usr/bin/env python3
"""Generate the aircraft coverage table and the aircraft gap reports.

The generator owns the coverage logic. It reads the four air tokens from the
shared class inventory ``data/vehicle/classes.json``, the aircraft catalogue
loader output and the aircraft class bindings, then writes four deterministic
artefacts:

  data/aircraft/coverage.json            one state per inventory token
  data/aircraft/COVERAGE_AUDIT.md        per-token runtime coverage
  data/aircraft/SOURCE_GAPS.md           per-entry missing runtime fields
  data/aircraft/CLASS_MAPPING_GAPS.md    air tokens and game classes with no
                                         sourced binding

The four air tokens (``Air``, ``Helicopter``, ``Plane``, ``UAV``) are in
scope. The states are ``recorded``, ``lead``, ``no_source`` and
``excluded_non_ground``. A token never leaves the inventory in silence. A
``recorded`` token has an emitted runtime row and a class binding for the
token. A lead is a researched candidate with no recorded row, so it never
reads as ``recorded``. An air token with no emitted row is ``no_source``. A
non-air token is ``excluded_non_ground``.

The gap reports name what is missing. They invent no value and add no
binding. A missing field is a gap with a next source class to try, taken
from the plan design table.

Run:  python3 tools/validation/gen_aircraft_coverage.py
      python3 tools/validation/gen_aircraft_coverage.py --data-dir PATH
      python3 tools/validation/gen_aircraft_coverage.py --check
Exit: 0 when the corpus obeys the contract, 1 when an output is stale.
Check mode writes nothing.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import cast

# A package import (tests) and a direct script run both resolve the sibling
# modules. The repository root goes on the path first.
_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

ROOT = _REPO
DEFAULT_DATA = ROOT / "data" / "aircraft"

# The class inventory is shared with the vehicle corpus. The aircraft corpus
# adds no classes.json, so the four air tokens are read from here.
CLASSES_PATH = ROOT / "data" / "vehicle" / "classes.json"

COVERAGE_OUT = "coverage.json"
COVERAGE_REPORT = "COVERAGE_AUDIT.md"
SOURCE_GAPS_REPORT = "SOURCE_GAPS.md"
CLASS_MAPPING_REPORT = "CLASS_MAPPING_GAPS.md"
ARTEFACTS = (
    COVERAGE_OUT,
    COVERAGE_REPORT,
    SOURCE_GAPS_REPORT,
    CLASS_MAPPING_REPORT,
)

COVERAGE_SCHEMA = "aee.aircraft.coverage/1"
COVERAGE_STATES = ("recorded", "lead", "no_source", "excluded_non_ground")
NON_AIR_STATE = "excluded_non_ground"
AIR_ABSENT_STATE = "no_source"

# The four air tokens the class inventory holds. They are the in-scope tokens
# for the aircraft corpus. Any other token is out of scope.
AIR_TOKENS = frozenset({"Air", "Helicopter", "Plane", "UAV"})

# The researched leads. Each air token maps to the reason carried in the
# committed table. A lead names a candidate and holds no runtime-ready entry,
# so it is never `recorded`. The guard promotes the token only when an emitted
# row and a class binding appear. The first slice holds no air lead: `UAV`
# lands `no_source` until a mapping exists.
LEAD_CANDIDATES: dict[str, str] = {}

# The next source class to try for each runtime-required field. The values
# come from the plan field table. A field with no entry falls back to the
# default.
NEXT_SOURCE_CLASS: dict[str, str] = {
    "operating_weight_kg": (
        "a tier 2 operating manual or a tier 4 manufacturer datasheet"
    ),
    "rated_power_w": ("the engine maker rating, or a tier 4 manufacturer datasheet"),
    "rotor_disc_area_m2": "a tier 3 or tier 4 rotor diameter datasheet",
    "drag_area_m2": "a tier 3 drag or wing-area databook",
}
DEFAULT_SOURCE_CLASS = "a held tier 2 manual or measurement source"
CLASS_MAP_SOURCE_CLASS = (
    "a real-world source that names the aircraft, corroborated by the engine "
    "displayName"
)

JsonObject = dict[str, object]


# --------------------------------------------------------------------------
# JSON helpers
# --------------------------------------------------------------------------


def _read_json(path: Path) -> object:
    return cast("object", json.loads(path.read_text(encoding="utf-8")))


def _as_mapping_or_none(value: object) -> JsonObject | None:
    if not isinstance(value, dict):
        return None
    result: JsonObject = {}
    for key, item in cast("dict[object, object]", value).items():
        result[str(key)] = item
    return result


def _as_mapping(value: object) -> JsonObject:
    result = _as_mapping_or_none(value)
    if result is None:
        raise TypeError(f"expected an object, got {type(value).__name__}")
    return result


def _as_sequence_or_none(value: object) -> list[object] | None:
    if not isinstance(value, list):
        return None
    return list(cast("list[object]", value))


def _as_sequence(value: object) -> list[object]:
    result = _as_sequence_or_none(value)
    if result is None:
        raise TypeError(f"expected an array, got {type(value).__name__}")
    return result


def _as_str(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"expected a string, got {type(value).__name__}")
    return value


def entries(payload: JsonObject) -> list[JsonObject]:
    """Return the token rows of an inventory or coverage payload."""
    return [_as_mapping(item) for item in _as_sequence(payload.get("tokens"))]


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def load_classes(path: Path = CLASSES_PATH) -> JsonObject:
    """Read the shared class inventory that holds the four air tokens."""
    return _as_mapping(_read_json(path))


def load_coverage(data_dir: Path = DEFAULT_DATA) -> JsonObject:
    return _as_mapping(_read_json(data_dir / COVERAGE_OUT))


def load_catalogue(data_dir: Path = DEFAULT_DATA) -> catalogue.CatalogueLoad:
    """Read the shared catalogue loader output through the aircraft profile."""
    return catalogue.load(data_dir, profile=catalogue.AIRCRAFT_PROFILE)


# --------------------------------------------------------------------------
# Emitted rows and recorded tokens
# --------------------------------------------------------------------------


def entry_emits(entry: catalogue.CatalogueEntry) -> bool:
    """True when an entry has the identity a runtime row needs.

    The aircraft profile supports ``fixed_wing`` and ``rotary_wing``. A
    vehicle family never emits an aircraft row.
    """
    return bool(
        entry.catalogue_id
        and entry.variant_id
        and entry.vehicle_type in catalogue.AIRCRAFT_VEHICLE_TYPES
    )


def emitted_rows(load: catalogue.CatalogueLoad) -> dict[str, str]:
    """Map each emitted catalogue id to its variant id."""
    rows: dict[str, str] = {}
    for entry in load.entries:
        if entry_emits(entry):
            rows[entry.catalogue_id] = entry.variant_id
    return rows


def recorded_variants(load: catalogue.CatalogueLoad) -> dict[str, set[str]]:
    """Map each air token to the variant ids of its recorded rows.

    A token is ``recorded`` when a runtime row is emitted and a class binding
    exists for the token. The class bindings carry the token, so a binding
    with an empty ``class_token`` still records through the entry.
    """
    emitted = emitted_rows(load)
    recorded: dict[str, set[str]] = {}
    for binding in load.bindings:
        variant = emitted.get(binding.catalogue_id)
        if variant is not None:
            recorded.setdefault(binding.class_token, set()).add(variant)
    return recorded


# --------------------------------------------------------------------------
# Coverage build and guard
# --------------------------------------------------------------------------


def _coverage_row(
    token: str,
    kind: str,
    is_air: bool,
    state: str,
    variant: str | None,
    reason: str,
) -> JsonObject:
    return {
        "class": token,
        "kind": kind,
        "is_air": is_air,
        "state": state,
        "variant": variant,
        "reason": reason,
    }


def build_coverage(
    classes_payload: JsonObject,
    recorded: dict[str, set[str]],
    leads: dict[str, str] | None = None,
) -> JsonObject:
    """Derive one coverage row per inventory token, in inventory order.

    ``recorded`` maps each class-binding token to the variant ids of its
    recorded rows: an emitted runtime row and a class binding. ``leads`` names
    the researched tokens with no recorded row. The four air tokens are in
    scope. Any other token is ``excluded_non_ground``.
    """
    rows: list[object] = []
    for entry in entries(classes_payload):
        token = _as_str(entry.get("class"))
        kind = _as_str(entry.get("kind"))
        if token not in AIR_TOKENS:
            reason = entry.get("exclusion_reason")
            if not isinstance(reason, str) or not reason:
                reason = "non-air token"
            rows.append(_coverage_row(token, kind, False, NON_AIR_STATE, None, reason))
            continue
        variants = sorted(recorded.get(token, set()))
        if variants:
            rows.append(
                _coverage_row(
                    token,
                    kind,
                    True,
                    "recorded",
                    variants[0] if len(variants) == 1 else None,
                    "runtime row emitted and class binding held",
                )
            )
        elif leads is not None and token in leads:
            rows.append(_coverage_row(token, kind, True, "lead", None, leads[token]))
        else:
            rows.append(
                _coverage_row(
                    token,
                    kind,
                    True,
                    AIR_ABSENT_STATE,
                    None,
                    "no emitted runtime row and no class binding held",
                )
            )
    return {"schema": COVERAGE_SCHEMA, "tokens": rows}


def coverage_errors(
    classes_payload: JsonObject,
    coverage_payload: object,
    recorded: dict[str, set[str]],
) -> list[str]:
    """Return every coverage contract error. An empty list is a clean guard."""
    coverage = _as_mapping_or_none(coverage_payload)
    if coverage is None:
        return ["coverage: must be an object"]
    errors: list[str] = []
    if coverage.get("schema") != COVERAGE_SCHEMA:
        errors.append(f"coverage: schema must be {COVERAGE_SCHEMA}")

    raw_rows = _as_sequence_or_none(coverage.get("tokens"))
    if raw_rows is None:
        return errors + ["coverage: tokens must be an array"]

    known: dict[str, JsonObject] = {}
    for entry in entries(classes_payload):
        token = entry.get("class")
        if isinstance(token, str) and token:
            known[token] = entry

    by_token: dict[str, JsonObject] = {}
    for raw in _as_sequence(raw_rows):
        row = _as_mapping_or_none(raw)
        if row is None:
            errors.append("coverage row: must be an object")
            continue
        token = row.get("class")
        if not isinstance(token, str) or not token:
            errors.append("coverage row: token is required")
            continue
        if token in by_token:
            errors.append(f"coverage token {token}: duplicate entry")
        by_token[token] = row

    for token in known:
        if token not in by_token:
            errors.append(
                f"coverage token {token}: no entry, every inventory token needs a state"
            )
    for token in by_token:
        if token not in known:
            errors.append(f"coverage token {token}: not in the class inventory")

    for token, entry in known.items():
        row = by_token.get(token)
        if row is None:
            continue
        state = row.get("state")
        if state not in COVERAGE_STATES:
            errors.append(
                f"coverage token {token}: state {state!r} is not a known state"
            )
            continue
        if token not in AIR_TOKENS:
            if state != NON_AIR_STATE:
                errors.append(
                    f"coverage token {token}: non-air token must be {NON_AIR_STATE}"
                )
            if not row.get("reason"):
                errors.append(f"coverage token {token}: non-air token needs a reason")
            continue
        if state == NON_AIR_STATE:
            errors.append(
                f"coverage token {token}: air token cannot be {NON_AIR_STATE}"
            )
            continue
        variants = recorded.get(token, set())
        if state == "recorded":
            if len(variants) != 1:
                errors.append(
                    f"coverage token {token}: recorded without an emitted row and binding"
                )
                continue
            if row.get("variant") not in variants:
                errors.append(
                    f"coverage token {token}: recorded variant is not the held variant"
                )
        else:
            if variants:
                errors.append(
                    f"coverage token {token}: state {state} hides a recorded row"
                )
            if not row.get("reason"):
                errors.append(f"coverage token {token}: {state} token needs a reason")
    return errors


# --------------------------------------------------------------------------
# Renderers
# --------------------------------------------------------------------------


def render_coverage(payload: JsonObject) -> str:
    """Return the exact on-disk text for the coverage payload."""
    return json.dumps(payload, indent=2) + "\n"


def _coverage_counts(coverage: JsonObject) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in entries(coverage):
        state = row.get("state")
        if isinstance(state, str):
            counts[state] += 1
    return counts


def _mapped_entries(token: str, load: catalogue.CatalogueLoad) -> list[str]:
    """Return the catalogue ids tied to one token, sorted and unique."""
    owners: set[str] = set()
    for entry in load.entries:
        if entry.class_token == token:
            owners.add(entry.catalogue_id)
    for binding in load.bindings:
        if binding.class_token == token:
            owners.add(binding.catalogue_id)
    return sorted(owners)


def build_coverage_report(
    classes: JsonObject,
    coverage: JsonObject,
    load: catalogue.CatalogueLoad,
) -> str:
    """Render data/aircraft/COVERAGE_AUDIT.md."""
    rows = entries(coverage)
    counts = _coverage_counts(coverage)
    air = [row for row in rows if row.get("is_air") is True]
    excluded = [row for row in rows if row.get("is_air") is not True]
    recorded = counts.get("recorded", 0)

    lines = [
        "# Aircraft coverage audit",
        "",
        "Generated by `tools/validation/gen_aircraft_coverage.py`. Do not edit",
        "by hand. The class inventory is `data/vehicle/classes.json`.",
        "",
        "A token is `recorded` only when a runtime row is emitted for an entry",
        "and a class binding exists for the token. A researched candidate",
        "with no recorded row is `lead`. An air token with no lead is",
        "`no_source`. A non-air token is `excluded_non_ground`. A token",
        "never leaves the inventory in silence.",
        "",
        f"- Tokens: {len(rows)}",
        f"- Air tokens: {len(air)}",
        f"- recorded: {counts.get('recorded', 0)}",
        f"- lead: {counts.get('lead', 0)}",
        f"- no_source: {counts.get('no_source', 0)}",
        f"- excluded_non_ground: {counts.get('excluded_non_ground', 0)}",
        f"- Runtime rows: {recorded}",
        "",
        "## Air tokens",
        "",
        "| Token | Kind | State | Mapped entries | Runtime row | Reason |",
        "|---|---|---|---|---|---|",
    ]
    for row in air:
        token = str(row.get("class", ""))
        mapped = _mapped_entries(token, load)
        mapped_text = ", ".join(f"`{item}`" for item in mapped) if mapped else "none"
        runtime_row = "yes" if row.get("state") == "recorded" else "no"
        lines.append(
            f"| `{token}` | {row.get('kind', '')} | {row.get('state', '')} | "
            f"{mapped_text} | {runtime_row} | {row.get('reason', '')} |"
        )

    lines += [
        "",
        "## Excluded tokens",
        "",
        "| Token | Reason |",
        "|---|---|",
    ]
    for row in excluded:
        lines.append(f"| `{row.get('class', '')}` | {row.get('reason', '')} |")

    lines.append("")
    return "\n".join(lines)


def build_source_gaps_report(load: catalogue.CatalogueLoad) -> str:
    """Render data/aircraft/SOURCE_GAPS.md."""
    entries_by_id = sorted(load.entries, key=lambda entry: entry.catalogue_id)
    emitted = sum(1 for entry in entries_by_id if entry_emits(entry))
    absent_total = 0
    gap_entries = 0
    for entry in entries_by_id:
        absent = [
            field
            for field in entry.resolved_fields().values()
            if field.grade == "absent"
        ]
        absent_total += len(absent)
        if absent:
            gap_entries += 1

    ready = sum(1 for entry in entries_by_id if entry.runtime_ready)

    lines = [
        "# Aircraft source gaps",
        "",
        "Generated by `tools/validation/gen_aircraft_coverage.py`. Do not edit",
        "by hand.",
        "",
        "Every catalogue entry with a complete identity emits a runtime row. A",
        "runtime field resolves to a held value, a named derivation or a",
        "labelled absent zero. This file lists the resolved provenance of each",
        "row and the next source class for each absent field. A missing field",
        "is a labelled zero, not a refusal.",
        "",
        f"- Catalogue entries: {len(entries_by_id)}",
        f"- Emitted runtime rows: {emitted}",
        f"- Runtime-ready entries: {ready}",
        f"- Entries with an absent runtime field: {gap_entries}",
        f"- Absent fields: {absent_total}",
        "",
    ]

    for entry in entries_by_id:
        resolved = entry.resolved_fields()
        lines += [
            f"## {entry.catalogue_id} - {entry.canonical_name} ({entry.vehicle_type})",
            "",
            f"- Capture: `data/aircraft/catalogue/{entry.source_file}`",
            f"- Required set: {entry.vehicle_type} ({len(resolved)} fields)",
            f"- Runtime row: {'yes' if entry_emits(entry) else 'no'}",
            f"- Runtime-ready: {'yes' if entry.runtime_ready else 'no'}",
            "",
        ]
        if resolved:
            lines += [
                "| Runtime field | Grade | Value | Source | Locator | State |",
                "|---|---|---|---|---|---|",
            ]
            for name, field in resolved.items():
                lines.append(
                    f"| `{name}` | {field.grade} | {field.value} | "
                    f"`{field.source}` | {field.locator} | {field.state} |"
                )
            lines.append("")
        absent = [name for name, field in resolved.items() if field.grade == "absent"]
        if absent:
            lines += [
                "| Absent field | Next source class |",
                "|---|---|",
            ]
            for name in absent:
                source_class = NEXT_SOURCE_CLASS.get(name, DEFAULT_SOURCE_CLASS)
                lines.append(f"| `{name}` | {source_class} |")
            lines.append("")

    if not entries_by_id:
        lines += ["No catalogue entry is held, so no runtime field is absent.", ""]

    return "\n".join(lines)


def build_class_mapping_report(
    classes: JsonObject, load: catalogue.CatalogueLoad
) -> str:
    """Render data/aircraft/CLASS_MAPPING_GAPS.md."""
    air_tokens = [
        _as_str(entry.get("class"))
        for entry in entries(classes)
        if entry.get("class") in AIR_TOKENS
    ]
    bound_tokens = {
        binding.class_token for binding in load.bindings if binding.class_token
    }
    gaps = [token for token in air_tokens if token not in bound_tokens]
    bound_entries = {
        binding.catalogue_id for binding in load.bindings if binding.catalogue_id
    }
    speed_held = 0
    speed_unbound = 0
    for entry in load.entries:
        field = entry.values.get("max_speed_kmh")
        if isinstance(field, dict) and isinstance(field.get("value"), (int, float)):
            speed_held += 1
            if entry.catalogue_id not in bound_entries:
                speed_unbound += 1

    lines = [
        "# Aircraft class mapping gaps",
        "",
        "Generated by `tools/validation/gen_aircraft_coverage.py`. Do not edit",
        "by hand.",
        "",
        "A class binding links one game class to one catalogue entry with its",
        "own identity source and grade. An engine class-table or config source",
        "is a `claimed` binding, not a real-world mapping. This file lists the",
        "bindings held, every air token with no binding, and the held max",
        "speed values that no binding reaches.",
        "",
        f"- Air tokens: {len(air_tokens)}",
        f"- Air tokens with a binding: {len(air_tokens) - len(gaps)}",
        f"- Air tokens without a binding: {len(gaps)}",
        f"- Class bindings: {len(load.bindings)}",
        f"- Catalogue entries holding max_speed_kmh: {speed_held}",
        f"- Of those with no class binding: {speed_unbound}",
        "",
        "## Class binding records",
        "",
        "| Game class | Token | Catalogue entry | Identity source | Grade | Evidence |",
        "|---|---|---|---|---|---|",
    ]
    if load.bindings:
        for binding in load.bindings:
            lines.append(
                f"| `{binding.game_class}` | `{binding.class_token}` | "
                f"`{binding.catalogue_id}` | `{binding.identity_source}` | "
                f"{binding.grade} | {binding.identity_evidence} |"
            )
    else:
        lines.append("| none | none | none | none | none | none |")

    lines += [
        "",
        "## Air tokens without a binding",
        "",
        "| Token | Next source class |",
        "|---|---|",
    ]
    if gaps:
        for token in gaps:
            lines.append(f"| `{token}` | {CLASS_MAP_SOURCE_CLASS} |")
    else:
        lines.append("| none | none |")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Artefacts
# --------------------------------------------------------------------------


def build_artefacts(data_dir: Path) -> dict[str, str]:
    """Build every artefact text from the corpus at ``data_dir``."""
    classes = load_classes()
    load = load_catalogue(data_dir)
    recorded = recorded_variants(load)
    coverage = build_coverage(classes, recorded, LEAD_CANDIDATES)
    return {
        COVERAGE_OUT: render_coverage(coverage),
        COVERAGE_REPORT: build_coverage_report(classes, coverage, load),
        SOURCE_GAPS_REPORT: build_source_gaps_report(load),
        CLASS_MAPPING_REPORT: build_class_mapping_report(classes, load),
    }


def write_all(data_dir: Path = DEFAULT_DATA) -> dict[str, str]:
    """Write every artefact and return the written text by filename."""
    artefacts = build_artefacts(data_dir)
    for name, text in artefacts.items():
        (data_dir / name).write_text(text, encoding="utf-8")
    return artefacts


def check_all(data_dir: Path = DEFAULT_DATA) -> int:
    """Return 0 when every artefact matches a fresh build.

    Check mode writes nothing. A missing or stale artefact returns 1, so a
    stale generated report fails the gate.
    """
    fresh = build_artefacts(data_dir)
    stale: list[str] = []
    for name in ARTEFACTS:
        path = data_dir / name
        if not path.is_file():
            print(f"aircraft coverage: {path} is missing; run the generator")
            stale.append(name)
            continue
        if path.read_text(encoding="utf-8") != fresh[name]:
            print(f"aircraft coverage: {path} is stale; run the generator")
            stale.append(name)
    if stale:
        return 1

    classes = load_classes()
    coverage = _as_mapping(json.loads(fresh[COVERAGE_OUT]))
    rows = entries(coverage)
    counts = _coverage_counts(coverage)
    air = sum(1 for entry in entries(classes) if entry.get("class") in AIR_TOKENS)
    print(
        f"aircraft coverage: {len(rows)} tokens ({air} air), "
        f"recorded {counts.get('recorded', 0)}, lead {counts.get('lead', 0)}, "
        f"no_source {counts.get('no_source', 0)}, "
        f"excluded {counts.get('excluded_non_ground', 0)} -> fresh"
    )
    return 0


def main(argv: list[str]) -> int:
    data_dir = DEFAULT_DATA
    if "--data-dir" in argv:
        index = argv.index("--data-dir")
        if index + 1 < len(argv):
            data_dir = Path(argv[index + 1])
    if "--check" in argv:
        return check_all(data_dir)
    artefacts = write_all(data_dir)
    coverage = _as_mapping(json.loads(artefacts[COVERAGE_OUT]))
    counts = _coverage_counts(coverage)
    load = load_catalogue(data_dir)
    print(
        f"aircraft coverage: {len(entries(coverage))} tokens, "
        f"recorded {counts.get('recorded', 0)}, lead {counts.get('lead', 0)}, "
        f"no_source {counts.get('no_source', 0)}, "
        f"excluded {counts.get('excluded_non_ground', 0)}, "
        f"{len(load.entries)} catalogue entries -> wrote {len(artefacts)} artefacts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
