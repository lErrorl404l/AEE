#!/usr/bin/env python3
"""Generate the engine CfgMagazines and CfgAmmo overrides from the database.

Two load-time engine overrides are emitted from the verified ballistics
database:

  * ``CfgMagazines >> <magazine> >> initSpeed``: the real muzzle velocity of
    the magazine's cartridge. The value is the cartridge service muzzle
    velocity (documented, US military specifications and TM 43-0001-27) or,
    when no service figure is held, the manufacturer velocity table (claimed,
    Hornady and Lapua). It is held per cartridge in data/ballistics/loads.json.

  * ``CfgAmmo >> <ammo> >> airFriction``: the ballistic drag of the
    projectile, DERIVED from the held ballistic coefficient and the held
    standard drag curve. The engine applies quadratic drag ``a = airFriction *
    v^2``; the verified AEE drag model (fnc_calculateBallisticDrag.sqf) states
    the same form with ``retard = 0.00068418 * (Cd / BC) * v^2``. The
    airFriction is that coefficient evaluated at the reference muzzle Mach
    (the cartridge service muzzle velocity at ISA sea level):

        airFriction = -0.00068418 * Cd(muzzleMach) / BC

    The ballistic coefficient is the held ``bc_g1`` or ``bc_g7`` (measured or
    documented, data/ballistics/projectiles.json). The drag curve is the held
    standard curve (data/ballistics/sources/drag_functions.json, JBM and
    McCoy). No engine number is copied.

The magazine-to-cartridge and ammo-to-projectile links are resolved from the
installed game config and cached under data/engine/. The check path reads the
committed caches only, so the gate stays deterministic in CI.

Run:
    python3 tools/validation/gen_engine_overrides.py --resolve --derap PATH
    python3 tools/validation/gen_engine_overrides.py
    python3 tools/validation/gen_engine_overrides.py --check
Exit 0 when fresh, 1 when stale or missing under --check.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

REPO = Path(__file__).parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

BALL = REPO / "data" / "ballistics"
ENGINE = REPO / "data" / "engine"
OUT_DIR = REPO / "addons" / "ballistics" / "generated"

MAG_BINDINGS = ENGINE / "magazine_bindings.json"
AMMO_BINDINGS = ENGINE / "ammo_bindings.json"
MAG_MASSES = BALL / "magazine_masses.json"
MAG_OUT = OUT_DIR / "CfgMagazines.hpp"
AMMO_OUT = OUT_DIR / "CfgAmmo.hpp"

VERDICTS = ENGINE / "verdicts.json"
REGISTER_OUT = REPO / "docs" / "wiki" / "research" / "engine-override-register.md"

MAG_SCHEMA = "aee.engine.magazine_bindings/1"
AMMO_SCHEMA = "aee.engine.ammo_bindings/1"
VERDICT_SCHEMA = "aee.engine.overrides/1"
VERDICT_ENUM = ("ADOPT", "ALREADY", "RECONCILE", "REJECT")
STATUS_ENUM = ("implemented", "present", "withheld", "rejected")

# The implemented verdicts and the generated key each one must correspond to.
IMPLEMENTED_KEYS = {
    "cfgmagazines-initspeed": ("CfgMagazines", "initSpeed"),
    "cfgmagazines-mass": ("CfgMagazines", "mass"),
    "cfgammo-airfriction": ("CfgAmmo", "airFriction"),
}

# The magazine loaded-mass projection (Task 2 of the mass-expansion plan),
# schema aee.ballistics.magazine_mass/1. The engine mass is the loaded mass.
MAG_MASS_SCHEMA = "aee.ballistics.magazine_mass/1"

# The drag constant and the ISA sea-level speed of sound, both from the
# verified AEE drag model (addons/ballistics/functions/fnc_calculateBallisticDrag.sqf).
DRAG_CONSTANT = 0.00068418
SPEED_OF_SOUND_15C = 340.29

# The cartridge-to-service-projectile map. The verified AEE projectile
# resolver holds this map (tools/validation/gen_runtime_projectiles.py); it is
# imported so the two cannot drift.
from tools.validation.gen_runtime_projectiles import DEFAULTS as SERVICE_PROJECTILE  # noqa: E402

# An ammo class is bound to a projectile only when it is a ball round. A tracer
# or a special round carries a different projectile, and the database holds no
# coefficient for it, so the generator fails closed and emits nothing.
_BALL_MARKERS = ("ball",)
_NON_BALL_MARKERS = (
    "tracer",
    "ap",
    "he",
    "smoke",
    "flare",
    "sub",
    "ir",
    "wp",
    "heat",
    "sabot",
)


@dataclass(frozen=True)
class MagazineBinding:
    game_class: str
    parent_class: str
    ammo_class: str
    cartridge_id: str


@dataclass(frozen=True)
class AmmoBinding:
    game_class: str
    parent_class: str
    cartridge_id: str
    projectile_id: str


@dataclass(frozen=True)
class MuzzleVelocity:
    value_ms: float
    source_id: str
    grade: str
    locator: str


# ─── small parsers ────────────────────────────────────────────────────────


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def normalise(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def derived_aliases(name: str) -> set[str]:
    """The compact aliases a cartridge designation yields.

    Mirrors tools/validation/gen_runtime_cartridges.py: a designation of the
    form 7.62x51 yields 762x51, and a name whose first token is a number
    yields the number plus the initials.
    """
    out: set[str] = set()
    cleaned = re.sub(",", ".", name)
    match = re.search(r"(\d+(?:\.\d+)?)\s*[x\u00d7]\s*(\d+(?:\.\d+)?)", cleaned)
    if match:
        out.add(re.sub(r"[^0-9x]", "", f"{match.group(1)}x{match.group(2)}"))
    tokens = re.findall(r"[A-Za-z0-9.]+", name)
    if tokens:
        digits = re.sub(r"[^0-9]", "", tokens[0])
        if len(digits) >= 3:
            out.add(digits)
    if tokens and re.fullmatch(r"\d+", tokens[0]) and len(tokens) >= 3:
        initials = "".join(t[0].lower() for t in tokens[1:] if t[:1].isalpha())
        if initials:
            out.add(tokens[0] + initials)
    return {a for a in out if len(a) >= 3}


def parse_block(text: str, cfg_name: str) -> str | None:
    """Return the body of a top-level config class, or None."""
    match = re.search(r"\n\s*class\s+" + re.escape(cfg_name) + r"\s*\{", text)
    if match is None:
        return None
    open_at = text.index("{", match.start())
    depth = 1
    index = open_at + 1
    while index < len(text) and depth > 0:
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    return text[open_at + 1 : index - 1]


def direct_children(body: str) -> list[tuple[str, str | None, str]]:
    """Return (name, parent, body) for the direct child classes of a body."""
    out: list[tuple[str, str | None, str]] = []
    depth = 0
    index = 0
    length = len(body)
    while index < length:
        char = body[index]
        if char == "{":
            depth += 1
            index += 1
            continue
        if char == "}":
            depth -= 1
            index += 1
            continue
        if depth == 0:
            match = re.match(
                r"class\s+([A-Za-z0-9_]+)\s*(?::\s*([A-Za-z0-9_]+))?\s*\{",
                body[index:],
            )
            if match is not None:
                open_at = body.index("{", index)
                inner_depth = 1
                cursor = open_at + 1
                while cursor < length and inner_depth > 0:
                    if body[cursor] == "{":
                        inner_depth += 1
                    elif body[cursor] == "}":
                        inner_depth -= 1
                    cursor += 1
                out.append(
                    (match.group(1), match.group(2), body[open_at + 1 : cursor - 1])
                )
                index = cursor
                continue
        index += 1
    return out


def field(body: str, key: str) -> str | None:
    match = re.search(
        r"(?<![\w])" + re.escape(key) + r"\s*=\s*(\"?[^;]*?\"?)\s*;", body
    )
    if match is None:
        return None
    return match.group(1).strip().strip('"')


# ─── corpus readers ───────────────────────────────────────────────────────


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def cartridge_index() -> dict[str, str]:
    """Return alias -> cartridge id, from the cartridge corpus."""
    records = load_json(BALL / "cartridges.json")
    if not isinstance(records, list):
        raise ValueError("cartridges.json must be a top-level array")
    index: dict[str, str] = {}
    for raw in records:
        record = _mapping(raw)
        if record is None:
            continue
        cartridge_id = _text(record.get("cartridge_id"))
        if cartridge_id is None:
            continue
        aliases = {normalise(cartridge_id)}
        names = record.get("names")
        if isinstance(names, list):
            for name in names:
                if not isinstance(name, str):
                    continue
                aliases.add(normalise(name))
                aliases |= derived_aliases(name)
        for alias in aliases:
            if len(alias) >= 3:
                index.setdefault(alias, cartridge_id)
    return index


def resolve_cartridge(aliases: dict[str, str], class_name: str) -> str | None:
    for token in re.split(r"[_\-. ]", class_name.lower()):
        if token in aliases:
            return aliases[token]
    return None


def load_drag_table(standard: str) -> list[tuple[float, float]]:
    payload = _mapping(load_json(BALL / "sources" / "drag_functions.json"))
    if payload is None:
        raise ValueError("drag_functions.json must be an object")
    models = _mapping(payload.get("models"))
    if models is None:
        raise ValueError("drag_functions.json holds no models")
    rows = models.get(standard)
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"drag_functions.json holds no {standard} curve")
    table: list[tuple[float, float]] = []
    for raw in rows:
        row = _mapping(raw)
        if row is None:
            continue
        mach = _number(row.get("mach"))
        cd = _number(row.get("cd"))
        if mach is not None and cd is not None:
            table.append((mach, cd))
    return sorted(table)


def interpolate_cd(table: Sequence[tuple[float, float]], mach: float) -> float:
    if not table:
        raise ValueError("empty drag table")
    if mach <= table[0][0]:
        return table[0][1]
    if mach >= table[-1][0]:
        return table[-1][1]
    for (m0, c0), (m1, c1) in zip(table, table[1:]):
        if m0 <= mach <= m1:
            span = m1 - m0
            if span == 0:
                return c0
            return c0 + (c1 - c0) * (mach - m0) / span
    return table[-1][1]


# ─── resolve from the installed game config ───────────────────────────────


def resolve_bindings(derap: Path) -> tuple[list[MagazineBinding], list[AmmoBinding]]:
    """Resolve the magazine and ammo bindings from a derapified config."""
    if not derap.is_file():
        raise ValueError(f"{derap}: the derapified config is not a file")
    text = derap.read_text(encoding="utf-8", errors="replace")
    aliases = cartridge_index()

    mag_body = parse_block(text, "CfgMagazines")
    ammo_body = parse_block(text, "CfgAmmo")
    if mag_body is None or ammo_body is None:
        raise ValueError("the derap holds no CfgMagazines or no CfgAmmo block")

    magazines: list[MagazineBinding] = []
    for name, parent, inner in direct_children(mag_body):
        if parent is None:
            continue
        ammo = field(inner, "ammo")
        if not ammo:
            continue
        cartridge = resolve_cartridge(aliases, ammo) or resolve_cartridge(aliases, name)
        if cartridge is None:
            continue
        magazines.append(
            MagazineBinding(
                game_class=name,
                parent_class=parent,
                ammo_class=ammo,
                cartridge_id=cartridge,
            )
        )

    ammo_records: list[AmmoBinding] = []
    for name, parent, _inner in direct_children(ammo_body):
        if parent is None:
            continue
        lowered = name.lower()
        if not any(marker in lowered for marker in _BALL_MARKERS):
            continue
        if any(marker in lowered for marker in _NON_BALL_MARKERS):
            continue
        cartridge = resolve_cartridge(aliases, name)
        if cartridge is None:
            continue
        projectile = SERVICE_PROJECTILE.get(cartridge)
        if projectile is None:
            continue
        ammo_records.append(
            AmmoBinding(
                game_class=name,
                parent_class=parent,
                cartridge_id=cartridge,
                projectile_id=projectile,
            )
        )

    if not magazines:
        raise ValueError("no magazine binding resolved from the derap")
    if not ammo_records:
        raise ValueError("no ammo binding resolved from the derap")
    return magazines, ammo_records


def write_bindings(derap: Path) -> tuple[int, int]:
    magazines, ammo = resolve_bindings(derap)
    provenance = "weapons_f.pbo config.bin (hemtt pbo extract + config derapify)"
    _write(
        MAG_BINDINGS,
        json.dumps(
            {
                "schema": MAG_SCHEMA,
                "note": "Resolved from the installed game config. Do not edit by hand.",
                "resolved_from": provenance,
                "rows": [binding.__dict__ for binding in magazines],
            },
            indent=2,
        )
        + "\n",
    )
    _write(
        AMMO_BINDINGS,
        json.dumps(
            {
                "schema": AMMO_SCHEMA,
                "note": "Resolved from the installed game config. Do not edit by hand.",
                "resolved_from": provenance,
                "rows": [binding.__dict__ for binding in ammo],
            },
            indent=2,
        )
        + "\n",
    )
    return len(magazines), len(ammo)


# ─── binding caches ───────────────────────────────────────────────────────


def load_magazine_bindings(path: Path = MAG_BINDINGS) -> list[MagazineBinding]:
    payload = _mapping(load_json(path))
    if payload is None or payload.get("schema") != MAG_SCHEMA:
        raise ValueError(f"{path}: schema must be {MAG_SCHEMA}")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: rows must be a non-empty array")
    out: list[MagazineBinding] = []
    seen: set[str] = set()
    for raw in rows:
        record = _mapping(raw)
        if record is None:
            raise ValueError(f"{path}: a row is not an object")
        game_class = _text(record.get("game_class"))
        parent_class = _text(record.get("parent_class"))
        ammo_class = _text(record.get("ammo_class"))
        cartridge_id = _text(record.get("cartridge_id"))
        if None in (game_class, parent_class, ammo_class, cartridge_id):
            raise ValueError(f"{path}: a row is incomplete")
        if game_class in seen:
            raise ValueError(f"{path}: duplicate game_class {game_class}")
        seen.add(game_class)
        out.append(MagazineBinding(game_class, parent_class, ammo_class, cartridge_id))
    return out


def load_ammo_bindings(path: Path = AMMO_BINDINGS) -> list[AmmoBinding]:
    payload = _mapping(load_json(path))
    if payload is None or payload.get("schema") != AMMO_SCHEMA:
        raise ValueError(f"{path}: schema must be {AMMO_SCHEMA}")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: rows must be a non-empty array")
    out: list[AmmoBinding] = []
    seen: set[str] = set()
    for raw in rows:
        record = _mapping(raw)
        if record is None:
            raise ValueError(f"{path}: a row is not an object")
        game_class = _text(record.get("game_class"))
        parent_class = _text(record.get("parent_class"))
        cartridge_id = _text(record.get("cartridge_id"))
        projectile_id = _text(record.get("projectile_id"))
        if None in (game_class, parent_class, cartridge_id, projectile_id):
            raise ValueError(f"{path}: a row is incomplete")
        if game_class in seen:
            raise ValueError(f"{path}: duplicate game_class {game_class}")
        seen.add(game_class)
        out.append(AmmoBinding(game_class, parent_class, cartridge_id, projectile_id))
    return out


# ─── magazine mass projection ─────────────────────────────────────────────


@dataclass(frozen=True)
class MassGroup:
    """One (chambering, capacity) group of the loaded-mass projection."""

    calibre_key: str
    capacity: int
    loaded_mass_kg: float
    source_id: str
    locator: str
    grade: str


def load_mass_groups(path: Path = MAG_MASSES) -> list[MassGroup]:
    """Read the loaded-mass projection. Raise ValueError when malformed."""
    payload = _mapping(load_json(path))
    if payload is None or payload.get("schema") != MAG_MASS_SCHEMA:
        raise ValueError(f"{path}: schema must be {MAG_MASS_SCHEMA}")
    rows = payload.get("groups")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: groups must be a non-empty array")
    out: list[MassGroup] = []
    for raw in rows:
        record = _mapping(raw)
        if record is None:
            raise ValueError(f"{path}: a group is not an object")
        calibre = _text(record.get("calibre_key"))
        capacity = _number(record.get("capacity"))
        mass = _number(record.get("loaded_mass_g"))
        source_id = _text(record.get("source_id"))
        locator = _text(record.get("locator"))
        grade = _text(record.get("grade"))
        if None in (calibre, capacity, mass, source_id, locator, grade):
            raise ValueError(f"{path}: a group is incomplete")
        out.append(
            MassGroup(calibre, int(capacity), mass / 1000.0, source_id, locator, grade)
        )
    return out


def classname_capacity(class_name: str) -> int:
    """The capacity a classname states, mirroring fnc_getMagazineMass.

    The digits that precede "rnd", as in "30Rnd_556x45_Stanag" -> 30. A
    classname that states no capacity returns 0.
    """
    lower = class_name.lower()
    marker = lower.find("rnd")
    if marker <= 0:
        return 0
    digits = ""
    index = marker - 1
    while index >= 0 and lower[index].isdigit():
        digits = lower[index] + digits
        index -= 1
    return int(digits) if digits else 0


def resolve_mass(class_name: str, groups: Sequence[MassGroup]) -> MassGroup | None:
    """Resolve a magazine classname to its loaded-mass group.

    The chambering token and the capacity are the two signals the classname
    carries, exactly as fnc_getMagazineMass parses them. A classname that
    states no capacity matches the first group for its chambering. A
    classname with no matching group resolves nothing.
    """
    lower = class_name.lower()
    capacity = classname_capacity(class_name)
    for group in groups:
        if group.calibre_key in lower and group.capacity == capacity:
            return group
    if capacity == 0:
        for group in groups:
            if group.calibre_key in lower:
                return group
    return None


# ─── value sources ────────────────────────────────────────────────────────


def load_projectiles() -> dict[str, dict[str, object]]:
    records = load_json(BALL / "projectiles.json")
    if not isinstance(records, list):
        raise ValueError("projectiles.json must be a top-level array")
    out: dict[str, dict[str, object]] = {}
    for raw in records:
        record = _mapping(raw)
        if record is None:
            continue
        projectile_id = _text(record.get("projectile_id"))
        if projectile_id is not None:
            out[projectile_id] = record
    return out


def load_loads() -> dict[str, list[dict[str, object]]]:
    records = load_json(BALL / "loads.json")
    if not isinstance(records, list):
        raise ValueError("loads.json must be a top-level array")
    out: dict[str, list[dict[str, object]]] = {}
    for raw in records:
        record = _mapping(raw)
        if record is None:
            continue
        cartridge_id = _text(record.get("cartridge_id"))
        if cartridge_id is not None:
            out.setdefault(cartridge_id, []).append(record)
    return out


def _held(row: dict[str, object], field_name: str) -> dict[str, object] | None:
    values = _mapping(row.get("values"))
    if values is None:
        return None
    return _mapping(values.get(field_name))


def _mv_from_load(row: dict[str, object]) -> MuzzleVelocity | None:
    service = _held(row, "service_velocity_ms")
    if service is not None:
        value = _number(service.get("value"))
        source = _text(service.get("source"))
        grade = _text(service.get("grade"))
        if value is not None and source is not None and grade is not None:
            return MuzzleVelocity(value, source, grade, "service_velocity_ms")
    anchors = _held(row, "mv_anchors")
    if anchors is not None:
        entries = anchors.get("value")
        source = _text(anchors.get("source"))
        grade = _text(anchors.get("grade"))
        if (
            isinstance(entries, list)
            and entries
            and source is not None
            and grade is not None
        ):
            first = _mapping(entries[0])
            if first is not None:
                value = _number(first.get("mv_ms"))
                barrel = _number(first.get("barrel_mm"))
                if value is not None:
                    locator = (
                        f"mv_anchors[0] barrel {barrel:g} mm"
                        if barrel is not None
                        else "mv_anchors[0]"
                    )
                    return MuzzleVelocity(value, source, grade, locator)
    return None


def cartridge_muzzle_velocity(
    cartridge_id: str,
    loads: dict[str, list[dict[str, object]]],
    projectiles: dict[str, dict[str, object]],
) -> MuzzleVelocity | None:
    """Return the cartridge muzzle velocity, preferring the service round.

    The service projectile (the verified cartridge-to-projectile map) names the
    service round; the load whose projectile text matches its names supplies
    the velocity. When no service round is held, the first documented service
    load, then the first manufacturer anchor, supplies it.
    """
    rows = loads.get(cartridge_id, [])
    if not rows:
        return None
    projectile_id = SERVICE_PROJECTILE.get(cartridge_id)
    if projectile_id is not None:
        names = projectiles.get(projectile_id, {}).get("names")
        wanted = (
            {normalise(name) for name in names} if isinstance(names, list) else set()
        )
        for row in rows:
            text = normalise(_text(row.get("projectile")))
            if text and text in wanted:
                found = _mv_from_load(row)
                if found is not None:
                    return found
    for row in rows:
        found = _mv_from_load(row)
        if found is not None and found.grade == "documented":
            return found
    for row in rows:
        found = _mv_from_load(row)
        if found is not None:
            return found
    return None


def air_friction(
    projectile: dict[str, object], init_speed: float
) -> tuple[float, str, float] | None:
    """Return (airFriction, standard, bc) derived from the held coefficient."""
    values = _mapping(projectile.get("values"))
    if values is None:
        return None
    for standard, key in (("G7", "bc_g7"), ("G1", "bc_g1")):
        held = _mapping(values.get(key))
        if held is None:
            continue
        bc = _number(held.get("value"))
        if bc is None or bc <= 0:
            continue
        mach = init_speed / SPEED_OF_SOUND_15C
        cd = interpolate_cd(load_drag_table(standard), mach)
        return (-DRAG_CONSTANT * cd / bc, standard, bc)
    return None


# ─── render ───────────────────────────────────────────────────────────────


def _render_number(value: float) -> str:
    rounded = round(value, 9)
    if float(rounded).is_integer():
        return str(int(rounded))
    return repr(rounded)


MAG_HEADER = """/* SPDX-License-Identifier: GPL-2.0-or-later */
// Generated engine config override. Do not edit by hand.
// Regenerate with: python3 tools/validation/gen_engine_overrides.py
//
// CfgMagazines initSpeed. This is a load-time, global override of the vanilla
// engine magazine velocity. The engine reads initSpeed when the magazine is
// created, and config cannot be gated at runtime, so the PBO is the only off
// switch.
//
// Each class restates its immediate real parent, and every parent is
// forward-declared once. A reopen that omits the parent invokes the engine
// Empty syntax and strips the vanilla class of every inherited property. The
// generator never emits a bare class.
//
// initSpeed is the cartridge service muzzle velocity in m/s:
//   * the documented service velocity from the US military specifications and
//     TM 43-0001-27 (grade documented); or, when none is held,
//   * the manufacturer velocity table from Hornady or Lapua (grade claimed).
// The value is held per cartridge in data/ballistics/loads.json. The
// magazine-to-cartridge link is the committed cache
// data/engine/magazine_bindings.json, resolved from the installed game
// config.
//
// CfgMagazines mass is the magazine LOADED mass in kg, from the held
// loaded-mass projection data/ballistics/magazine_masses.json (schema
// aee.ballistics.magazine_mass/1). The loaded mass is the held value where
// it is held, or DERIVED as empty_mass_g + capacity * round_mass_g from the
// held round mass for the chambering. It resolves by the classname capacity
// plus the chambering token, exactly as fnc_getMagazineMass parses a
// classname. A magazine that resolves no mass keeps its initSpeed and is
// recorded below as a mass lead. No engine number is copied.
"""

AMMO_HEADER = """/* SPDX-License-Identifier: GPL-2.0-or-later */
// Generated engine config override. Do not edit by hand.
// Regenerate with: python3 tools/validation/gen_engine_overrides.py
//
// CfgAmmo airFriction. This is a load-time, global override of the vanilla
// engine projectile drag. The engine reads airFriction when the projectile is
// created, and config cannot be gated at runtime, so the PBO is the only off
// switch.
//
// Each class restates its immediate real parent, and every parent is
// forward-declared once. A reopen that omits the parent invokes the engine
// Empty syntax and strips the vanilla class of every inherited property. The
// generator never emits a bare class.
//
// airFriction is DERIVED, never copied. The engine applies quadratic drag
// a = airFriction * v^2. The verified AEE drag model states the same form with
// retard = 0.00068418 * (Cd / BC) * v^2. The value is that coefficient at the
// reference muzzle Mach (the cartridge service muzzle velocity at ISA sea
// level):
//     airFriction = -0.00068418 * Cd(muzzleMach) / BC
// BC is the held measured or documented ballistic coefficient and Cd is the
// held standard drag curve (data/ballistics/projectiles.json and
// data/ballistics/sources/drag_functions.json, JBM and McCoy). The
// ammo-to-projectile link is the committed cache
// data/engine/ammo_bindings.json.
"""


@dataclass(frozen=True)
class MagazineEmission:
    game_class: str
    parent_class: str
    init_speed: float
    velocity: MuzzleVelocity
    mass_kg: float | None = None
    mass_source_id: str | None = None
    mass_locator: str | None = None
    mass_grade: str | None = None


@dataclass(frozen=True)
class AmmoEmission:
    game_class: str
    parent_class: str
    air_friction: float
    standard: str
    bc: float


def build_magazines(
    bindings: Sequence[MagazineBinding],
    loads: dict[str, list[dict[str, object]]],
    projectiles: dict[str, dict[str, object]],
    groups: Sequence[MassGroup] | None = None,
) -> tuple[list[MagazineEmission], list[str], list[str]]:
    if groups is None:
        groups = load_mass_groups()
    emissions: list[MagazineEmission] = []
    withheld: list[str] = []
    mass_leads: list[str] = []
    cache: dict[str, MuzzleVelocity | None] = {}
    for binding in sorted(bindings, key=lambda item: item.game_class):
        if binding.cartridge_id not in cache:
            cache[binding.cartridge_id] = cartridge_muzzle_velocity(
                binding.cartridge_id, loads, projectiles
            )
        velocity = cache[binding.cartridge_id]
        if velocity is None:
            withheld.append(
                f"{binding.game_class}: no muzzle velocity for {binding.cartridge_id}"
            )
            continue
        group = resolve_mass(binding.game_class, groups)
        if group is None:
            mass_leads.append(f"{binding.game_class}: no resolved loaded mass")
            emissions.append(
                MagazineEmission(
                    binding.game_class,
                    binding.parent_class,
                    velocity.value_ms,
                    velocity,
                )
            )
            continue
        emissions.append(
            MagazineEmission(
                binding.game_class,
                binding.parent_class,
                velocity.value_ms,
                velocity,
                mass_kg=group.loaded_mass_kg,
                mass_source_id=group.source_id,
                mass_locator=group.locator,
                mass_grade=group.grade,
            )
        )
    return emissions, withheld, mass_leads


def build_ammo(
    bindings: Sequence[AmmoBinding],
    loads: dict[str, list[dict[str, object]]],
    projectiles: dict[str, dict[str, object]],
) -> tuple[list[AmmoEmission], list[str]]:
    emissions: list[AmmoEmission] = []
    withheld: list[str] = []
    cache: dict[str, float | None] = {}
    for binding in sorted(bindings, key=lambda item: item.game_class):
        if binding.cartridge_id not in cache:
            velocity = cartridge_muzzle_velocity(
                binding.cartridge_id, loads, projectiles
            )
            cache[binding.cartridge_id] = (
                velocity.value_ms if velocity is not None else None
            )
        init_speed = cache[binding.cartridge_id]
        if init_speed is None:
            withheld.append(
                f"{binding.game_class}: no muzzle velocity for {binding.cartridge_id}"
            )
            continue
        projectile = projectiles.get(binding.projectile_id)
        if projectile is None:
            withheld.append(
                f"{binding.game_class}: no projectile {binding.projectile_id}"
            )
            continue
        derived = air_friction(projectile, init_speed)
        if derived is None:
            withheld.append(
                f"{binding.game_class}: {binding.projectile_id} holds no coefficient"
            )
            continue
        value, standard, bc = derived
        emissions.append(
            AmmoEmission(binding.game_class, binding.parent_class, value, standard, bc)
        )
    return emissions, withheld


def _render_classes(
    header: str,
    class_name: str,
    rows: Sequence[tuple[str, str, str]],
    withheld: Sequence[str],
    mass_leads: Sequence[str] = (),
) -> str:
    by_class = {game: (parent, body) for game, parent, body in rows}
    emitted = set(by_class)
    # Only an external parent is forward-declared. A parent that this block
    # also defines is emitted as a body, and a forward declaration beside the
    # body is a duplicate definition (hemtt L-C03).
    external_parents = sorted(
        {parent for _g, parent, _b in rows if parent not in emitted}
    )

    depth_cache: dict[str, int] = {}

    def depth(game: str, stack: frozenset[str]) -> int:
        if game not in emitted:
            return 0
        if game in depth_cache:
            return depth_cache[game]
        if game in stack:
            return 0
        parent = by_class[game][0]
        value = 0 if parent not in emitted else depth(parent, stack | {game}) + 1
        depth_cache[game] = value
        return value

    # An emitted parent must be defined before its child, so order by depth.
    ordered = sorted(rows, key=lambda item: (depth(item[0], frozenset()), item[0]))

    lines = [header, f"class {class_name} {{"]
    for parent in external_parents:
        lines.append(f"    class {parent};")
    if external_parents and rows:
        lines.append("")
    for game_class, parent, body in ordered:
        lines.append(f"    class {game_class}: {parent} {{")
        lines.append(f"        {body}")
        lines.append("    };")
    lines.append("};")
    if withheld:
        lines.append("")
        lines.append("// Withheld bindings (no sourced value):")
        for item in withheld:
            lines.append(f"//   {item}")
    if mass_leads:
        lines.append("")
        lines.append("// Mass leads (no resolved loaded mass):")
        for item in mass_leads:
            lines.append(f"//   {item}")
    return "\n".join(lines) + "\n"


def render_magazines(
    emissions: Sequence[MagazineEmission],
    withheld: Sequence[str],
    mass_leads: Sequence[str] = (),
) -> str:
    rows = []
    for item in emissions:
        body = f"initSpeed = {_render_number(item.init_speed)};"
        if item.mass_kg is not None:
            body += f"\n        mass = {_render_number(item.mass_kg)};"
        rows.append((item.game_class, item.parent_class, body))
    return _render_classes(MAG_HEADER, "CfgMagazines", rows, withheld, mass_leads)


def render_ammo(emissions: Sequence[AmmoEmission], withheld: Sequence[str]) -> str:
    rows = [
        (
            item.game_class,
            item.parent_class,
            f"airFriction = {_render_number(item.air_friction)};",
        )
        for item in emissions
    ]
    return _render_classes(AMMO_HEADER, "CfgAmmo", rows, withheld)


def load_verdicts(path: Path = VERDICTS) -> list[dict[str, object]]:
    payload = _mapping(load_json(path))
    if payload is None or payload.get("schema") != VERDICT_SCHEMA:
        raise ValueError(f"{path}: schema must be {VERDICT_SCHEMA}")
    rows = payload.get("surfaces")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: surfaces must be a non-empty array")
    out: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in rows:
        record = _mapping(raw)
        if record is None:
            raise ValueError(f"{path}: a surface is not an object")
        surface_id = _text(record.get("id"))
        verdict = _text(record.get("verdict"))
        status = _text(record.get("status"))
        if surface_id is None or verdict is None or status is None:
            raise ValueError(f"{path}: a surface is incomplete")
        if surface_id in seen:
            raise ValueError(f"{path}: duplicate surface id {surface_id}")
        if verdict not in VERDICT_ENUM:
            raise ValueError(f"{path}: {surface_id} has verdict {verdict}")
        if status not in STATUS_ENUM:
            raise ValueError(f"{path}: {surface_id} has status {status}")
        seen.add(surface_id)
        out.append(record)
    return out


def render_register(verdicts: Sequence[dict[str, object]]) -> str:
    lines = [
        "# Engine override register",
        "",
        "Generated by `tools/validation/gen_engine_overrides.py` from",
        "`data/engine/verdicts.json`. Do not edit by hand. It records the",
        "verdict per base engine config class AEE can override: implemented",
        "(ADOPT), already overridden (ALREADY), withheld with a reason",
        "(RECONCILE), or rejected with a ceiling (REJECT).",
        "",
        "| Domain | Surface | Verdict | Status |",
        "|---|---|---|---|",
    ]
    order = {"ADOPT": 0, "ALREADY": 1, "RECONCILE": 2, "REJECT": 3}
    for record in sorted(
        verdicts, key=lambda item: (order.get(str(item["verdict"]), 9), str(item["id"]))
    ):
        lines.append(
            f"| {record['domain']} | `{record['surface']}` | {record['verdict']} | {record['status']} |"
        )
    lines.append("")
    for record in verdicts:
        lines.append(f"## {record['surface']}")
        lines.append("")
        lines.append(f"- Verdict: **{record['verdict']}** ({record['status']})")
        lines.append(f"- Source: {record.get('source', 'None.')}")
        lines.append(f"- Reason: {record.get('reason', 'None.')}")
        if record.get("ceiling"):
            lines.append(f"- Ceiling: {record['ceiling']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def implemented_keys(
    verdicts: Sequence[dict[str, object]],
) -> dict[str, tuple[str, str]]:
    """Return the implemented verdict ids and the generated key each one owns."""
    return {
        str(record["id"]): IMPLEMENTED_KEYS[str(record["id"])]
        for record in verdicts
        if record.get("status") == "implemented"
    }


def build_all(
    mag_path: Path = MAG_BINDINGS, ammo_path: Path = AMMO_BINDINGS
) -> tuple[str, str, str]:
    loads = load_loads()
    projectiles = load_projectiles()
    groups = load_mass_groups()
    magazines, mag_withheld, mass_leads = build_magazines(
        load_magazine_bindings(mag_path), loads, projectiles, groups
    )
    ammo, ammo_withheld = build_ammo(load_ammo_bindings(ammo_path), loads, projectiles)
    return (
        render_magazines(magazines, mag_withheld, mass_leads),
        render_ammo(ammo, ammo_withheld),
        render_register(load_verdicts()),
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fresh(path: Path, text: str) -> bool:
    if not path.is_file():
        print(f"engine overrides: {path} is missing; run the generator")
        return False
    if path.read_text(encoding="utf-8") != text:
        print(f"engine overrides: {path} is stale; run the generator")
        return False
    return True


def _count_values(text: str, key: str) -> int:
    return text.count(f"        {key} = ")


def write_outputs() -> tuple[int, int, int]:
    mag_text, ammo_text, register_text = build_all()
    _write(MAG_OUT, mag_text)
    _write(AMMO_OUT, ammo_text)
    _write(REGISTER_OUT, register_text)
    return (
        _count_values(mag_text, "initSpeed"),
        _count_values(mag_text, "mass"),
        _count_values(ammo_text, "airFriction"),
    )


def check() -> int:
    try:
        mag_text, ammo_text, register_text = build_all()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"engine overrides: cannot build from the corpus: {exc}")
        return 1
    ok = _fresh(MAG_OUT, mag_text)
    ok = _fresh(AMMO_OUT, ammo_text) and ok
    ok = _fresh(REGISTER_OUT, register_text) and ok
    if not ok:
        return 1
    print(
        f"engine overrides: {_count_values(mag_text, 'initSpeed')} initSpeed, "
        f"{_count_values(mag_text, 'mass')} mass and "
        f"{_count_values(ammo_text, 'airFriction')} airFriction values (fresh)"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the engine override headers."
    )
    parser.add_argument(
        "--check", action="store_true", help="verify freshness; write nothing"
    )
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="resolve the binding caches from a derapified game config",
    )
    parser.add_argument(
        "--derap",
        type=Path,
        help="path to a derapified weapons_f config.cpp for --resolve",
    )
    args = parser.parse_args(argv)

    if args.resolve:
        if args.derap is None:
            print("engine overrides: --resolve needs --derap PATH")
            return 2
        try:
            mags, ammo = write_bindings(args.derap)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"engine overrides: cannot resolve bindings: {exc}")
            return 1
        print(f"engine overrides: resolved {mags} magazines and {ammo} ammo classes")
        return 0

    if args.check:
        return check()
    try:
        mags, masses, ammo = write_outputs()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"engine overrides: cannot build from the corpus: {exc}")
        return 1
    print(
        f"engine overrides: wrote {mags} initSpeed, {masses} mass and "
        f"{ammo} airFriction values"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
