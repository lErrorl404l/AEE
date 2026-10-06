#!/usr/bin/env python3
"""Generate the per-optic thermal config block from the device corpus.

The device corpus holds one entry per real thermal device. An entry carries a
graded value row. The authored class bindings under
``data/device/class_bindings.json`` link one real Arma optic class to one
corpus device. This generator reads both and writes one ``class CfgWeapons``
patch block:

  addons/thermal/generated/ThermalOptics.hpp

The block declares ``thermalMode[]``, ``thermalNoise[]`` and
``thermalResolution[]`` on each bound optic, under
``CfgWeapons >> <optic> >> ItemInfo >> OpticsModes >> <mode>``. That path is
the verified vanilla path in the derap
``/tmp/opencode/ti-research/v2/weapons_f/acc/config.cpp`` (``optic_tws`` line
1026, ``optic_Nightstalker`` line 986, ``optic_tws_mg`` line 1069).

The generator fails closed. A binding with no corpus row, or with no held
``netd_c``, ``resolution_x`` or ``resolution_y``, emits no declaration. The
generator never invents a value. It reads the corpus and the bindings only.

``thermalMode[]`` is the one declared constant: the engine-minimum palette
pair WHOT (0) and BHOT (1). It is not a corpus figure. Every other emitted
number is derived from a corpus row and its formula is named in the header.

Run:  python3 tools/validation/gen_thermal_optics.py
      python3 tools/validation/gen_thermal_optics.py --check
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation import device_catalogue as catalogue  # noqa: E402

ROOT = _REPO
DEFAULT_DATA = ROOT / "data" / "device"
DEFAULT_BINDINGS = DEFAULT_DATA / "class_bindings.json"
OUT = ROOT / "addons" / "thermal" / "generated" / "ThermalOptics.hpp"

# The engine-minimum palette pair. 0 is WHOT and 1 is BHOT, per the thermal
# mode table in docs/wiki/research/engine-thermal-mechanisms.md.
THERMAL_MODE_PAIR = (0, 1)

# The corpus figures a declaration needs. A missing figure fails closed.
REQUIRED_FIGURES = ("netd_c", "resolution_x", "resolution_y")

# The keys a binding record carries.
BINDING_FIELDS = (
    "game_class",
    "catalogue_id",
    "optic_mode",
    "identity_source",
    "identity_evidence",
    "grade",
)


@dataclass(frozen=True)
class Binding:
    """One authored link from a real Arma optic class to a corpus device."""

    game_class: str
    catalogue_id: str
    optic_mode: str
    identity_source: str
    identity_evidence: str
    grade: str


def load_thermal(data_dir: Path = DEFAULT_DATA) -> dict[str, catalogue.DeviceEntry]:
    """Return the thermal entries of the corpus, keyed by device id."""
    load = catalogue.load(data_dir)
    return {
        entry.device_id: entry for entry in load.entries if entry.family == "thermal"
    }


def load_bindings(path: Path = DEFAULT_BINDINGS) -> tuple[list[Binding], list[str]]:
    """Read the authored class bindings. Return the bindings and the errors."""
    errors: list[str] = []
    if not path.is_file():
        return [], [f"{path}: the class bindings file is missing"]
    import json

    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"{path}: {exc}"]
    if not isinstance(loaded, list):
        return [], [f"{path}: the class bindings must be a top-level array"]

    bindings: list[Binding] = []
    seen: set[str] = set()
    for index, raw in enumerate(loaded):
        if not isinstance(raw, dict):
            errors.append(f"{path}: binding {index} is not an object")
            continue
        record = {str(key): value for key, value in raw.items()}
        missing = [key for key in BINDING_FIELDS if not _text(record.get(key))]
        if missing:
            errors.append(f"{path}: binding {index} is missing {', '.join(missing)}")
            continue
        game_class = str(record["game_class"])
        if game_class in seen:
            errors.append(f"{path}: duplicate game_class {game_class}")
            continue
        seen.add(game_class)
        bindings.append(
            Binding(
                game_class=game_class,
                catalogue_id=str(record["catalogue_id"]),
                optic_mode=str(record["optic_mode"]),
                identity_source=str(record["identity_source"]),
                identity_evidence=str(record["identity_evidence"]),
                grade=str(record["grade"]),
            )
        )
    return bindings, errors


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _number(value: object) -> str | None:
    """Render a held corpus figure as an SQF number, or None when absent."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:g}"
    return None


def _held(entry: catalogue.DeviceEntry, field: str) -> object | None:
    held = catalogue.held_value(entry.values, field)
    if held is None:
        return None
    return held.get("value")


def build_declaration(
    binding: Binding, entries: dict[str, catalogue.DeviceEntry]
) -> str | None:
    """Return one optic patch declaration, or None when the binding fails closed.

    A binding fails closed when the corpus holds no row for its catalogue id,
    or when the row holds no figure for netd_c, resolution_x or resolution_y.
    """
    entry = entries.get(binding.catalogue_id)
    if entry is None:
        return None

    netd = _number(_held(entry, "netd_c"))
    res_x = _number(_held(entry, "resolution_x"))
    res_y = _number(_held(entry, "resolution_y"))
    if netd is None or res_x is None or res_y is None:
        return None

    mode = ", ".join(str(item) for item in THERMAL_MODE_PAIR)
    lines = [
        f"    class {binding.game_class} {{",
        "        class ItemInfo {",
        "            class OpticsModes {",
        f"                class {binding.optic_mode} {{",
        f"                    thermalMode[] = {{{mode}}};",
        f"                    thermalNoise[] = {{{netd}}};",
        f"                    thermalResolution[] = {{{res_x}, {res_y}}};",
        "                };",
        "            };",
        "        };",
        "    };",
    ]
    return "\n".join(lines)


def _skipped(binding: Binding, entries: dict[str, catalogue.DeviceEntry]) -> str | None:
    """Return the fail-closed reason for a binding, or None when it emits."""
    entry = entries.get(binding.catalogue_id)
    if entry is None:
        return f"{binding.game_class}: no corpus row for {binding.catalogue_id}"
    missing = [field for field in REQUIRED_FIGURES if _held(entry, field) is None]
    if missing:
        return (
            f"{binding.game_class}: {binding.catalogue_id} holds no "
            f"{', '.join(missing)}"
        )
    return None


def render(
    data_dir: Path = DEFAULT_DATA, bindings_path: Path = DEFAULT_BINDINGS
) -> str:
    """Render the full generated header."""
    entries = load_thermal(data_dir)
    bindings, errors = load_bindings(bindings_path)
    if errors:
        raise SystemExit("\n".join(errors))

    declarations: list[str] = []
    skipped: list[str] = []
    for binding in sorted(bindings, key=lambda item: item.game_class):
        block = build_declaration(binding, entries)
        if block is None:
            reason = _skipped(binding, entries)
            skipped.append(reason if reason is not None else binding.game_class)
            continue
        declarations.append(block)

    body = "\n\n".join(declarations)
    skipped_lines = (
        "\n".join(f"  - {item}" for item in skipped) if skipped else "  - none"
    )

    return f"""/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
Per-optic thermal configuration (aee-thermal-realism T11).

This file is GENERATED. The generator tools/validation/gen_thermal_optics.py
writes it from the device corpus data/device/catalogue/thermal_devices.json
and the authored class bindings data/device/class_bindings.json. Do not edit
it by hand. Edit the corpus or the bindings and regenerate it.

VERIFIED ENGINE PATH. The per-optic thermal keys live at
  CfgWeapons >> <optic class> >> ItemInfo >> OpticsModes >> <mode>
in the vanilla derap /tmp/opencode/ti-research/v2/weapons_f/acc/config.cpp
(optic_tws line 1026, optic_Nightstalker line 986, optic_tws_mg line 1069).
The vanilla optic_tws mode TWS carries thermalMode[] = {{0,1}}. The vanilla
config carries no thermalNoise[] and no thermalResolution[]. The shapes below
follow the same flat number-array interface.

INTERFACE EVIDENCE, NO VALUE COPIED. The surveyed mods A3RO (3341786920)
and AH-64D (1351428303) place thermalMode[], thermalNoise[] and
thermalResolution[] on the optic class or on the OpticsModes mode. Their
arrays are interface shapes only. No mod value is copied.

BINDINGS. The class bindings are AUTHORED. Each binding links one real Arma
optic class to one corpus device. The mapping and its identity evidence are
in data/device/class_bindings.json.

DERIVATIONS. Every emitted number has one recorded source:
  thermalMode[]       DECLARED. The engine-minimum palette pair, WHOT (0)
                      and BHOT (1), per the thermal mode table in
                      docs/wiki/research/engine-thermal-mechanisms.md. It is
                      not a corpus figure. The corpus holds no palette.
  thermalNoise[]      DERIVED. The detector NETD in C, from the corpus field
                      netd_c.
  thermalResolution[] DERIVED. The detector pixel array, from the corpus
                      fields resolution_x and resolution_y.

FAIL CLOSED. A binding with no corpus row, or with no held netd_c,
resolution_x or resolution_y, emits no declaration. The withheld bindings
are named below. No value is invented.

WITHHELD BINDINGS
{skipped_lines}
*/
class CfgWeapons {{
{body}
}};
"""


def write(path: Path = OUT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(), encoding="utf-8")


def check(path: Path = OUT) -> int:
    """Return 0 when the generated file is fresh, 1 when it is stale."""
    expected = render()
    if not path.is_file():
        print(f"gen_thermal_optics: {path} is missing")
        return 1
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        print(f"gen_thermal_optics: {path} is stale")
        return 1
    print(f"gen_thermal_optics: {path} is fresh")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify freshness")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--bindings", type=Path, default=DEFAULT_BINDINGS)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)

    if args.check:
        return check(args.out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(args.data_dir, args.bindings), encoding="utf-8")
    print(f"gen_thermal_optics: wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
