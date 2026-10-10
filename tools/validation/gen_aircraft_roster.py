#!/usr/bin/env python3
"""Derive the aircraft class roster from a committed class inventory.

The class inventory is resolved once from the installed air config with
``--resolve --game-root PATH``. The roster is derived from the committed
inventory and never reads the game install. The check path reads no game
install either, so the roster is reproducible on a bare checkout.

Run:
    python3 tools/validation/gen_aircraft_roster.py --resolve --game-root PATH
    python3 tools/validation/gen_aircraft_roster.py
    python3 tools/validation/gen_aircraft_roster.py --check
Exit: 0 when fresh, 1 when stale or when a guard fails.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

REPO = Path(__file__).parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import schemas  # noqa: E402

DEFAULT_DATA = REPO / "data" / "aircraft"

INVENTORY_OUT = "class_inventory.json"
ROSTER_OUT = "roster.json"
ROSTER_REPORT = "ROSTER.md"

INVENTORY_SCHEMA = schemas.AIRCRAFT_CLASS_INVENTORY

# The four engine class tokens of the air family.
AIR_TOKENS = ("Air", "Plane", "Helicopter", "UAV")
# The generic engine bases below a family base. A family base is any other
# class whose name ends in `_base_` plus a letter.
ENGINE_BASES = frozenset(
    {
        "AllVehicles",
        "Air",
        "Plane",
        "Helicopter",
        "UAV",
        "Plane_Base_F",
        "Plane_Base_H",
        "Helicopter_Base_F",
        "Helicopter_Base_H",
        "VTOL_Base_F",
    }
)
# The engine places a parachute under Helicopter. A parachute is a recovery
# system, not an air vehicle, so the roster excludes its chain.
PARACHUTE_NAMES = frozenset(
    {"Parachute", "ParachuteWest", "ParachuteBase", "Paraglide"}
)

# A variant family with no real counterpart is recorded as ``no_source``.
# The corpus holds no catalogue entry for the real type, and the class is a
# fictional or toy-grade stand-in, so no binding is invented. The reason text
# is attached to every roster row of the family. The list is keyed by the
# variant family the roster derives, so a new class in a listed family is
# covered without a second edit.
NO_SOURCE_FAMILIES: dict[str, str] = {
    "Heli_Transport_04": (
        "fictional CSAT heavy lift (Mi-290 Taru). The Armed Assault Wiki "
        "names a composite of the Sikorsky CH-54 Tarhe and the Kamov Ka-226, "
        "so there is no single real counterpart and no held catalogue entry."
    ),
    "UAV_01": (
        "toy-grade miniature quadcopter (AR-2 Darter). No real counterpart "
        "with a held specification, so the class is no_source."
    ),
    "UAV_02": (
        "fictional unmanned combat air vehicle (MQ-4A Greyhawk). The Armed "
        "Assault Wiki names the MQ-9 as its basis, and the corpus holds no "
        "catalogue entry, so the class is no_source."
    ),
    "UAV_03": (
        "fictional unmanned combat air vehicle (MQ-12 Falcon). The corpus "
        "holds no catalogue entry for the real type, so the class is "
        "no_source."
    ),
    "UAV_04": (
        "fictional unmanned combat air vehicle (KH-3A Fenghuang). The corpus "
        "holds no catalogue entry for the real type, so the class is "
        "no_source."
    ),
    "UAV_05": (
        "fictional unmanned combat air vehicle (UCAV Sentinel). The corpus "
        "holds no catalogue entry for the real type, so the class is "
        "no_source."
    ),
    "UAV_06": (
        "fictional utility quadcopter (AL-6 Pelican). No real counterpart "
        "with a held specification, so the class is no_source."
    ),
    "VTOL_01": (
        "fictional tiltrotor (V-44X Blackfish). The Armed Assault Wiki names "
        "an enlarged Bell Boeing V-22 Osprey with V-280 Valor propulsion, so "
        "there is no single real counterpart and no held catalogue entry."
    ),
    "VTOL_02": (
        "fictional stealth VTOL (Y-32 Xi'an). The Armed Assault Wiki names no "
        "real counterpart, so the class is no_source."
    ),
}

# A family or engine base class name.
BASE_SUFFIX = re.compile(r"_base_[A-Za-z]+$", re.IGNORECASE)
# The air addons. Only these packed addons are unpacked for the resolve.
AIR_ADDON = re.compile(r"(?:air_f|drones_f)", re.IGNORECASE)
# A class declaration, with an optional parent, and its opening brace.
CLASS_DECL = re.compile(
    r"(?<![\w])class\s+([A-Za-z_]\w*)\s*(?::\s*([A-Za-z_]\w*))?\s*\{"
)
# The engine scope of a class. An inherited scope is resolved at derive time.
SCOPE_RE = re.compile(r"(?<![A-Za-z_])scope\s*=\s*(\d+)\s*;")
# A concrete class a user can spawn, or close to it.
CONCRETE_SCOPES = (1, 2)

# The installed directories that hold no vanilla air class.
SKIP_PARTS = frozenset(
    {"workshop", "mods", "steamapps", "mpmissions", "keys", "battleye", "dta"}
)

JsonObject = dict[str, object]


# --------------------------------------------------------------------------
# Config reading
# --------------------------------------------------------------------------


def _skip(path: Path, root: Path) -> bool:
    """True when the path is a mod or install directory, not a game addon."""
    parts = path.relative_to(root).parts
    if not parts:
        return False
    head = parts[0]
    return head.startswith("@") or head in SKIP_PARTS


def _run_hemtt(argv: list[str]) -> bool:
    """Run hemtt. Return True on success. A missing hemtt raises."""
    try:
        result = subprocess.run(
            ["hemtt", *argv], capture_output=True, text=True, check=False
        )
    except FileNotFoundError as exc:
        raise ValueError("hemtt is required to resolve from a game install") from exc
    return result.returncode == 0


def _unpack(pbo: Path, dest: Path) -> bool:
    """Unpack a packed addon to dest. Return True on success."""
    return _run_hemtt(["utils", "pbo", "unpack", str(pbo), str(dest)]) and dest.is_dir()


def _derapify(binary: Path, target: Path) -> bool:
    """Convert a packed config to readable text. Return True on success."""
    return _run_hemtt(
        ["utils", "config", "derapify", "-f", "cpp", str(binary), str(target)]
    )


def config_texts(game_root: Path, scratch: Path) -> list[tuple[str, str]]:
    """Return the locator and text of every readable air config file.

    The loose game config comes first, then the air packed addons in a fixed
    order, so the result is deterministic.
    """
    found: list[tuple[str, str]] = []
    for path in sorted(game_root.rglob("config.cpp")):
        if _skip(path, game_root):
            continue
        try:
            found.append(
                (
                    path.relative_to(game_root).as_posix(),
                    path.read_text(encoding="utf-8", errors="replace"),
                )
            )
        except OSError:
            continue
    pbos = sorted(
        (
            pbo
            for pbo in game_root.rglob("*.pbo")
            if AIR_ADDON.search(pbo.name) and not _skip(pbo, game_root)
        ),
        key=lambda pbo: pbo.as_posix(),
    )
    for pbo in pbos:
        rel = pbo.relative_to(game_root).as_posix()
        dest = scratch / rel.replace("/", "__")
        if not _unpack(pbo, dest):
            continue
        for config in sorted(dest.rglob("config.cpp")):
            try:
                found.append(
                    (
                        f"{rel} > {config.relative_to(dest).as_posix()}",
                        config.read_text(encoding="utf-8", errors="replace"),
                    )
                )
            except OSError:
                continue
        for binary in sorted(dest.rglob("config.bin")):
            target = binary.with_suffix(".cpp")
            if not _derapify(binary, target):
                continue
            try:
                found.append(
                    (
                        f"{rel} > {binary.relative_to(dest).with_suffix('.cpp').as_posix()}",
                        target.read_text(encoding="utf-8", errors="replace"),
                    )
                )
            except OSError:
                continue
    return found


def _block(text: str, start: int) -> str:
    """Return the body of the class whose declaration starts at start."""
    open_index = text.find("{", start)
    if open_index < 0:
        return ""
    depth = 0
    index = open_index
    while index < len(text):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[open_index + 1 : index]
        index += 1
    return text[open_index + 1 :]


def _top_scope(block: str) -> int | None:
    """Return the first scope stated in the class body, ignoring nested classes."""
    depth = 0
    index = 0
    while index < len(block):
        char = block[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif depth == 0:
            match = SCOPE_RE.match(block, index)
            if match:
                return int(match.group(1))
        index += 1
    return None


def parse_declarations(text: str, locator: str, tree: dict[str, JsonObject]) -> None:
    """Record every class declaration of one config text. The first wins."""
    for match in CLASS_DECL.finditer(text):
        name = match.group(1)
        if name in tree:
            continue
        line = text.count("\n", 0, match.start()) + 1
        tree[name] = {
            "class": name,
            "parent_class": match.group(2),
            "scope": _top_scope(_block(text, match.start())),
            "source_locator": f"{locator}:{line}",
        }


# --------------------------------------------------------------------------
# Inventory
# --------------------------------------------------------------------------


def _chain(tree: dict[str, JsonObject], name: str) -> list[str]:
    """Return the class and its ancestors, nearest first."""
    chain: list[str] = []
    seen: set[str] = set()
    current: str | None = name
    while current and current not in seen:
        chain.append(current)
        seen.add(current)
        record = tree.get(current)
        current = cast("str | None", record.get("parent_class")) if record else None
    return chain


def _air_token(tree: dict[str, JsonObject], name: str) -> str | None:
    """Return the nearest engine token of the class, or None when not air."""
    for cls in _chain(tree, name):
        if cls in AIR_TOKENS:
            return cls
    return None


def _effective_scope(tree: dict[str, JsonObject], name: str) -> int | None:
    """Return the class scope, inherited from the nearest ancestor that states one."""
    for cls in _chain(tree, name):
        record = tree.get(cls)
        if record is not None and record.get("scope") is not None:
            return cast("int", record["scope"])
    return None


def _family(tree: dict[str, JsonObject], name: str) -> str | None:
    """Return the variant family name of the class.

    The family base is the highest non-generic abstract base below the engine
    token. The family name drops the `_base_` suffix. A class with no family
    base takes the engine token as its family.
    """
    bases: list[str] = []
    for cls in _chain(tree, name)[1:]:
        if cls in AIR_TOKENS or cls in ENGINE_BASES:
            continue
        if BASE_SUFFIX.search(cls):
            bases.append(cls)
    if bases:
        return BASE_SUFFIX.sub("", bases[-1])
    return _air_token(tree, name)


def is_concrete(tree: dict[str, JsonObject], name: str) -> bool:
    """True when the class is a concrete air class a user can spawn."""
    if name in ENGINE_BASES or name in AIR_TOKENS:
        return False
    if BASE_SUFFIX.search(name):
        return False
    if PARACHUTE_NAMES & set(_chain(tree, name)):
        return False
    if _air_token(tree, name) is None:
        return False
    return _effective_scope(tree, name) in CONCRETE_SCOPES


def resolve_inventory(game_root: Path) -> JsonObject:
    """Resolve every air class from the installed config. Read the install once."""
    if not game_root.is_dir():
        raise ValueError(f"{game_root}: the game root is not a directory")
    with tempfile.TemporaryDirectory(prefix="aee-air-roster-") as scratch_name:
        texts = config_texts(game_root, Path(scratch_name))
    raw: dict[str, JsonObject] = {}
    for locator, text in texts:
        parse_declarations(text, locator, raw)
    classes: list[JsonObject] = []
    for name in sorted(raw):
        if _air_token(raw, name) is None:
            continue
        record = raw[name]
        locator = cast("str", record["source_locator"])
        classes.append(
            {
                "class": name,
                "parent_class": record.get("parent_class"),
                "class_token": _air_token(raw, name),
                "scope": record.get("scope"),
                "source_kind": "pbo_config" if " > " in locator else "game_config",
                "source_locator": locator,
            }
        )
    return {"schema": INVENTORY_SCHEMA, "classes": classes}


def load_inventory(path: Path) -> JsonObject:
    """Read a committed inventory. Raise when the shape is wrong."""
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: the inventory must be an object")
    payload = cast("JsonObject", loaded)
    if payload.get("schema") != INVENTORY_SCHEMA:
        raise ValueError(f"{path}: not a {INVENTORY_SCHEMA} artefact")
    if not isinstance(payload.get("classes"), list):
        raise ValueError(f"{path}: classes must be an array")
    return payload


# --------------------------------------------------------------------------
# Roster
# --------------------------------------------------------------------------


def build_roster(inventory: JsonObject) -> list[JsonObject]:
    """Derive one row per concrete air class from the inventory. No game read."""
    rows: list[JsonObject] = []
    records = cast("list[object]", inventory["classes"])
    tree: dict[str, JsonObject] = {}
    for item in records:
        if not isinstance(item, dict):
            raise TypeError("inventory class must be an object")
        record = cast("JsonObject", item)
        tree[cast("str", record["class"])] = record
    for name in sorted(tree):
        if not is_concrete(tree, name):
            continue
        token = _air_token(tree, name)
        family = _family(tree, name)
        is_base = False
        if family is not None:
            index = name.find(family)
            if index >= 0 and name[index:] == family + "_F":
                is_base = True
        record = tree[name]
        row: JsonObject = {
            "game_class": name,
            "class_token": token,
            "base_class": record.get("parent_class"),
            "variant_family": family,
            "role": "base" if is_base else "variant",
            "is_variant": not is_base,
        }
        if family is not None and family in NO_SOURCE_FAMILIES:
            row["no_source_reason"] = NO_SOURCE_FAMILIES[family]
        rows.append(row)
    return rows


def roster_errors(inventory: JsonObject, roster: list[JsonObject]) -> list[str]:
    """Return every roster contract error. An empty list is a clean guard."""
    errors: list[str] = []
    classes = cast("list[object]", inventory["classes"])
    known: dict[str, JsonObject] = {}
    for item in classes:
        if not isinstance(item, dict):
            errors.append("inventory class: must be an object")
            continue
        record = cast("JsonObject", item)
        name = record.get("class")
        if not isinstance(name, str) or not name:
            errors.append("inventory class: name is required")
            continue
        if name in known:
            errors.append(f"inventory class {name}: duplicate entry")
        known[name] = record
        if record.get("class_token") not in AIR_TOKENS:
            errors.append(f"inventory class {name}: not an air class")
    seen: set[str] = set()
    for row in roster:
        name = row.get("game_class")
        if not isinstance(name, str) or not name:
            errors.append("roster row: game_class is required")
            continue
        if name in seen:
            errors.append(f"roster class {name}: duplicate entry")
        seen.add(name)
        if name not in known:
            errors.append(f"roster class {name}: absent from the committed inventory")
            continue
        token = known[name].get("class_token")
        if token not in AIR_TOKENS:
            errors.append(f"roster class {name}: not an air class")
    return errors


def resolution_errors(
    roster: list[JsonObject], bindings: list[JsonObject]
) -> list[str]:
    """Return every roster class that is neither bound nor no_source.

    A roster class is resolved when a class binding names it, or when the
    roster row carries a ``no_source_reason``. A class that is neither is an
    unresolved gap and blocks the change.
    """
    bound = {
        cast("str", binding["game_class"])
        for binding in bindings
        if isinstance(binding, dict) and "game_class" in binding
    }
    errors: list[str] = []
    for row in roster:
        if not isinstance(row, dict):
            errors.append("roster row: must be an object")
            continue
        name = row.get("game_class")
        if name in bound:
            continue
        reason = row.get("no_source_reason")
        if isinstance(reason, str) and reason.strip():
            continue
        errors.append(f"roster class {name}: neither bound nor no_source")
    return errors


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def render_inventory(payload: JsonObject) -> str:
    """Return the exact on-disk text for an inventory payload."""
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_roster(rows: list[JsonObject]) -> str:
    """Return the exact on-disk text for a roster."""
    return json.dumps(rows, indent=2) + "\n"


def build_roster_report(inventory: JsonObject, rows: list[JsonObject]) -> str:
    """Render data/aircraft/ROSTER.md."""
    bases = sum(1 for row in rows if row.get("role") == "base")
    variants = len(rows) - bases
    no_source = sum(1 for row in rows if row.get("no_source_reason"))
    token_counts: dict[str, int] = {}
    for row in rows:
        token = cast("str", row.get("class_token"))
        token_counts[token] = token_counts.get(token, 0) + 1
    token_text = ", ".join(
        f"{token} {token_counts[token]}"
        for token in AIR_TOKENS
        if token in token_counts
    )
    lines = [
        "# Aircraft class roster",
        "",
        "Generated by `tools/validation/gen_aircraft_roster.py`. Do not edit",
        "by hand.",
        "",
        "The roster derives from `data/aircraft/class_inventory.json`. The",
        "inventory is resolved once from the installed air config. The roster",
        "derivation reads no game install.",
        "",
        "A concrete air class is an air class with an effective scope of 1 or 2",
        "that is not an abstract base. A base class name ends in `_base_` plus a",
        "letter. The engine places a parachute under `Helicopter`, so the roster",
        "excludes the parachute chain.",
        "",
        "The variant family is the highest family base below the engine token.",
        "The base member of a family is the member whose name is the family name",
        "plus `_F`. Every other member is a variant.",
        "",
        f"- Rows: {len(rows)}",
        f"- Base members: {bases}",
        f"- Variants: {variants}",
        f"- no_source rows: {no_source}",
        f"- Tokens: {token_text}",
        "",
        "## Roster",
        "",
        "| Game class | Token | Base class | Variant family | Role |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row.get('game_class', '')}` | {row.get('class_token', '')} | "
            f"`{row.get('base_class', '')}` | `{row.get('variant_family', '')}` | "
            f"{row.get('role', '')} |"
        )
    lines += [
        "",
        "## No-source classes",
        "",
        "A class with no real counterpart is `no_source`. It carries the reason",
        "in `roster.json`. No analogue is invented.",
        "",
        "| Game class | Variant family | Reason |",
        "|---|---|---|",
    ]
    for row in rows:
        reason = row.get("no_source_reason")
        if reason:
            lines.append(
                f"| `{row.get('game_class', '')}` | "
                f"`{row.get('variant_family', '')}` | {reason} |"
            )
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def write_all(data_dir: Path, inventory: JsonObject) -> list[JsonObject]:
    """Write the inventory, the roster and the report. Return the roster."""
    rows = build_roster(inventory)
    (data_dir / INVENTORY_OUT).write_text(render_inventory(inventory), encoding="utf-8")
    (data_dir / ROSTER_OUT).write_text(render_roster(rows), encoding="utf-8")
    (data_dir / ROSTER_REPORT).write_text(
        build_roster_report(inventory, rows), encoding="utf-8"
    )
    return rows


def check_all(data_dir: Path) -> int:
    """Return 0 when the committed artefacts match a fresh headless build."""
    inventory_path = data_dir / INVENTORY_OUT
    if not inventory_path.is_file():
        print(f"aircraft roster: {inventory_path} is missing; run the generator")
        return 1
    try:
        inventory = load_inventory(inventory_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"aircraft roster: cannot read the inventory: {exc}")
        return 1
    rows = build_roster(inventory)
    errors = roster_errors(inventory, rows)
    if errors:
        for error in errors:
            print(f"aircraft roster: {error}")
        return 1
    fresh = {
        ROSTER_OUT: render_roster(rows),
        ROSTER_REPORT: build_roster_report(inventory, rows),
    }
    stale = False
    for name, text in fresh.items():
        path = data_dir / name
        if not path.is_file():
            print(f"aircraft roster: {path} is missing; run the generator")
            stale = True
            continue
        if path.read_text(encoding="utf-8") != text:
            print(f"aircraft roster: {path} is stale; run the generator")
            stale = True
    if stale:
        return 1
    tokens = {cast("str", row["class_token"]) for row in rows}
    print(
        f"aircraft roster: {len(inventory['classes'])} inventory classes, "
        f"{len(rows)} roster rows, tokens {'/'.join(sorted(tokens))} (fresh)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive the aircraft class roster.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="Resolve the class inventory from the installed air config.",
    )
    parser.add_argument("--game-root", type=Path, default=None)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed artefacts are fresh. Write nothing.",
    )
    args = parser.parse_args(argv)
    if args.resolve:
        if args.game_root is None:
            print("aircraft roster: --resolve needs --game-root")
            return 1
        try:
            inventory = resolve_inventory(args.game_root)
        except (OSError, ValueError) as exc:
            print(f"aircraft roster: cannot resolve the inventory: {exc}")
            return 1
        args.data_dir.mkdir(parents=True, exist_ok=True)
        rows = write_all(args.data_dir, inventory)
        print(
            f"aircraft roster: resolved {len(inventory['classes'])} classes, "
            f"wrote {len(rows)} roster rows -> {args.data_dir}"
        )
        return 0
    if args.check:
        return check_all(args.data_dir)
    inventory_path = args.data_dir / INVENTORY_OUT
    try:
        inventory = load_inventory(inventory_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"aircraft roster: cannot read the inventory: {exc}")
        return 1
    rows = write_all(args.data_dir, inventory)
    print(f"aircraft roster: {len(rows)} roster rows -> {args.data_dir / ROSTER_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
