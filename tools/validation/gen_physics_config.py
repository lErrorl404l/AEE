#!/usr/bin/env python3
"""Generate the engine CfgVehicles maxSpeed override from the vehicle corpus.

The class set and the values come from ``data/vehicle/class_bindings.json``
and the catalogue ``max_speed_kmh`` field. A bound class yields a line only
when its catalogue entry holds that field with a complete held value object.
The generator invents no value and drops no binding it can represent.

The generator reads the immediate real parent of each bound class from
``data/vehicle/class_parents.json``. That cache is a committed generated
artefact: resolve it from the installed game config with
``--resolve-parents --game-root PATH``. The check path never reads the game
install, so the gate stays deterministic in CI.

The emitted shape states the parent:

    class <Parent>;
    class <X>: <Parent> { maxSpeed = v; };

The parent is the immediate real parent and it is forward-declared once.
A reopen that omits the parent invokes the engine Empty syntax and strips
the vanilla class of every inherited property. A forward declaration alone
does not carry the parent, so the child must restate it. The generator
therefore states the parent and never emits a bare class. It fails closed
when a bound class has no resolved parent.

It declares maxSpeed and no other key. ``thermal`` and ``optics`` own
``htMin``, ``htMax``, ``afMax``, ``mfMax``, ``mFact`` and ``tBody``; a
redeclaration here would win and change the thermal model, so the generator
admits no other key.

The generator also writes ``data/physics/config_bindings.json`` as a
generated projection with the same shape the validator reads.

Run:
    python3 tools/validation/gen_physics_config.py
    python3 tools/validation/gen_physics_config.py --check
    python3 tools/validation/gen_physics_config.py --resolve-parents --game-root "/path/to/Arma 3"
Exit 0 when fresh, 1 when stale or missing under --check.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

DEFAULT_CLASS_BINDINGS = REPO / "data" / "vehicle" / "class_bindings.json"
DEFAULT_VEHICLE_DIR = REPO / "data" / "vehicle"
DEFAULT_PARENTS = REPO / "data" / "vehicle" / "class_parents.json"
DEFAULT_PROJECTION = REPO / "data" / "physics" / "config_bindings.json"
DEFAULT_OUT = REPO / "addons" / "mobility" / "generated" / "CfgVehicles.hpp"

# This version emits one config class and one key. The schema admits no other
# pair, so a corpus record outside this pair is an error rather than a silent
# drop: the generator must not lose a binding it cannot represent.
CONFIG_CLASS = "CfgVehicles"
KEY = "maxSpeed"
VALUE_FIELD = "max_speed_kmh"
KEY_UNIT = "km/h"
CONVERSION = "identity"

HEADER = (
    "/* SPDX-License-Identifier: GPL-2.0-or-later */\n"
    "// Generated engine config override. Do not edit by hand.\n"
    "// Regenerate with: python3 tools/validation/gen_physics_config.py\n"
    "//\n"
    "// This is a load-time, global override of vanilla engine config. The\n"
    "// engine reads it when the config loads and config cannot be gated at\n"
    "// runtime, so the PBO is the only off switch.\n"
    "//\n"
    "// Each class restates its immediate real parent, and the parent is\n"
    "// forward-declared once:\n"
    "//\n"
    "//     class <Parent>;\n"
    "//     class <X>: <Parent> { maxSpeed = v; };\n"
    "//\n"
    "// A reopen that omits the parent invokes the engine Empty syntax and\n"
    "// strips the vanilla class of every inherited property. A forward\n"
    "// declaration alone does not carry the parent, so the child restates\n"
    "// it. The generator never emits a bare class.\n"
    "//\n"
    "// It declares maxSpeed and no other key. thermal and optics own htMin,\n"
    "// htMax, afMax, mfMax, mFact and tBody; a redeclaration here would win\n"
    "// and change the thermal model, so only maxSpeed is admitted.\n"
)


@dataclass(frozen=True)
class ParentRecord:
    """One resolved immediate parent with its provenance."""

    parent_class: str
    source_kind: str
    source_locator: str


@dataclass(frozen=True)
class Emission:
    """One corpus binding that holds a value and can be emitted."""

    game_class: str
    parent_class: str
    value: object
    unit: str
    source_id: str
    locator: str
    grade: str


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _text(value: object) -> str | None:
    """Return a non-empty string, or None. An empty field is not a value."""
    if isinstance(value, str) and value.strip():
        return value
    return None


def load_class_bindings(path: Path) -> list[dict[str, object]]:
    """Read the class bindings. Raise ValueError when not a top-level array."""
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"{path}: class bindings must be a top-level array")
    records: list[dict[str, object]] = []
    for index, raw in enumerate(loaded):
        record = _mapping(raw)
        if record is None:
            raise ValueError(f"{path}: binding[{index}] must be an object")
        records.append(record)
    return records


def bound_classes(path: Path) -> list[str]:
    """Return every game class named by the class-binding corpus, sorted."""
    classes: list[str] = []
    for index, record in enumerate(load_class_bindings(path)):
        game_class = _text(record.get("game_class"))
        if game_class is None:
            raise ValueError(f"{path}: binding[{index}] has no game_class")
        classes.append(game_class)
    if len(classes) != len(set(classes)):
        raise ValueError(f"{path}: a game class repeats in the corpus")
    return sorted(classes)


def _corpus_values(
    class_bindings_path: Path, vehicle_dir: Path
) -> dict[str, dict[str, object]]:
    """Return the held maxSpeed fields of the corpus, keyed by game class.

    A bound class whose catalogue entry holds no ``max_speed_kmh`` yields no
    entry here. A held field with an unexpected unit is an error: the engine
    key is documented in km/h and the generator emits no other unit.
    """
    load = catalogue.load(vehicle_dir)
    if load.errors:
        raise ValueError(
            f"{vehicle_dir}: the catalogue does not load: {load.errors[0]}"
        )
    entries = {entry.catalogue_id: entry for entry in load.entries}
    held_by_class: dict[str, dict[str, object]] = {}
    for index, record in enumerate(load_class_bindings(class_bindings_path)):
        where = f"binding[{index}]"
        game_class = _text(record.get("game_class"))
        catalogue_id = _text(record.get("catalogue_id"))
        if game_class is None:
            raise ValueError(f"{where}: game_class must be a non-empty string")
        if catalogue_id is None:
            raise ValueError(f"{where}: catalogue_id must be a non-empty string")
        entry = entries.get(catalogue_id)
        if entry is None:
            raise ValueError(f"{where}: unknown catalogue_id {catalogue_id}")
        held = catalogue.held_value(entry.values, VALUE_FIELD)
        if held is None:
            continue
        unit = _text(held.get("unit"))
        if unit != KEY_UNIT:
            raise ValueError(
                f"{where}: {VALUE_FIELD} is held in {unit}, the key is {KEY_UNIT}"
            )
        source_id = _text(held.get("source"))
        locator = _text(held.get("locator"))
        grade = _text(held.get("grade"))
        if source_id is None or locator is None or grade is None:
            raise ValueError(f"{where}: the held {VALUE_FIELD} value is incomplete")
        held_by_class[game_class] = {
            "value": held.get("value"),
            "source_id": source_id,
            "locator": locator,
            "grade": grade,
        }
    return held_by_class


def _render_value(value: object) -> str:
    """Return the engine literal for a numeric config value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"config value must be a number, got {value!r}")
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return repr(number)


def load_parents(path: Path) -> dict[str, ParentRecord]:
    """Read the resolved-parent cache. Raise ValueError on a malformed file."""
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"{path}: the parent cache must be a top-level array")
    parents: dict[str, ParentRecord] = {}
    for index, raw in enumerate(loaded):
        record = _mapping(raw)
        if record is None:
            raise ValueError(f"{path}: parent[{index}] must be an object")
        game_class = _text(record.get("game_class"))
        parent_class = _text(record.get("parent_class"))
        if game_class is None or parent_class is None:
            raise ValueError(
                f"{path}: parent[{index}] needs game_class and parent_class"
            )
        if game_class in parents:
            raise ValueError(f"{path}: duplicate parent for {game_class}")
        parents[game_class] = ParentRecord(
            parent_class=parent_class,
            source_kind=_text(record.get("source_kind")) or "",
            source_locator=_text(record.get("source_locator")) or "",
        )
    return parents


def build(
    class_bindings_path: Path,
    vehicle_dir: Path,
    parents_path: Path,
) -> list[Emission]:
    """Return the ordered emissions, one per bound class that holds a value.

    A bound class with a held value and no resolved parent is an error. The
    generator emits no bare class, so it stops rather than guess a parent.
    """
    held_by_class = _corpus_values(class_bindings_path, vehicle_dir)
    parents = load_parents(parents_path)
    emissions: list[Emission] = []
    for game_class in sorted(held_by_class):
        held = held_by_class[game_class]
        parent = parents.get(game_class)
        if parent is None:
            raise ValueError(
                f"{game_class}: no resolved parent in {parents_path}; "
                "run --resolve-parents against the game install"
            )
        emissions.append(
            Emission(
                game_class=game_class,
                parent_class=parent.parent_class,
                value=held["value"],
                unit=KEY_UNIT,
                source_id=str(held["source_id"]),
                locator=str(held["locator"]),
                grade=str(held["grade"]),
            )
        )
    return emissions


def render(emissions: Sequence[Emission]) -> str:
    """Return the exact on-disk text for the emitted bindings."""
    parents = sorted({emission.parent_class for emission in emissions})
    lines = [HEADER, f"class {CONFIG_CLASS} {{"]
    for parent in parents:
        lines.append(f"    class {parent};")
    if parents and emissions:
        lines.append("")
    for emission in emissions:
        lines.append(f"    class {emission.game_class}: {emission.parent_class} {{")
        lines.append(f"        {KEY} = {_render_value(emission.value)};")
        lines.append("    };")
    lines.append("};")
    return "\n".join(lines) + "\n"


def projection_records(emissions: Sequence[Emission]) -> list[dict[str, object]]:
    """Return the validator projection of the emissions."""
    return [
        {
            "game_class": emission.game_class,
            "config_class": CONFIG_CLASS,
            "key": KEY,
            "value": emission.value,
            "unit": emission.unit,
            "value_source": {
                "source_id": emission.source_id,
                "locator": emission.locator,
                "field": VALUE_FIELD,
            },
            "conversion": CONVERSION,
            "grade": emission.grade,
        }
        for emission in emissions
    ]


def render_projection(emissions: Sequence[Emission]) -> str:
    """Return the exact on-disk text of the validator projection."""
    return json.dumps(projection_records(emissions), indent=2) + "\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_outputs(
    class_bindings_path: Path,
    vehicle_dir: Path,
    parents_path: Path,
    out: Path,
    projection: Path,
) -> int:
    """Write the header and the projection. Return the binding count."""
    emissions = build(class_bindings_path, vehicle_dir, parents_path)
    _write(out, render(emissions))
    _write(projection, render_projection(emissions))
    return len(emissions)


def _fresh(path: Path, text: str, label: str) -> bool:
    if not path.is_file():
        print(f"physics config override: {label} {path} is missing; run the generator")
        return False
    if path.read_text(encoding="utf-8") != text:
        print(f"physics config override: {label} {path} is stale; run the generator")
        return False
    return True


def check_config(
    class_bindings_path: Path,
    vehicle_dir: Path,
    parents_path: Path,
    out: Path,
    projection: Path,
) -> int:
    """Return 0 when both committed artefacts match a fresh build.

    Check mode writes nothing. A missing or stale file returns 1, so a
    stale generated override fails the gate.
    """
    try:
        emissions = build(class_bindings_path, vehicle_dir, parents_path)
        text = render(emissions)
        expected = render_projection(emissions)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"physics config override: cannot build from the corpus: {exc}")
        return 1
    if not _fresh(out, text, "override"):
        return 1
    if not _fresh(projection, expected, "projection"):
        return 1
    print(
        f"physics config override: {len(emissions)} bindings -> {out}, "
        f"{projection} (fresh)"
    )
    return 0


# --- Parent resolution against the installed game config ----------------

_CLASS_DECL = r"(?<![\w])class\s+%s\s*:\s*([A-Za-z_]\w*)"

# Addons that hold content or references rather than the class tree. They
# are searched last, so a real addon PBO answers first. This orders a search
# only. It is never a parent value.
_REFERENCE_ONLY = (
    "missions",
    "campaign",
    "characters",
    "data_",
    "music",
    "sounds",
    "dubbing",
    "map",
    "structures",
)


def _first_parent(text: str, game_class: str) -> tuple[str, int] | None:
    """Return the (parent, line) of a class declaration, or None."""
    pattern = re.compile(_CLASS_DECL % re.escape(game_class))
    match = pattern.search(text)
    if match is None:
        return None
    return match.group(1), text.count("\n", 0, match.start()) + 1


def _contains(path: Path, needle: bytes) -> bool:
    """True when the file holds the byte string. Reads in bounded chunks."""
    overlap = len(needle) - 1
    tail = b""
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1 << 22)
            if not chunk:
                return False
            if needle in tail + chunk:
                return True
            tail = chunk[-overlap:] if overlap > 0 else b""


def _pbo_rank(path: Path) -> tuple[int, str]:
    name = path.name.lower()
    return (1 if name.startswith(_REFERENCE_ONLY) else 0, path.as_posix())


def _run_hemtt(argv: list[str]) -> None:
    try:
        result = subprocess.run(
            ["hemtt", *argv], capture_output=True, text=True, check=False
        )
    except FileNotFoundError as exc:
        raise ValueError(
            "hemtt is required to resolve parents from a game install"
        ) from exc
    if result.returncode != 0:
        raise ValueError(f"hemtt {' '.join(argv)} failed: {result.stderr.strip()}")


def _unpacked_configs(unpacked: Path) -> list[Path]:
    """Return the derapified config.cpp paths under an unpacked PBO."""
    configs: list[Path] = []
    for binary in sorted(unpacked.rglob("config.bin")):
        target = binary.with_suffix(".cpp")
        _run_hemtt(
            ["utils", "config", "derapify", "-f", "cpp", str(binary), str(target)]
        )
        configs.append(target)
    for existing in sorted(unpacked.rglob("config.cpp")):
        if existing not in configs:
            configs.append(existing)
    return configs


def resolve_parents(
    game_root: Path,
    class_bindings_path: Path,
    vehicle_dir: Path,
) -> list[dict[str, object]]:
    """Resolve every bound class's immediate parent from the game install.

    The loose ``config.cpp`` files answer first. A class that is only in a
    PBO is unpacked and derapified. A bound class that cannot be resolved is
    an error: the generator must not guess a parent.
    """
    if not game_root.is_dir():
        raise ValueError(f"{game_root}: the game root is not a directory")
    wanted = bound_classes(class_bindings_path)
    remaining = set(wanted)
    resolved: dict[str, dict[str, object]] = {}

    for path in sorted(game_root.rglob("config.cpp")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for game_class in sorted(remaining):
            hit = _first_parent(text, game_class)
            if hit is None:
                continue
            parent, line = hit
            resolved[game_class] = {
                "game_class": game_class,
                "parent_class": parent,
                "source_kind": "game_config",
                "source_locator": f"{path.relative_to(game_root).as_posix()}:{line}",
            }
            remaining.discard(game_class)
        if not remaining:
            return [resolved[game_class] for game_class in wanted]

    needles = {game_class: game_class.encode() for game_class in remaining}
    for pbo in sorted(game_root.rglob("*.pbo"), key=_pbo_rank):
        present = [
            game_class
            for game_class, needle in needles.items()
            if _contains(pbo, needle)
        ]
        if not present:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            unpacked = Path(tmp) / "unpacked"
            _run_hemtt(["utils", "pbo", "unpack", str(pbo), str(unpacked)])
            for config in _unpacked_configs(unpacked):
                text = config.read_text(encoding="utf-8", errors="replace")
                for game_class in sorted(present):
                    if game_class not in remaining:
                        continue
                    hit = _first_parent(text, game_class)
                    if hit is None:
                        continue
                    parent, line = hit
                    resolved[game_class] = {
                        "game_class": game_class,
                        "parent_class": parent,
                        "source_kind": "pbo_config",
                        "source_locator": (
                            f"{pbo.relative_to(game_root).as_posix()} > "
                            f"{config.relative_to(unpacked).as_posix()}:{line}"
                        ),
                    }
                    remaining.discard(game_class)
        if not remaining:
            break

    if remaining:
        raise ValueError(
            "could not resolve an immediate parent for: " + ", ".join(sorted(remaining))
        )
    return [resolved[game_class] for game_class in wanted]


def write_parents(
    game_root: Path,
    class_bindings_path: Path,
    vehicle_dir: Path,
    parents_path: Path,
) -> int:
    """Resolve the parents and write the cache. Return the record count."""
    records = resolve_parents(game_root, class_bindings_path, vehicle_dir)
    _write(parents_path, json.dumps(records, indent=2) + "\n")
    return len(records)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the engine CfgVehicles override."
    )
    parser.add_argument("--class-bindings", type=Path, default=DEFAULT_CLASS_BINDINGS)
    parser.add_argument("--vehicle-dir", type=Path, default=DEFAULT_VEHICLE_DIR)
    parser.add_argument("--parents", type=Path, default=DEFAULT_PARENTS)
    parser.add_argument("--projection", type=Path, default=DEFAULT_PROJECTION)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed artefacts are fresh. Write nothing.",
    )
    parser.add_argument(
        "--resolve-parents",
        action="store_true",
        help="Resolve the bound class parents from the game install.",
    )
    parser.add_argument(
        "--game-root",
        type=Path,
        help="Path to the installed Arma 3 directory for --resolve-parents.",
    )
    args = parser.parse_args(argv)

    if args.resolve_parents:
        if args.game_root is None:
            print("physics config override: --resolve-parents needs --game-root")
            return 2
        try:
            count = write_parents(
                args.game_root,
                args.class_bindings,
                args.vehicle_dir,
                args.parents,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"physics config override: cannot resolve parents: {exc}")
            return 1
        print(f"physics config parents: {count} records -> {args.parents}")
        return 0

    if args.check:
        return check_config(
            args.class_bindings,
            args.vehicle_dir,
            args.parents,
            args.out,
            args.projection,
        )
    try:
        count = write_outputs(
            args.class_bindings,
            args.vehicle_dir,
            args.parents,
            args.out,
            args.projection,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"physics config override: cannot build from the corpus: {exc}")
        return 1
    print(f"physics config override: {count} bindings -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
