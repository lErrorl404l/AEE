#!/usr/bin/env python3
"""Validate the concrete class-binding layer.

``data/vehicle/class_bindings.json`` binds one concrete AEE game class to one
held catalogue entry. It is the concrete extension of the class-to-catalogue
map: the class map binds a class token, the binding layer binds the concrete
class that carries the token. A later engine-physics override reads this layer.
The override never copies an engine value. It traces to a held catalogue
source.

One record carries six required fields: ``game_class``, ``class_token``,
``catalogue_id``, ``identity_source``, ``identity_evidence`` and ``grade``.

The gate checks:

  * every ``catalogue_id`` resolves in the catalogue corpus;
  * every ``game_class`` is unique;
  * every ``grade`` is one of the class-map grades the schema defines;
  * every ``identity_source`` resolves in ``data/vehicle/sources.json``;
  * a claimed engine binding names the concrete class token in its evidence;
  * no required field is empty.

Run:  python3 tools/validation/validate_class_bindings.py
Exit: 0 on success, 1 on any binding error.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path

# A package import (tests) and a direct script run both resolve the sibling
# loader. The repository root goes on the path first.
_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

ROOT = _REPO
DEFAULT_DATA = ROOT / "data" / "vehicle"
BINDINGS_NAME = "class_bindings.json"
SOURCES_NAME = "sources.json"

# The six required fields of one record, in schema order.
REQUIRED_FIELDS = (
    "game_class",
    "class_token",
    "catalogue_id",
    "identity_source",
    "identity_evidence",
    "grade",
)

# The class-map grade set per schema section 7. A concrete class binds by the
# same rule as its class token: documented needs a real-world source, claimed
# is an engine class-table or config binding.
GRADES = catalogue.CLASS_MAP_GRADES


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _text(value: object) -> str | None:
    """Return a non-empty string, or None. An empty field is not a value."""
    if isinstance(value, str) and value.strip():
        return value
    return None


def load_bindings(path: Path) -> list[object]:
    """Read the binding file. Raise ValueError when it is not an array."""
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"{path}: class bindings must be a top-level array")
    return list(loaded)


def catalogue_ids(data_dir: Path) -> set[str]:
    """Return every catalogue id in the corpus. The shared loader reads it."""
    load = catalogue.load(data_dir)
    return {entry.catalogue_id for entry in load.entries}


def sources_by_id(data_dir: Path) -> dict[str, dict[str, object]]:
    """Return the source registry keyed by source_id."""
    path = data_dir / SOURCES_NAME
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


def validate_bindings(
    records: Sequence[object],
    catalogue_ids: set[str],
    sources: dict[str, dict[str, object]],
) -> list[str]:
    """Validate the concrete class bindings. Return every error.

    A binding needs a concrete game class, the class token it carries, a
    catalogue entry, a binding source and its evidence. A duplicate class and
    an unresolved catalogue id are errors.
    """
    errors: list[str] = []
    seen_classes: set[str] = set()
    for index, raw in enumerate(records):
        record = _mapping(raw)
        if record is None:
            errors.append(f"class binding[{index}]: must be an object")
            continue

        game_class = _text(record.get("game_class"))
        where = f"class binding {game_class or f'[{index}]'}"

        missing = [
            field for field in REQUIRED_FIELDS if _text(record.get(field)) is None
        ]
        if missing:
            errors.append(
                f"{where}: required field is empty or missing: {', '.join(missing)}"
            )

        if game_class is None:
            pass
        elif game_class in seen_classes:
            errors.append(
                f"{where}: duplicate game_class; one game class binds one catalogue entry"
            )
        seen_classes.add(game_class or f"<none:{index}>")

        cid = _text(record.get("catalogue_id"))
        if cid is not None and cid not in catalogue_ids:
            errors.append(f"{where}: unknown catalogue_id {cid}")

        grade = record.get("grade")
        grade_ok = isinstance(grade, str) and grade in GRADES
        if not grade_ok:
            errors.append(f"{where}: grade must be one of {sorted(GRADES)}")

        source_id = _text(record.get("identity_source"))
        source = sources.get(source_id) if source_id is not None else None
        if source_id is not None and source is None:
            errors.append(f"{where}: unknown identity_source {source_id}")

        if grade_ok and source is not None:
            source_type = source.get("type")
            if source_type in catalogue.ENGINE_MAPPING_SOURCE_TYPES:
                # An engine class table or config binds a concrete class only
                # at grade claimed, and the evidence names the concrete token.
                if grade != "claimed":
                    errors.append(
                        f"{where}: identity_source {source_id} is engine evidence "
                        "and must be graded claimed"
                    )
                else:
                    token = _text(record.get("class_token"))
                    evidence = _text(record.get("identity_evidence"))
                    if token is None:
                        pass
                    elif evidence is None or token not in evidence:
                        errors.append(
                            f"{where}: a claimed engine binding must name the "
                            f"concrete class token {token} in the identity evidence"
                        )
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    paths = list(sys.argv[1:] if argv is None else argv)
    data_dir = DEFAULT_DATA
    if paths:
        if len(paths) != 2 or paths[0] != "--data-dir":
            print("usage: validate_class_bindings.py [--data-dir PATH]")
            return 2
        data_dir = Path(paths[1])

    path = data_dir / BINDINGS_NAME
    try:
        records = load_bindings(path)
        ids = catalogue_ids(data_dir)
        sources = sources_by_id(data_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"class bindings: FAIL\n  cannot read the corpus: {exc}")
        return 1

    errors = validate_bindings(records, ids, sources)
    if errors:
        print("class bindings: FAIL")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"class bindings: {len(records)} concrete classes -> {path} (valid)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
