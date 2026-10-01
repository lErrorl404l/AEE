#!/usr/bin/env python3
"""Generate the engine CfgVehicles override from the config-binding corpus.

``data/physics/config_bindings.json`` is the only value source. This tool
reads the corpus and emits ``addons/physics/generated/CfgVehicles.hpp``. It
never copies an engine value and it invents nothing. A class with no held
source in the corpus yields no line here.

This override is load-time only and global. The engine reads it when the
config loads, so there is no runtime off switch: the PBO itself is the only
way to disable it. The file declares ``maxSpeed`` and no other key, because
``thermal`` and ``optics`` already override ``htMin``, ``htMax``, ``afMax``,
``mfMax``, ``mFact`` and ``tBody``, and this addon loads last.

Run:
    python3 tools/validation/gen_physics_config.py
    python3 tools/validation/gen_physics_config.py --check
Exit 0 when fresh, 1 when stale or missing under --check.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

REPO = Path(__file__).parents[2]
DEFAULT_DATA = REPO / "data" / "physics" / "config_bindings.json"
DEFAULT_OUT = REPO / "addons" / "physics" / "generated" / "CfgVehicles.hpp"

# This version emits one config class and one key. The schema admits no other
# pair, so a corpus record outside this pair is an error rather than a silent
# drop: the generator must not lose a binding it cannot represent.
CONFIG_CLASS = "CfgVehicles"
KEY = "maxSpeed"

HEADER = (
    "/* SPDX-License-Identifier: GPL-2.0-or-later */\n"
    "// Generated engine config override. Do not edit by hand.\n"
    "// Regenerate with: python3 tools/validation/gen_physics_config.py\n"
    "//\n"
    "// This is a load-time, global override of vanilla engine config. The\n"
    "// engine reads it when the config loads and config cannot be gated at\n"
    "// runtime, so the PBO is the only off switch.\n"
    "//\n"
    "// It declares maxSpeed and no other key. thermal and optics already\n"
    "// override htMin, htMax, afMax, mfMax, mFact and tBody, and this addon\n"
    "// loads last, so redeclaring those keys here would silently win.\n"
)


def load_bindings(path: Path) -> list[object]:
    """Read the binding file. Raise ValueError when it is not an array."""
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"{path}: config bindings must be a top-level array")
    return list(loaded)


def _render_value(value: object) -> str:
    """Return the engine literal for a numeric config value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"config value must be a number, got {value!r}")
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return repr(number)


def _admit(record: object, where: str) -> tuple[str, str]:
    """Check the record carries the admitted class and key. Return both."""
    if not isinstance(record, dict):
        raise ValueError(f"{where}: binding must be an object")
    config_class = record.get("config_class")
    key = record.get("key")
    if config_class != CONFIG_CLASS:
        raise ValueError(
            f"{where}: the generator emits {CONFIG_CLASS} only, got {config_class!r}"
        )
    if key != KEY:
        raise ValueError(f"{where}: the generator emits {KEY} only, got {key!r}")
    game_class = record.get("game_class")
    if not isinstance(game_class, str) or not game_class.strip():
        raise ValueError(f"{where}: game_class must be a non-empty string")
    return game_class, _render_value(record.get("value"))


def build(data: Path) -> list[tuple[str, str]]:
    """Return the (game_class, value literal) pairs, sorted by class."""
    records = load_bindings(data)
    bindings = [
        _admit(record, f"binding[{index}]") for index, record in enumerate(records)
    ]
    classes = [game_class for game_class, _value in bindings]
    if len(classes) != len(set(classes)):
        raise ValueError(f"{data}: a game class repeats in the corpus")
    return sorted(bindings)


def render(bindings: Sequence[tuple[str, str]]) -> str:
    """Return the exact on-disk text for the admitted bindings."""
    lines = [HEADER, f"class {CONFIG_CLASS} {{"]
    for game_class, value in bindings:
        # A bare redeclaration merges into the vanilla class. A forward
        # declaration of the same name in the same scope is rejected as a
        # duplicate definition (hemtt L-C03).
        lines.append(f"    class {game_class} {{")
        lines.append(f"        {KEY} = {value};")
        lines.append("    };")
    lines.append("};")
    return "\n".join(lines) + "\n"


def write_config(data: Path, out: Path) -> int:
    """Write the generated header. Return the binding count."""
    bindings = build(data)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(bindings), encoding="utf-8")
    return len(bindings)


def check_config(data: Path, out: Path) -> int:
    """Return 0 when the committed header matches a fresh build.

    Check mode writes nothing. A missing or stale file returns 1, so a
    stale generated override fails the gate.
    """
    try:
        rendered = render(build(data))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"physics config override: cannot build from the corpus: {exc}")
        return 1
    if not out.is_file():
        print(f"physics config override: {out} is missing; run the generator")
        return 1
    if out.read_text(encoding="utf-8") != rendered:
        print(f"physics config override: {out} is stale; run the generator")
        return 1
    print(f"physics config override: {len(build(data))} bindings -> {out} (fresh)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the engine CfgVehicles override."
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed override is fresh. Write nothing.",
    )
    args = parser.parse_args(argv)
    if args.check:
        return check_config(args.data, args.out)
    try:
        count = write_config(args.data, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"physics config override: cannot build from the corpus: {exc}")
        return 1
    print(f"physics config override: {count} bindings -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
