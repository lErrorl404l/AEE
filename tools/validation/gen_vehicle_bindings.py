#!/usr/bin/env python3
"""Resolve vanilla vehicle display names to catalogue entries.

A vanilla CfgVehicles class stores a localisation key in ``displayName``, for
example ``$STR_A3_CfgVehicles_B_Truck_01_primemover0``. The text behind the key
is the name the user sees, for example ``HEMTT``. This generator reads the game
stringtables, resolves each ground class displayName to that text, and matches
the text against the vehicle catalogue.

The output is a generated, committed artefact,
``data/vehicle/stringtable_bindings.json``. Each record holds the game class,
the raw displayName key, the resolved text, the stringtable file and key that
resolved it, and the catalogue entry the text names. The record carries
provenance and no invented value.

A class whose displayName does not resolve is not bound. A text that names more
than one catalogue entry is ambiguous and is not bound. The generator guesses
nothing.

Enumeration reads the installed game config. The displayName key is read from
the class, or from the nearest parent that states one. The class tree comes from
the loose game config and from the packed config of each vehicle addon. A mod
that carries ground vehicles is read the same way: pass it with ``--mod-root``.
The display name of a mod vehicle is often the real vehicle designation, so it
resolves to a catalogue entry without a class map.

Run:
    python3 tools/validation/gen_vehicle_bindings.py --resolve --game-root PATH
    python3 tools/validation/gen_vehicle_bindings.py --resolve --game-root PATH \\
        --mod-root PATH [--mod-root PATH ...]
    python3 tools/validation/gen_vehicle_bindings.py --check
Exit: 0 when fresh, 1 when stale or missing under --check.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

DEFAULT_OUT = REPO / "data" / "vehicle" / "stringtable_bindings.json"
DEFAULT_VEHICLE_DIR = REPO / "data" / "vehicle"
DEFAULT_CLASS_BINDINGS = REPO / "data" / "vehicle" / "fleet" / "class_binding_map.json"
SCHEMA = "aee.vehicle.stringtable_bindings/1"
CLASS_BINDING_SCHEMA = "aee.vehicle.class_binding_map/1"

# The provenance label of an explicit fleet class binding, taken from the map.
CLASS_BINDING_SOURCE = "data/vehicle/fleet/class_binding_map.json"

# The ground base class and the weapon family to exclude from a vehicle sweep.
GROUND_BASE = "LandVehicle"
STATIC_WEAPON = "StaticWeapon"

# A packed config of an addon that carries ground vehicles. The pattern keeps
# the resolve pass bounded to the addons that hold a vehicle class.
VEHICLE_ADDON = re.compile(r"(?:soft|armor|weapons)_f", re.IGNORECASE)

# A class declaration, with an optional parent, and its opening brace.
CLASS_DECL = re.compile(r"class\s+([A-Za-z_]\w*)\s*(?::\s*([A-Za-z_]\w*))?\s*\{")
DISPLAY_NAME = re.compile(r'displayName\s*=\s*"([^"]*)"')
# The engine mass of a class. It is an identity hint only, never a value source.
MASS_VALUE = re.compile(r"\bmass\s*=\s*([0-9.]+)\s*;")
# A trailing parenthetical qualifier in a display name: the production year, the
# armament or the trim. It is not part of the vehicle designation.
PARENTHETICAL = re.compile(r"\([^)]*\)")

# The shortest token the matcher accepts, as the runtime matcher does.
SCAN_MIN = 4
TOKEN_SPLIT = re.compile(r"[^A-Za-z0-9]+")

# The locale element order. Original is authoritative; English is the fallback.
LOCALE_ORDER = ("Original", "English")


@dataclass(frozen=True)
class Binding:
    """One game class bound to a catalogue entry, with provenance."""

    game_class: str
    display_name_key: str
    display_name: str
    display_name_source: str
    config_locator: str
    catalogue_id: str
    matched_tokens: tuple[str, ...]

    def to_mapping(self) -> dict[str, object]:
        return {
            "game_class": self.game_class,
            "display_name_key": self.display_name_key,
            "display_name": self.display_name,
            "display_name_source": self.display_name_source,
            "config_locator": self.config_locator,
            "catalogue_id": self.catalogue_id,
            "matched_tokens": list(self.matched_tokens),
        }


@dataclass(frozen=True)
class ClassRecord:
    """One class node of the game config with its provenance."""

    parent: str | None
    display_name: str | None
    locator: str
    mass: float | None = None


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


# --- stringtables ---------------------------------------------------------


def _stringtable_text(path: Path) -> dict[str, str]:
    """Return the key to text map of one stringtable file."""
    out: dict[str, str] = {}
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return out
    for key in root.iter("Key"):
        key_id = (key.get("ID") or "").strip().lower()
        if not key_id or key_id in out:
            continue
        text = ""
        for locale in LOCALE_ORDER:
            node = key.find(locale)
            if node is not None and (node.text or "").strip():
                text = (node.text or "").strip()
                break
        if text:
            out[key_id] = text
    return out


def _loose_stringtables(
    game_root: Path, mod_roots: Sequence[Path] = ()
) -> list[tuple[str, Path]]:
    """Return the game, mod and repository stringtables, in a fixed order."""
    found: list[tuple[str, Path]] = []
    for path in sorted(game_root.rglob("stringtable.xml")):
        found.append((path.relative_to(game_root).as_posix(), path))
    for root in mod_roots:
        base = root.name or root.as_posix()
        for path in sorted(root.rglob("stringtable.xml")):
            found.append((f"{base}/{path.relative_to(root).as_posix()}", path))
    for path in sorted((REPO / "addons").rglob("stringtable.xml")):
        found.append((path.relative_to(REPO).as_posix(), path))
    return found


def _run_hemtt(argv: list[str]) -> bool:
    try:
        result = subprocess.run(
            ["hemtt", *argv], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0


def _pbo_files(pbo: Path) -> list[str]:
    """Return the file names inside a packed file, or an empty list."""
    try:
        result = subprocess.run(
            ["hemtt", "utils", "pbo", "inspect", str(pbo)],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    if result.returncode != 0:
        return []
    names: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split("\u2502")
        if len(parts) >= 2:
            name = parts[1].strip()
            if name:
                names.append(name)
    return names


def _extract(pbo: Path, name: str, dest: Path) -> Path | None:
    """Extract one file from a packed file. Return its path, or None.

    The target name carries the packed file name so two addons that hold a
    file at the same internal path do not collide in the scratch directory.
    """
    target = dest / (pbo.name + "__" + name.replace("/", "__").replace("\\", "__"))
    target.parent.mkdir(parents=True, exist_ok=True)
    if not _run_hemtt(["utils", "pbo", "extract", str(pbo), name, str(target)]):
        return None
    return target if target.is_file() and target.stat().st_size else None


def _derapify(binary: Path, dest: Path) -> Path | None:
    """Convert a packed config to a readable config. Return its path, or None."""
    target = dest / (binary.name + ".cpp")
    if not _run_hemtt(
        ["utils", "config", "derapify", "-f", "cpp", str(binary), str(target)]
    ):
        return None
    return target if target.is_file() and target.stat().st_size else None


def build_stringtable_map(
    game_root: Path, scratch: Path, mod_roots: Sequence[Path] = ()
) -> tuple[dict[str, str], dict[str, str]]:
    """Return the key to text map and the key to source-locator map.

    The loose files answer first. A key that only a packed file holds is
    unpacked and read. The first readable source wins, so the result is
    deterministic.
    """
    texts: dict[str, str] = {}
    sources: dict[str, str] = {}

    def merge(locator: str, table: dict[str, str]) -> None:
        for key, value in table.items():
            if key not in texts:
                texts[key] = value
                sources[key] = locator

    for locator, path in _loose_stringtables(game_root, mod_roots):
        merge(locator, _stringtable_text(path))

    for locator, pbo in _scan_pbos(game_root, mod_roots):
        names = _pbo_files(pbo)
        packed = [name for name in names if name.lower().endswith("stringtable.xml")]
        if not packed:
            continue
        for name in packed:
            extracted = _extract(pbo, name, scratch)
            if extracted is None:
                continue
            merge(f"{locator} > {name}", _stringtable_text(extracted))
    return texts, sources


# --- game config ----------------------------------------------------------


def _scan_pbos(
    game_root: Path, mod_roots: Sequence[Path] = ()
) -> list[tuple[str, Path]]:
    """Return (locator, packed addon) for the game and each mod root.

    The game root keeps the bounded addon pattern, so the pass stays cheap.
    A mod root is scanned for every packed addon, because a mod names its own
    addons and the vehicle config can live in any of them. The locator is
    relative to the root that holds the addon, so provenance survives.
    """
    found: list[tuple[str, Path]] = []
    for pbo in game_root.rglob("*.pbo"):
        if VEHICLE_ADDON.search(pbo.name):
            found.append((pbo.relative_to(game_root).as_posix(), pbo))
    for root in mod_roots:
        base = root.name or root.as_posix()
        for pbo in root.rglob("*.pbo"):
            found.append((f"{base}/{pbo.relative_to(root).as_posix()}", pbo))
    found.sort(key=lambda item: item[1].as_posix())
    return found


def _config_texts(
    game_root: Path, scratch: Path, mod_roots: Sequence[Path] = ()
) -> list[tuple[str, str]]:
    """Return the locator and text of every readable game config file.

    The loose files answer first. The packed config of a vehicle addon is
    unpacked and derapified.
    """
    found: list[tuple[str, str]] = []
    for path in sorted(game_root.rglob("config.cpp")):
        try:
            found.append(
                (
                    path.relative_to(game_root).as_posix(),
                    path.read_text(encoding="utf-8", errors="replace"),
                )
            )
        except OSError:
            continue
    for root in mod_roots:
        base = root.name or root.as_posix()
        for path in sorted(root.rglob("config.cpp")):
            try:
                found.append(
                    (
                        f"{base}/{path.relative_to(root).as_posix()}",
                        path.read_text(encoding="utf-8", errors="replace"),
                    )
                )
            except OSError:
                continue
    for locator, pbo in _scan_pbos(game_root, mod_roots):
        for name in _pbo_files(pbo):
            if not name.endswith("config.bin"):
                continue
            binary = _extract(pbo, name, scratch)
            if binary is None:
                continue
            text = _derapify(binary, scratch)
            if text is None:
                continue
            try:
                found.append(
                    (
                        f"{locator} > {name}",
                        text.read_text(encoding="utf-8", errors="replace"),
                    )
                )
            except OSError:
                continue
    return found


def parse_class_tree(
    config_texts: Sequence[tuple[str, str]],
) -> dict[str, ClassRecord]:
    """Return the class tree with the parent and displayName of each class.

    A class is recorded once. The first declaration wins, so the result is
    deterministic. A parent and a displayName are recorded only when the class
    states them.
    """
    tree: dict[str, ClassRecord] = {}
    for locator, text in config_texts:
        for match in CLASS_DECL.finditer(text):
            name = match.group(1)
            if name in tree:
                continue
            depth = 0
            index = match.end() - 1
            while index < len(text):
                if text[index] == "{":
                    depth += 1
                elif text[index] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                index += 1
            block = text[match.end() : index]
            display = DISPLAY_NAME.search(block)
            mass = MASS_VALUE.search(block)
            tree[name] = ClassRecord(
                parent=match.group(2),
                display_name=display.group(1) if display else None,
                locator=locator,
                mass=float(mass.group(1)) if mass else None,
            )
    return tree


def is_kind_of(tree: dict[str, ClassRecord], name: str, base: str) -> bool:
    """True when the class or a parent chain reaches the base class."""
    seen: set[str] = set()
    current: str | None = name
    while current and current not in seen:
        if current == base:
            return True
        seen.add(current)
        record = tree.get(current)
        current = record.parent if record is not None else None
    return False


def ground_classes(tree: dict[str, ClassRecord]) -> list[str]:
    """Return the ground vehicle classes of the tree, sorted.

    A ground class is a LandVehicle that is not a StaticWeapon. The engine
    places static emplacements under LandVehicle, so the weapon family is
    excluded.
    """
    if GROUND_BASE not in tree:
        return []
    found = [
        name
        for name in tree
        if is_kind_of(tree, name, GROUND_BASE)
        and not is_kind_of(tree, name, STATIC_WEAPON)
    ]
    return sorted(found)


def resolve_display_name(
    tree: dict[str, ClassRecord], name: str
) -> tuple[str, str] | None:
    """Return the (key, locator) of the nearest stated displayName, or None."""
    seen: set[str] = set()
    current: str | None = name
    while current and current not in seen:
        seen.add(current)
        record = tree.get(current)
        if record is None:
            return None
        if record.display_name:
            return record.display_name, record.locator
        current = record.parent
    return None


# --- catalogue matching ---------------------------------------------------


def build_token_index(
    load: catalogue.CatalogueLoad,
) -> dict[str, set[str]]:
    """Map each catalogue identity token to the entries that own it."""
    index: dict[str, set[str]] = {}
    for entry in load.entries:
        tokens = set(entry.identity_aliases())
        tokens.add(catalogue.normalise(entry.canonical_name))
        tokens.add(catalogue.normalise(entry.model))
        tokens |= set(entry.keywords)
        for token in tokens:
            if token:
                index.setdefault(token, set()).add(entry.catalogue_id)
    return index


def display_tokens(text: str) -> list[str]:
    """Split a resolved display name into normalised match tokens.

    The words of the name are tokens, as the runtime matcher takes them. The
    whole name is also a token: a mod display name is often the real vehicle
    designation (``Ural-4320``), which names one entry as one string and must
    not be split into a maker word and a number. A trailing parenthetical
    qualifier is dropped first, so ``BMP-2 (obr. 1986g.)`` keeps ``BMP-2``.
    """
    tokens = [catalogue.normalise(word) for word in TOKEN_SPLIT.split(text)]
    keys = [token for token in tokens if len(token) >= SCAN_MIN]
    whole = catalogue.normalise(PARENTHETICAL.sub(" ", text))
    if len(whole) >= SCAN_MIN and whole not in keys:
        keys.append(whole)
    return keys


def match_display_name(
    text: str, index: dict[str, set[str]]
) -> tuple[str, tuple[str, ...]] | None:
    """Return the unique catalogue entry a display name names, or None.

    Every token of the text is looked up. The candidates are the union of the
    owning entries. Exactly one owner is a binding. No owner, or more than one,
    is no binding. A generic word such as Truck names many entries, so it binds
    nothing.
    """
    owners: set[str] = set()
    matches: set[str] = set()
    for token in display_tokens(text):
        found = index.get(token)
        if found:
            owners |= found
            matches.add(token)
    if len(owners) != 1:
        return None
    return next(iter(owners)), tuple(sorted(matches))


def _lookup_key(texts: dict[str, str], raw: str) -> str | None:
    """Resolve a raw displayName value. Strip the marker and a digit suffix."""
    key = raw.lstrip("$").strip().lower()
    if key in texts:
        return texts[key]
    return texts.get(re.sub(r"\d+$", "", key))


# --- artefact -------------------------------------------------------------


def build_bindings(
    game_root: Path,
    vehicle_dir: Path,
    scratch: Path,
    mod_roots: Sequence[Path] = (),
    class_bindings: Sequence[dict[str, object]] = (),
) -> list[Binding]:
    """Return every ground class the stringtable names to one catalogue entry.

    The explicit class-binding map is applied after the display-name pass. It
    names a concrete game class the display name does not resolve, so a fleet
    class with an empty or unhelpful display name still binds. An explicit
    record overrides a display-name record for the same class.
    """
    texts, sources = build_stringtable_map(game_root, scratch, mod_roots)
    tree = parse_class_tree(_config_texts(game_root, scratch, mod_roots))
    load = catalogue.load(vehicle_dir)
    index = build_token_index(load)
    by_class: dict[str, Binding] = {}
    for game_class in ground_classes(tree):
        resolved = resolve_display_name(tree, game_class)
        if resolved is None:
            continue
        raw, config_locator = resolved
        text = _lookup_key(texts, raw)
        if text is None:
            continue
        matched = match_display_name(text, index)
        if matched is None:
            continue
        catalogue_id, tokens = matched
        by_class[game_class] = Binding(
            game_class=game_class,
            display_name_key=raw,
            display_name=text,
            display_name_source=sources.get(raw.lstrip("$").strip().lower(), ""),
            config_locator=config_locator,
            catalogue_id=catalogue_id,
            matched_tokens=tokens,
        )
    known = {entry.catalogue_id for entry in load.entries}
    for record in class_bindings:
        game_class = _text(record.get("game_class"))
        catalogue_id = _text(record.get("catalogue_id"))
        if game_class is None or catalogue_id is None or catalogue_id not in known:
            continue
        existing = by_class.get(game_class)
        if existing is not None and existing.catalogue_id == catalogue_id:
            # The display name already binds the class to the same entry.
            continue
        by_class[game_class] = Binding(
            game_class=game_class,
            display_name_key="",
            display_name="",
            display_name_source=CLASS_BINDING_SOURCE,
            config_locator="",
            catalogue_id=catalogue_id,
            matched_tokens=(),
        )
    return sorted(by_class.values(), key=lambda binding: binding.game_class)


def render_bindings(bindings: Sequence[Binding]) -> str:
    """Return the exact on-disk text of the binding artefact."""
    payload = {
        "schema": SCHEMA,
        "bindings": [binding.to_mapping() for binding in bindings],
    }
    return json.dumps(payload, indent=2) + "\n"


def load_bindings(path: Path) -> list[dict[str, object]]:
    """Read the committed artefact. Return its records."""
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    payload = _mapping(loaded)
    if payload is None or payload.get("schema") != SCHEMA:
        raise ValueError(f"{path}: not a {SCHEMA} artefact")
    records = payload.get("bindings")
    if not isinstance(records, list):
        raise ValueError(f"{path}: bindings must be an array")
    out: list[dict[str, object]] = []
    for index, raw in enumerate(records):
        record = _mapping(raw)
        if record is None:
            raise ValueError(f"{path}: binding[{index}] must be an object")
        out.append(record)
    return out


def load_class_bindings(path: Path) -> list[dict[str, object]]:
    """Read the explicit fleet class-binding map.

    The map binds one concrete game class to one catalogue entry for a fleet
    whose display name does not resolve offline. It is an input to the
    resolver, so a class whose display name is empty or unhelpful still binds.
    A missing map yields no explicit bindings, so the resolver still runs.
    """
    if not path.is_file():
        return []
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    payload = _mapping(loaded)
    if payload is None or payload.get("schema") != CLASS_BINDING_SCHEMA:
        raise ValueError(f"{path}: not a {CLASS_BINDING_SCHEMA} artefact")
    records = payload.get("bindings")
    if not isinstance(records, list):
        raise ValueError(f"{path}: bindings must be an array")
    out: list[dict[str, object]] = []
    for index, raw in enumerate(records):
        record = _mapping(raw)
        if record is None:
            raise ValueError(f"{path}: class binding[{index}] must be an object")
        out.append(record)
    return out


def check_bindings(
    path: Path,
    vehicle_dir: Path,
    class_bindings: Sequence[dict[str, object]] = (),
) -> int:
    """Return 0 when the artefact matches a fresh decision from its own data.

    The check is deterministic and reads no game install. It rebuilds each
    display-name binding from the committed display name and the catalogue,
    and verifies each explicit binding against the class-binding map. It
    compares the catalogue entry and the matched tokens.
    """
    try:
        records = load_bindings(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"stringtable bindings: cannot read the artefact: {exc}")
        return 1
    load = catalogue.load(vehicle_dir)
    index = build_token_index(load)
    known = {entry.catalogue_id for entry in load.entries}
    explicit: dict[str, str] = {}
    for record in class_bindings:
        explicit_class = _text(record.get("game_class"))
        explicit_id = _text(record.get("catalogue_id"))
        if explicit_class is not None and explicit_id is not None:
            explicit[explicit_class] = explicit_id
    seen: set[str] = set()
    stale = False
    for index_number, record in enumerate(records):
        game_class = _text(record.get("game_class"))
        text = _text(record.get("display_name"))
        if game_class is None:
            print(f"stringtable bindings: binding[{index_number}] lacks a class")
            stale = True
            continue
        if game_class in seen:
            print(f"stringtable bindings: {game_class} repeats")
            stale = True
        seen.add(game_class)
        if text is None:
            catalogue_id = record.get("catalogue_id")
            if explicit.get(game_class) != catalogue_id or catalogue_id not in known:
                print(f"stringtable bindings: {game_class} explicit binding is stale")
                stale = True
            continue
        if game_class in explicit and explicit[game_class] != record.get(
            "catalogue_id"
        ):
            print(
                f"stringtable bindings: {game_class} class-binding map disagrees; stale"
            )
            stale = True
            continue
        matched = match_display_name(text, index)
        if matched is None:
            print(
                f"stringtable bindings: {game_class} [{text}] no longer names one entry"
            )
            stale = True
            continue
        catalogue_id, tokens = matched
        if record.get("catalogue_id") != catalogue_id:
            print(f"stringtable bindings: {game_class} names {catalogue_id}, stale")
            stale = True
        if list(record.get("matched_tokens") or []) != list(tokens):
            print(f"stringtable bindings: {game_class} matched tokens are stale")
            stale = True
    if stale:
        return 1
    print(f"stringtable bindings: {len(records)} records -> {path} (fresh)")
    return 0


@dataclass(frozen=True)
class FleetRecord:
    """One ground class of a game or mod config, with provenance.

    It is an inventory record. It carries identity evidence and an engine mass
    hint only. The mass is an identity hint, never a real-world value source.
    """

    game_class: str
    parent: str
    vehicle_type: str
    display_name_key: str
    display_name: str
    display_name_source: str
    mass_hint: float | None
    config_locator: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "game_class": self.game_class,
            "parent": self.parent,
            "vehicle_type": self.vehicle_type,
            "display_name_key": self.display_name_key,
            "display_name": self.display_name,
            "display_name_source": self.display_name_source,
            "mass_hint": self.mass_hint,
            "config_locator": self.config_locator,
        }


FLEET_SCHEMA = "aee.vehicle.mod_fleet/1"


def build_fleet(
    game_root: Path,
    scratch: Path,
    mod_roots: Sequence[Path] = (),
) -> list[FleetRecord]:
    """Return one inventory record per ground class of the mod roots.

    When a mod root is given the sweep is restricted to classes the mod roots
    declare, so the artefact is the mod fleet. With no mod root it is the whole
    game fleet.
    """
    texts, sources = build_stringtable_map(game_root, scratch, mod_roots)
    tree = parse_class_tree(_config_texts(game_root, scratch, mod_roots))
    prefixes = tuple(f"{root.name or root.as_posix()}/" for root in mod_roots)
    records: list[FleetRecord] = []
    for game_class in ground_classes(tree):
        record = tree[game_class]
        if prefixes and not record.locator.startswith(prefixes):
            continue
        resolved = resolve_display_name(tree, game_class)
        raw = resolved[0] if resolved is not None else ""
        locator = resolved[1] if resolved is not None else record.locator
        text = _lookup_key(texts, raw) if raw else None
        vehicle_type = "tracked" if is_kind_of(tree, game_class, "Tank") else "wheeled"
        records.append(
            FleetRecord(
                game_class=game_class,
                parent=record.parent or "",
                vehicle_type=vehicle_type,
                display_name_key=raw,
                display_name=text or "",
                display_name_source=sources.get(raw.lstrip("$").strip().lower(), ""),
                mass_hint=record.mass,
                config_locator=locator,
            )
        )
    records.sort(key=lambda item: item.game_class)
    return records


def render_fleet(records: Sequence[FleetRecord]) -> str:
    """Return the exact on-disk text of the fleet inventory artefact."""
    payload = {
        "schema": FLEET_SCHEMA,
        "records": [record.to_mapping() for record in records],
    }
    return json.dumps(payload, indent=2) + "\n"


def write_bindings(bindings: Sequence[Binding], path: Path) -> None:
    """Write the binding artefact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_bindings(bindings), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve vanilla display names to catalogue entries."
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--vehicle-dir", type=Path, default=DEFAULT_VEHICLE_DIR)
    parser.add_argument(
        "--class-bindings",
        type=Path,
        default=DEFAULT_CLASS_BINDINGS,
        help="The explicit fleet class-binding map. Default is the committed map.",
    )
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="Read the game install and write the binding artefact.",
    )
    parser.add_argument(
        "--game-root",
        type=Path,
        help="Path to the installed Arma 3 directory for --resolve.",
    )
    parser.add_argument(
        "--mod-root",
        type=Path,
        action="append",
        default=[],
        help="Path to an installed mod root for --resolve. Repeatable.",
    )
    parser.add_argument(
        "--fleet-out",
        type=Path,
        help="Write the ground class inventory of the resolved roots here.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed artefact is fresh. Write nothing.",
    )
    args = parser.parse_args(argv)

    try:
        class_bindings = load_class_bindings(args.class_bindings)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"stringtable bindings: cannot read the class-binding map: {exc}")
        return 1

    if args.check:
        return check_bindings(args.out, args.vehicle_dir, class_bindings)

    if args.resolve:
        if args.game_root is None:
            print("stringtable bindings: --resolve needs --game-root")
            return 2
        if not args.game_root.is_dir():
            print(f"stringtable bindings: {args.game_root} is not a directory")
            return 1
        for mod_root in args.mod_root:
            if not mod_root.is_dir():
                print(f"stringtable bindings: {mod_root} is not a directory")
                return 1
        try:
            with tempfile.TemporaryDirectory() as tmp:
                scratch = Path(tmp)
                bindings = build_bindings(
                    args.game_root,
                    args.vehicle_dir,
                    scratch,
                    args.mod_root,
                    class_bindings,
                )
                fleet = (
                    build_fleet(args.game_root, scratch, args.mod_root)
                    if args.fleet_out is not None
                    else None
                )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"stringtable bindings: cannot resolve: {exc}")
            return 1
        write_bindings(bindings, args.out)
        print(f"stringtable bindings: {len(bindings)} records -> {args.out}")
        if fleet is not None and args.fleet_out is not None:
            args.fleet_out.parent.mkdir(parents=True, exist_ok=True)
            args.fleet_out.write_text(render_fleet(fleet), encoding="utf-8")
            print(
                f"stringtable bindings: {len(fleet)} fleet records -> {args.fleet_out}"
            )
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
