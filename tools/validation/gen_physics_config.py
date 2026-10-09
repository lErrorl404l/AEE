#!/usr/bin/env python3
"""Generate the engine CfgVehicles override from the vehicle corpus.

One CfgVehicles block carries the land keys and, only when the build-time
gate passes, the aircraft fuel key:

  * ``maxSpeed`` from the held catalogue ``max_speed_kmh`` field;
  * ``mass`` as a CALIBRATED scale of a held real mass;
  * ``fuelCapacity`` from the held aircraft catalogue ``fuel_capacity`` field.

The land keys are pre-existing and NOT identity-derived: maxSpeed comes from
the held catalogue and mass from the approved mass calibration. The gate never
retro-applies to them, and their output is unchanged by this version.

The aircraft key is gated at BUILD TIME by ``emit_key``: a key is emitted only
when the class identity grade (``data/aircraft/class_bindings.json``) AND the
value grade (the held catalogue value object) are both ``documented``. Config
is load-time and global, so the build-time predicate is the only gate: a
runtime setting cannot gate it and the PBO is the only off switch. A
``claimed`` identity, a missing grade or any other grade emits no key and the
class is recorded as a lead.

PRODUCTION EMITS ZERO NEW KEYS TODAY. Every aircraft class binding is
``claimed``, so fail-closed means no ``fuelCapacity`` key ships yet. That is
the gate working, not a broken generator. The emission path is proved by the
sentinel fixture in ``tools/tests/test_aircraft_systems.py``.

The class set is ``data/vehicle/class_bindings.json``. The maxSpeed value
comes from the catalogue ``max_speed_kmh`` field. The mass value comes from
the approved calibration ``data/physics/mass_calibration.json``:

    mass = real_analogue_mass_kg / fit.scale

The engine's own ``getMass`` and config ``mass`` are engine tuning values and
are never a value source. The fit is a calibration scale over a held real
mass.

The generator reads the immediate real parent of each bound class from
``data/vehicle/class_parents.json``. That cache is a committed generated
artefact: resolve it from the installed game config with
``--resolve-parents --game-root PATH``. The check path never reads the game
install, so the gate stays deterministic in CI.

The emitted shape states the parent:

    class <Parent>;
    class <X>: <Parent> { maxSpeed = v; mass = w; };

The parent is the immediate real parent and it is forward-declared once.
A reopen that omits the parent invokes the engine Empty syntax and strips
the vanilla class of every inherited property. A forward declaration alone
does not carry the parent, so the child must restate it. The generator
therefore states the parent and never emits a bare class. It fails closed
when a bound class has no resolved parent.

One block carries both keys. The engine lint rejects a second CfgVehicles
block in the same addon, so the two keys share one render.

It declares maxSpeed and mass and no other key. ``thermal`` and ``optics``
own ``htMin``, ``htMax``, ``afMax``, ``mfMax``, ``mFact`` and ``tBody``; a
redeclaration here would win and change the thermal model, so the generator
admits no other key.

The generator also writes ``data/physics/config_bindings.json`` as a
generated projection of the maxSpeed bindings, with the shape the validator
reads.

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
DEFAULT_CALIBRATION = REPO / "data" / "physics" / "mass_calibration.json"
DEFAULT_PROJECTION = REPO / "data" / "physics" / "config_bindings.json"
DEFAULT_OUT = REPO / "addons" / "mobility" / "generated" / "CfgVehicles.hpp"
DEFAULT_AIRCRAFT_CLASS_BINDINGS = REPO / "data" / "aircraft" / "class_bindings.json"
DEFAULT_AIRCRAFT_DIR = REPO / "data" / "aircraft"
DEFAULT_AIRCRAFT_PARENTS = REPO / "data" / "aircraft" / "class_parents.json"

# This version emits one config class. The land pair is un-gated: the schema
# admits no other land pair, so a corpus record outside this pair is an error
# rather than a silent drop. The aircraft key is gated by ``emit_key``.
CONFIG_CLASS = "CfgVehicles"
KEY = "maxSpeed"
MASS_KEY = "mass"
VALUE_FIELD = "max_speed_kmh"
KEY_UNIT = "km/h"
CONVERSION = "identity"
MASS_SCHEMA = "aee.physics.mass_calibration/1"

# The aircraft key. ``fuel_capacity`` is held in litres and projects to the
# engine ``fuelCapacity`` key by the identity conversion.
AIRCRAFT_KEY = "fuelCapacity"
AIRCRAFT_VALUE_FIELD = "fuel_capacity"
AIRCRAFT_KEY_UNIT = "L"

# The grade the build-time gate requires on both the class identity and the
# held value. No other grade emits a key.
DOCUMENTED = "documented"

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
    "//     class <X>: <Parent> { maxSpeed = v; mass = w; };\n"
    "//\n"
    "// A reopen that omits the parent invokes the engine Empty syntax and\n"
    "// strips the vanilla class of every inherited property. A forward\n"
    "// declaration alone does not carry the parent, so the child restates\n"
    "// it. The generator never emits a bare class.\n"
    "//\n"
    "// It declares maxSpeed and mass for the pre-existing land classes. Those\n"
    "// keys are NOT identity-derived and the aircraft gate never\n"
    "// retro-applies to them. thermal and optics own htMin, htMax, afMax,\n"
    "// mfMax, mFact and tBody; a redeclaration here would win and change the\n"
    "// thermal model, so no thermal key is admitted. Each mass is a\n"
    "// calibrated scale of a held real mass, never a copied engine number,\n"
    "// from data/physics/mass_calibration.json.\n"
    "//\n"
    "// The aircraft fuel key is gated at BUILD TIME: it is emitted only\n"
    "// when the class identity grade and the held value grade are both\n"
    "// documented. Config is load-time and global, so the build-time\n"
    "// predicate is the only gate. Every aircraft class binding is claimed\n"
    "// today, so NO aircraft key ships yet. That is the gate working, not a\n"
    "// broken generator.\n"
    "//\n"
    "// One block carries every key: the engine lint rejects a second\n"
    "// CfgVehicles block in the same addon.\n"
)


@dataclass(frozen=True)
class ParentRecord:
    """One resolved immediate parent with its provenance."""

    parent_class: str
    source_kind: str
    source_locator: str


@dataclass(frozen=True)
class Emission:
    """One corpus binding that holds a maxSpeed value and can be emitted."""

    game_class: str
    parent_class: str
    value: object
    unit: str
    source_id: str
    locator: str
    grade: str


@dataclass(frozen=True)
class AircraftEmission:
    """One aircraft binding that passes the build-time gate and can be emitted."""

    game_class: str
    parent_class: str
    value: object
    unit: str
    source_id: str
    locator: str
    grade: str


@dataclass(frozen=True)
class MassCalibration:
    """The approved calibration: one fitted scale and the held mass per class."""

    scale: float
    round_to: int
    held_kg: dict[str, float]


@dataclass(frozen=True)
class ClassBinding:
    """One bare class body with the keys it holds."""

    game_class: str
    parent_class: str
    max_speed: object | None
    mass: float | None
    fuel_capacity: object | None = None


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _text(value: object) -> str | None:
    """Return a non-empty string, or None. An empty field is not a value."""
    if isinstance(value, str) and value.strip():
        return value
    return None


def _number(value: object) -> float | None:
    """Return a real number, rejecting a bool and a numeric string."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def emit_key(identity_grade: object, value_grade: object) -> bool:
    """True only when the class identity and the value grade are both documented.

    Config is load-time and global, so the build-time predicate is the only
    gate. A ``claimed`` identity, a missing grade or any other grade emits no
    key.
    """
    return identity_grade == DOCUMENTED and value_grade == DOCUMENTED


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


def _parents_from_records(loaded: object, path: Path) -> dict[str, ParentRecord]:
    """Parse the parent records. Raise ValueError on a malformed array."""
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


def load_parents(path: Path) -> dict[str, ParentRecord]:
    """Read the resolved-parent cache. Raise ValueError on a malformed file."""
    return _parents_from_records(json.loads(path.read_text(encoding="utf-8")), path)


def load_aircraft_parents(path: Path) -> dict[str, ParentRecord]:
    """Read the aircraft parent cache.

    The committed cache is ``{}`` when no game install resolved a parent, so
    an empty JSON object means no parents. Any other shape is the vehicle
    cache shape and parses the same way.
    """
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict) and not loaded:
        return {}
    return _parents_from_records(loaded, path)


def load_mass_calibration(path: Path) -> MassCalibration:
    """Read the approved mass calibration. Raise ValueError when unusable.

    An unapproved calibration is an error: the mass override waits on the
    operator approval, so the generator must not consume the fit before it is
    granted. A class with no held real mass is an error too, because the
    generator must not invent a mass.
    """
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    payload = _mapping(loaded)
    if payload is None:
        raise ValueError(f"{path}: the calibration must be a JSON object")
    if payload.get("schema") != MASS_SCHEMA:
        raise ValueError(f"{path}: schema must be {MASS_SCHEMA}")
    if payload.get("approved") is not True:
        raise ValueError(
            f"{path}: the calibration is not approved; the mass override waits "
            "on the operator approval"
        )
    fit = _mapping(payload.get("fit"))
    if fit is None:
        raise ValueError(f"{path}: fit must be an object")
    scale = _number(fit.get("scale"))
    if scale is None or scale <= 0:
        raise ValueError(f"{path}: fit.scale must be positive")
    round_value = _number(fit.get("round"))
    round_to = int(round_value) if round_value is not None else 6
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: rows must be a non-empty array")
    held: dict[str, float] = {}
    for index, raw in enumerate(rows):
        row = _mapping(raw)
        if row is None:
            raise ValueError(f"{path}: rows[{index}] must be an object")
        game_class = _text(row.get("game_class"))
        if game_class is None:
            raise ValueError(f"{path}: rows[{index}].game_class must be a string")
        if game_class in held:
            raise ValueError(f"{path}: rows[{index}] repeats {game_class}")
        mass = _number(row.get("real_analogue_mass_kg"))
        if mass is None or mass <= 0:
            raise ValueError(
                f"{path}: rows[{index}].real_analogue_mass_kg must be positive"
            )
        held[game_class] = mass
    return MassCalibration(scale=scale, round_to=round_to, held_kg=held)


def build(
    class_bindings_path: Path,
    vehicle_dir: Path,
    parents_path: Path,
) -> list[Emission]:
    """Return the ordered maxSpeed emissions, one per bound class with a value.

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


def build_class_bindings(
    class_bindings_path: Path,
    vehicle_dir: Path,
    parents_path: Path,
    calibration_path: Path,
) -> list[ClassBinding]:
    """Return the ordered class bodies, one per bound class.

    Every bound class carries a calibrated mass: the mass override covers the
    whole class-binding corpus. A bound class with no held real mass in the
    approved calibration is an error, because the generator emits no invented
    mass. A bound class with no resolved parent is an error, because the
    generator emits no bare class. A class that also holds a maxSpeed value
    carries both keys in its one body.
    """
    max_speed = {
        emission.game_class: emission
        for emission in build(class_bindings_path, vehicle_dir, parents_path)
    }
    calibration = load_mass_calibration(calibration_path)
    parents = load_parents(parents_path)
    bindings: list[ClassBinding] = []
    for game_class in bound_classes(class_bindings_path):
        held_kg = calibration.held_kg.get(game_class)
        if held_kg is None:
            raise ValueError(
                f"{game_class}: no held real mass in {calibration_path}; "
                "the mass override cannot emit it"
            )
        parent = parents.get(game_class)
        if parent is None:
            raise ValueError(
                f"{game_class}: no resolved parent in {parents_path}; "
                "run --resolve-parents against the game install"
            )
        emission = max_speed.get(game_class)
        value = round(held_kg / calibration.scale, calibration.round_to)
        bindings.append(
            ClassBinding(
                game_class=game_class,
                parent_class=parent.parent_class,
                max_speed=emission.value if emission is not None else None,
                mass=value,
            )
        )
    return bindings


def build_aircraft_emissions(
    class_bindings_path: Path,
    aircraft_dir: Path,
    parents_path: Path,
) -> tuple[list[AircraftEmission], list[str]]:
    """Return the gate-passing aircraft fuel emissions and the rejected leads.

    The class identity grade comes from the aircraft class binding and the
    value grade from the held catalogue value object. ``emit_key`` admits a
    key only when both are ``documented``. A class that fails the predicate is
    a lead: it emits no key, needs no resolved parent and the build does not
    fail for it. A gate-passing class with no resolved parent is an error,
    because the generator emits no bare class.
    """
    load = catalogue.load(aircraft_dir, profile=catalogue.AIRCRAFT_PROFILE)
    entries = {entry.catalogue_id: entry for entry in load.entries}
    parents = load_aircraft_parents(parents_path)
    emissions: list[AircraftEmission] = []
    leads: list[str] = []
    for index, record in enumerate(load_class_bindings(class_bindings_path)):
        where = f"binding[{index}]"
        game_class = _text(record.get("game_class"))
        catalogue_id = _text(record.get("catalogue_id"))
        if game_class is None:
            raise ValueError(f"{where}: game_class must be a non-empty string")
        if catalogue_id is None:
            raise ValueError(f"{where}: catalogue_id must be a non-empty string")
        entry = entries.get(catalogue_id)
        held = (
            catalogue.held_value(entry.values, AIRCRAFT_VALUE_FIELD)
            if entry is not None
            else None
        )
        identity_grade = record.get("grade")
        value_grade = held.get("grade") if held is not None else None
        if not emit_key(identity_grade, value_grade):
            leads.append(game_class)
            continue
        assert held is not None
        unit = _text(held.get("unit"))
        if unit != AIRCRAFT_KEY_UNIT:
            raise ValueError(
                f"{where}: {AIRCRAFT_VALUE_FIELD} is held in {unit}, "
                f"the key is {AIRCRAFT_KEY_UNIT}"
            )
        source_id = _text(held.get("source"))
        locator = _text(held.get("locator"))
        if source_id is None or locator is None:
            raise ValueError(
                f"{where}: the held {AIRCRAFT_VALUE_FIELD} value is incomplete"
            )
        parent = parents.get(game_class)
        if parent is None:
            raise ValueError(
                f"{game_class}: no resolved parent in {parents_path}; "
                "run --resolve-aircraft-parents against the game install"
            )
        emissions.append(
            AircraftEmission(
                game_class=game_class,
                parent_class=parent.parent_class,
                value=held.get("value"),
                unit=AIRCRAFT_KEY_UNIT,
                source_id=source_id,
                locator=locator,
                grade=str(value_grade),
            )
        )
    return emissions, leads


def build_all_bindings(
    class_bindings_path: Path,
    vehicle_dir: Path,
    parents_path: Path,
    calibration_path: Path,
    aircraft_class_bindings: Path,
    aircraft_dir: Path,
    aircraft_parents: Path,
) -> tuple[list[ClassBinding], list[str]]:
    """Return the one-block class bodies and the aircraft leads.

    The land bodies are un-gated and their output is unchanged. Each
    gate-passing aircraft binding appends one body that restates its parent
    beside the land bodies in the same block. A rejected aircraft binding
    emits nothing.
    """
    bindings = build_class_bindings(
        class_bindings_path, vehicle_dir, parents_path, calibration_path
    )
    emissions, leads = build_aircraft_emissions(
        aircraft_class_bindings, aircraft_dir, aircraft_parents
    )
    for emission in sorted(emissions, key=lambda item: item.game_class):
        bindings.append(
            ClassBinding(
                game_class=emission.game_class,
                parent_class=emission.parent_class,
                max_speed=None,
                mass=None,
                fuel_capacity=emission.value,
            )
        )
    return bindings, leads


def render_bindings(bindings: Sequence[ClassBinding]) -> str:
    """Return the exact on-disk text for the emitted class bodies."""
    parents = sorted({binding.parent_class for binding in bindings})
    lines = [HEADER, f"class {CONFIG_CLASS} {{"]
    for parent in parents:
        lines.append(f"    class {parent};")
    if parents and bindings:
        lines.append("")
    for binding in bindings:
        lines.append(f"    class {binding.game_class}: {binding.parent_class} {{")
        if binding.max_speed is not None:
            lines.append(f"        {KEY} = {_render_value(binding.max_speed)};")
        if binding.mass is not None:
            lines.append(f"        {MASS_KEY} = {_render_value(binding.mass)};")
        if binding.fuel_capacity is not None:
            lines.append(
                f"        {AIRCRAFT_KEY} = {_render_value(binding.fuel_capacity)};"
            )
        lines.append("    };")
    lines.append("};")
    return "\n".join(lines) + "\n"


def projection_records(emissions: Sequence[Emission]) -> list[dict[str, object]]:
    """Return the validator projection of the maxSpeed emissions."""
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
    calibration_path: Path = DEFAULT_CALIBRATION,
    aircraft_class_bindings: Path = DEFAULT_AIRCRAFT_CLASS_BINDINGS,
    aircraft_dir: Path = DEFAULT_AIRCRAFT_DIR,
    aircraft_parents: Path = DEFAULT_AIRCRAFT_PARENTS,
) -> int:
    """Write the header and the projection. Return the class-body count."""
    bindings, _leads = build_all_bindings(
        class_bindings_path,
        vehicle_dir,
        parents_path,
        calibration_path,
        aircraft_class_bindings,
        aircraft_dir,
        aircraft_parents,
    )
    _write(out, render_bindings(bindings))
    _write(
        projection,
        render_projection(build(class_bindings_path, vehicle_dir, parents_path)),
    )
    return len(bindings)


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
    calibration_path: Path = DEFAULT_CALIBRATION,
    aircraft_class_bindings: Path = DEFAULT_AIRCRAFT_CLASS_BINDINGS,
    aircraft_dir: Path = DEFAULT_AIRCRAFT_DIR,
    aircraft_parents: Path = DEFAULT_AIRCRAFT_PARENTS,
) -> int:
    """Return 0 when both committed artefacts match a fresh build.

    Check mode writes nothing. A missing or stale file returns 1, so a stale
    generated override fails the gate.
    """
    try:
        bindings, _leads = build_all_bindings(
            class_bindings_path,
            vehicle_dir,
            parents_path,
            calibration_path,
            aircraft_class_bindings,
            aircraft_dir,
            aircraft_parents,
        )
        text = render_bindings(bindings)
        expected = render_projection(
            build(class_bindings_path, vehicle_dir, parents_path)
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"physics config override: cannot build from the corpus: {exc}")
        return 1
    if not _fresh(out, text, "override"):
        return 1
    if not _fresh(projection, expected, "projection"):
        return 1
    print(
        f"physics config override: {len(bindings)} class bodies -> {out}, "
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


def write_aircraft_parents(
    game_root: Path,
    class_bindings_path: Path,
    aircraft_dir: Path,
    parents_path: Path,
) -> int:
    """Resolve the aircraft parents and write the cache. Return the count."""
    records = resolve_parents(game_root, class_bindings_path, aircraft_dir)
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
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--aircraft-class-bindings",
        type=Path,
        default=DEFAULT_AIRCRAFT_CLASS_BINDINGS,
    )
    parser.add_argument("--aircraft-dir", type=Path, default=DEFAULT_AIRCRAFT_DIR)
    parser.add_argument(
        "--aircraft-parents", type=Path, default=DEFAULT_AIRCRAFT_PARENTS
    )
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
        "--resolve-aircraft-parents",
        action="store_true",
        help="Resolve the aircraft class parents from the game install.",
    )
    parser.add_argument(
        "--game-root",
        type=Path,
        help="Path to the installed Arma 3 directory for --resolve-parents.",
    )
    args = parser.parse_args(argv)

    if args.resolve_parents or args.resolve_aircraft_parents:
        if args.game_root is None:
            print("physics config override: resolving parents needs --game-root")
            return 2
        try:
            if args.resolve_aircraft_parents:
                count = write_aircraft_parents(
                    args.game_root,
                    args.aircraft_class_bindings,
                    args.aircraft_dir,
                    args.aircraft_parents,
                )
                label = "aircraft parents"
                target = args.aircraft_parents
            else:
                count = write_parents(
                    args.game_root,
                    args.class_bindings,
                    args.vehicle_dir,
                    args.parents,
                )
                label = "parents"
                target = args.parents
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"physics config override: cannot resolve parents: {exc}")
            return 1
        print(f"physics config {label}: {count} records -> {target}")
        return 0

    if args.check:
        return check_config(
            args.class_bindings,
            args.vehicle_dir,
            args.parents,
            args.out,
            args.projection,
            args.calibration,
            args.aircraft_class_bindings,
            args.aircraft_dir,
            args.aircraft_parents,
        )
    try:
        count = write_outputs(
            args.class_bindings,
            args.vehicle_dir,
            args.parents,
            args.out,
            args.projection,
            args.calibration,
            args.aircraft_class_bindings,
            args.aircraft_dir,
            args.aircraft_parents,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"physics config override: cannot build from the corpus: {exc}")
        return 1
    print(f"physics config override: {count} class bodies -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
