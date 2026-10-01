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
the loose game config and from the packed config of each vehicle addon.

Run:
    python3 tools/validation/gen_vehicle_bindings.py --resolve --game-root PATH
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
SCHEMA = "aee.vehicle.stringtable_bindings/1"

# The ground base class and the weapon family to exclude from a vehicle sweep.
GROUND_BASE = "LandVehicle"
STATIC_WEAPON = "StaticWeapon"

# A packed config of an addon that carries ground vehicles. The pattern keeps
# the resolve pass bounded to the addons that hold a vehicle class.
VEHICLE_ADDON = re.compile(r"(?:soft|armor|weapons)_f", re.IGNORECASE)

# A class declaration, with an optional parent, and its opening brace.
CLASS_DECL = re.compile(r"class\s+([A-Za-z_]\w*)\s*(?::\s*([A-Za-z_]\w*))?\s*\{")
DISPLAY_NAME = re.compile(r'displayName\s*=\s*"([^"]*)"')

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


def _loose_stringtables(game_root: Path) -> list[tuple[str, Path]]:
    """Return the game and repository stringtables, in a fixed order."""
    found: list[tuple[str, Path]] = []
    for path in sorted(game_root.rglob("stringtable.xml")):
        found.append((path.relative_to(game_root).as_posix(), path))
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
    """Extract one file from a packed file. Return its path, or None."""
    target = dest / (name.replace("/", "__").replace("\\", "__"))
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
    game_root: Path, scratch: Path
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

    for locator, path in _loose_stringtables(game_root):
        merge(locator, _stringtable_text(path))

    for pbo in _vehicle_pbos(game_root):
        names = _pbo_files(pbo)
        packed = [name for name in names if name.lower().endswith("stringtable.xml")]
        if not packed:
            continue
        relative = pbo.relative_to(game_root).as_posix()
        for name in packed:
            extracted = _extract(pbo, name, scratch)
            if extracted is None:
                continue
            merge(f"{relative} > {name}", _stringtable_text(extracted))
    return texts, sources


# --- game config ----------------------------------------------------------


def _vehicle_pbos(game_root: Path) -> list[Path]:
    """Return the packed addons that can hold a ground vehicle config."""
    found = [p for p in game_root.rglob("*.pbo") if VEHICLE_ADDON.search(p.name)]
    return sorted(found, key=lambda path: path.as_posix())


def _config_texts(game_root: Path, scratch: Path) -> list[tuple[str, str]]:
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
    for pbo in _vehicle_pbos(game_root):
        relative = pbo.relative_to(game_root).as_posix()
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
                        f"{relative} > {name}",
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
            tree[name] = ClassRecord(
                parent=match.group(2),
                display_name=display.group(1) if display else None,
                locator=locator,
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
    """Split a resolved display name into normalised match tokens."""
    tokens = [catalogue.normalise(word) for word in TOKEN_SPLIT.split(text)]
    return [token for token in tokens if len(token) >= SCAN_MIN]


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


def build_bindings(game_root: Path, vehicle_dir: Path, scratch: Path) -> list[Binding]:
    """Return every ground class the stringtable names to one catalogue entry."""
    texts, sources = build_stringtable_map(game_root, scratch)
    tree = parse_class_tree(_config_texts(game_root, scratch))
    load = catalogue.load(vehicle_dir)
    index = build_token_index(load)
    bindings: list[Binding] = []
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
        bindings.append(
            Binding(
                game_class=game_class,
                display_name_key=raw,
                display_name=text,
                display_name_source=sources.get(raw.lstrip("$").strip().lower(), ""),
                config_locator=config_locator,
                catalogue_id=catalogue_id,
                matched_tokens=tokens,
            )
        )
    bindings.sort(key=lambda binding: binding.game_class)
    return bindings


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


def check_bindings(path: Path, vehicle_dir: Path) -> int:
    """Return 0 when the artefact matches a fresh decision from its own data.

    The check is deterministic and reads no game install. It rebuilds each
    binding from the committed display name and the catalogue, and compares the
    catalogue entry and the matched tokens.
    """
    try:
        records = load_bindings(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"stringtable bindings: cannot read the artefact: {exc}")
        return 1
    load = catalogue.load(vehicle_dir)
    index = build_token_index(load)
    seen: set[str] = set()
    stale = False
    for index_number, record in enumerate(records):
        game_class = _text(record.get("game_class"))
        text = _text(record.get("display_name"))
        if game_class is None or text is None:
            print(
                f"stringtable bindings: binding[{index_number}] lacks a class or name"
            )
            stale = True
            continue
        if game_class in seen:
            print(f"stringtable bindings: {game_class} repeats")
            stale = True
        seen.add(game_class)
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
        "--check",
        action="store_true",
        help="Verify the committed artefact is fresh. Write nothing.",
    )
    args = parser.parse_args(argv)

    if args.check:
        return check_bindings(args.out, args.vehicle_dir)

    if args.resolve:
        if args.game_root is None:
            print("stringtable bindings: --resolve needs --game-root")
            return 2
        if not args.game_root.is_dir():
            print(f"stringtable bindings: {args.game_root} is not a directory")
            return 1
        try:
            with tempfile.TemporaryDirectory() as tmp:
                bindings = build_bindings(args.game_root, args.vehicle_dir, Path(tmp))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"stringtable bindings: cannot resolve: {exc}")
            return 1
        write_bindings(bindings, args.out)
        print(f"stringtable bindings: {len(bindings)} records -> {args.out}")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
