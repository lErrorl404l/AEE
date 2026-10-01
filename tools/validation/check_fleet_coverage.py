#!/usr/bin/env python3
"""Report the empirical fleet identification gap from the fleet probe log.

The probe ``tests/docker/missions/aee_test.Stratis/aee_p73_fleet_probe.sqf``
enumerates every public ground vehicle class in the engine config, spawns one
instance of each, reads the engine's own values and asks the runtime matcher to
resolve the class. It emits one line per class:

  [P73] FLEET <class> type=<wheeled|tracked> match=<catalogue_id|-> conf=<n>
        by=<layer> mass=<n> len=<n> wid=<n> turret=<0|1> data=<0|1>

This tool parses that log and reports:

  - how many classes the matcher resolved (matched)
  - how many it did not (unmatched: the empirical coverage gap)
  - which unmatched classes the maxSpeed override still reaches, because the
    class holds a binding in data/vehicle/class_bindings.json and its catalogue
    entry holds a max_speed_kmh, so the override emits it

It reads the log and the corpus only. It invents no value and writes nothing.

Run:  python3 tools/validation/check_fleet_coverage.py
      python3 tools/validation/check_fleet_coverage.py --log tests/docker/run.log
      python3 tools/validation/check_fleet_coverage.py --self-test
Exit: 0 when the report is printed (or the self-test passes). 1 when a probe
      line is malformed, or no probe line is present and --require is given.
      2 on a usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parents[2]
DEFAULT_LOG = ROOT / "tests" / "docker" / "run.log"
DEFAULT_BINDINGS = ROOT / "data" / "vehicle" / "class_bindings.json"
DEFAULT_EMITTED = ROOT / "data" / "physics" / "config_bindings.json"

PROBE_TAG = "[P73] FLEET"
LAYERS = ("exact_class", "alias", "keyword", "inheritance", "closest")
LINE_RE = re.compile(
    r"^\[P73\] FLEET "
    r"(?P<class>\S+) type=(?P<type>wheeled|tracked) "
    r"match=(?P<match>\S+) conf=(?P<conf>\S+) by=(?P<by>\S+) "
    r"mass=(?P<mass>\S+) len=(?P<len>\S+) wid=(?P<wid>\S+) "
    r"turret=(?P<turret>[01])(?: data=(?P<data>[01]))?"
    r"(?: cls=(?P<cls>\S+) cby=(?P<cby>\S+))?\s*$"
)


class FleetError(ValueError):
    """The probe log does not satisfy the line contract."""


@dataclass(frozen=True)
class FleetRow:
    """One ground vehicle class as the probe reported it."""

    game_class: str
    vehicle_type: str
    match: str
    confidence: str
    matched_by: str
    mass: str
    length: str
    width: str
    turret: int
    value_row: int
    cls: str = "-"
    cby: str = "-"

    @property
    def matched(self) -> bool:
        return self.match != "-"


def parse_lines(lines: Iterable[str]) -> list[FleetRow]:
    """Return one row per probe line. A duplicate or malformed line refuses."""
    rows: list[FleetRow] = []
    seen: set[str] = set()
    for raw in lines:
        line = raw.strip()
        # The captured log prefixes every line with the container name and a
        # timestamp; the raw RPT does not. Find the tag and match from there.
        tag = line.find(PROBE_TAG)
        if tag < 0:
            continue
        match = LINE_RE.match(line[tag:])
        if match is None:
            raise FleetError(f"malformed fleet line: {line!r}")
        name = match.group("class")
        if name in seen:
            raise FleetError(f"class {name} appears more than once")
        seen.add(name)
        rows.append(
            FleetRow(
                game_class=name,
                vehicle_type=match.group("type"),
                match=match.group("match"),
                confidence=match.group("conf"),
                matched_by=match.group("by"),
                mass=match.group("mass"),
                length=match.group("len"),
                width=match.group("wid"),
                turret=int(match.group("turret")),
                value_row=int(match.group("data") or "0"),
                cls=match.group("cls") or "-",
                cby=match.group("cby") or "-",
            )
        )
    return rows


def parse_log(path: Path) -> list[FleetRow]:
    """Read the probe log. A missing file is a fleet error."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise FleetError(f"{path}: cannot read the probe log: {exc}") from exc
    return parse_lines(text.splitlines())


def class_set(path: Path) -> set[str]:
    """Return the game classes an array of binding records names."""
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FleetError(f"{path}: cannot read the class records: {exc}") from exc
    if not isinstance(loaded, list):
        raise FleetError(f"{path}: the class records must be a top-level array")
    classes: set[str] = set()
    for index, raw in enumerate(loaded):
        if not isinstance(raw, dict):
            raise FleetError(f"{path}: record[{index}] must be an object")
        name = raw.get("game_class")
        if not isinstance(name, str) or not name.strip():
            raise FleetError(f"{path}: record[{index}].game_class must be a string")
        classes.add(name)
    return classes


def report(rows: Sequence[FleetRow], bindings: set[str], emitted: set[str]) -> str:
    """Render the fleet report. A deterministic text for the parsed rows."""
    matched = [row for row in rows if row.matched]
    unmatched = [row for row in rows if not row.matched]
    layers = Counter(row.matched_by for row in matched)
    emitted_unmatched = sorted(
        row.game_class for row in unmatched if row.game_class in emitted
    )
    bound_waiting = sorted(
        row.game_class
        for row in unmatched
        if row.game_class in bindings and row.game_class not in emitted
    )

    lines = [
        f"fleet coverage: {len(rows)} ground classes, {len(matched)} matched, {len(unmatched)} unmatched",
        "matched by layer: "
        + ", ".join(f"{layer}={layers.get(layer, 0)}" for layer in LAYERS),
        f"override reaches {len(emitted_unmatched)} unmatched classes: "
        + (", ".join(emitted_unmatched) if emitted_unmatched else "none"),
        f"bound but no held max_speed, so not emitted ({len(bound_waiting)}): "
        + (", ".join(bound_waiting) if bound_waiting else "none"),
    ]

    # The classifier route is optional. It is present only when the probe
    # records it, so an older log reports as before.
    classified = [row for row in rows if row.cby != "-"]
    if classified:
        routes = Counter(row.cby for row in classified)
        catalogue = routes.get("corpus", 0) + routes.get("band", 0)
        token_only = routes.get("token", 0)
        none = routes.get("none", 0)
        lines.append(
            f"classifier: {catalogue} catalogue entries "
            f"({routes.get('corpus', 0)} corpus, {routes.get('band', 0)} band), "
            f"{token_only} token only, {none} none"
        )
    if unmatched:
        lines.append(f"unmatched classes ({len(unmatched)}):")
        for row in unmatched:
            lines.append(f"  {row.game_class} type={row.vehicle_type} mass={row.mass}")
    return "\n".join(lines)


_SELF_TEST_FIXTURE = (
    "[P73] FLEET C_Hatchback_01_F type=wheeled match=honda_civic_6gen_hatchback "
    "conf=5 by=closest mass=1200 len=4.2 wid=1.8 turret=0 data=1",
    "[P73] FLEET B_MBT_01_cannon_F type=tracked match=- conf=- by=- "
    "mass=60000 len=9.5 wid=3.6 turret=1 data=0",
    "[P73] FLEET B_APC_Wheeled_01_cannon_F type=wheeled match=btr_80 conf=4 "
    "by=inheritance mass=15000 len=7.1 wid=2.9 turret=1 data=1",
)


def self_test() -> int:
    """Run the parser over a fixed fixture and assert the report."""
    rows = parse_lines(_SELF_TEST_FIXTURE)
    if len(rows) != 3:
        raise FleetError(f"fixture gave {len(rows)} rows, want 3")
    matched = [row for row in rows if row.matched]
    if len(matched) != 2:
        raise FleetError(f"fixture gave {len(matched)} matched, want 2")
    unmatched = [row.game_class for row in rows if not row.matched]
    if unmatched != ["B_MBT_01_cannon_F"]:
        raise FleetError(f"fixture unmatched {unmatched}, want the one tank")
    layers = Counter(row.matched_by for row in matched)
    if layers != Counter({"closest": 1, "inheritance": 1}):
        raise FleetError(f"fixture layers {dict(layers)}, want one each")
    text = report(
        rows,
        {"B_MBT_01_cannon_F", "B_APC_Wheeled_01_cannon_F"},
        {"B_APC_Wheeled_01_cannon_F"},
    )
    for expected in (
        "3 ground classes, 2 matched, 1 unmatched",
        "override reaches 0 unmatched classes: none",
        "bound but no held max_speed, so not emitted (1): B_MBT_01_cannon_F",
    ):
        if expected not in text:
            raise FleetError(f"self-test report misses {expected!r}")
    try:
        parse_lines(["[P73] FLEET broken"])
    except FleetError:
        pass
    else:
        raise FleetError("a malformed line was not refused")
    print("fleet coverage: self-test passed")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report the empirical fleet identification gap."
    )
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--bindings", type=Path, default=DEFAULT_BINDINGS)
    parser.add_argument("--emitted", type=Path, default=DEFAULT_EMITTED)
    parser.add_argument(
        "--require",
        action="store_true",
        help="exit 1 when the log holds no probe line",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    try:
        rows = parse_log(args.log) if args.log.is_file() else []
        bindings = class_set(args.bindings)
        emitted = class_set(args.emitted) if args.emitted.is_file() else set()
    except FleetError as exc:
        print(f"fleet coverage: {exc}", file=sys.stderr)
        return 1

    if not rows:
        print(f"fleet coverage: not run yet: no {PROBE_TAG} line in {args.log}")
        print("  run the fleet probe, then report:")
        print("    tools/docker_test.sh")
        print("    python3 tools/validation/check_fleet_coverage.py")
        return 1 if args.require else 0

    print(report(rows, bindings, emitted))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
