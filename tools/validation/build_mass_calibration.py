#!/usr/bin/env python3
"""Build the engine mass calibration from the in-engine mass census.

The census probe ``aee_p72_mass_probe.sqf`` spawns one instance of every
class in ``data/vehicle/class_bindings.json``, reads the engine's own
``getMass`` and deletes the instance. It emits one line per class:

  [P72] MASS <class> config=<n> live=<n>

This tool parses that log, pairs each class with the held real mass in
``data/vehicle/mass_model_calibration.json`` and writes the fit:

  engine_mass = real_analogue_mass_kg / scale

The engine mass and the config ``mass`` are ENGINE tuning values. They are
never a real-world value, so the calibration only records them. It never
copies an engine value into a held source and it applies no override.

The tool fails closed. No log, a log that misses a bound class, a non-numeric
reading or a class with no held pair produces no artefact and exits non-zero.
The ``approved`` flag is always false; nothing consumes it yet.

Run:  python3 tools/validation/build_mass_calibration.py
      python3 tools/validation/build_mass_calibration.py --log tests/docker/run.log
Exit: 0 when the artefact is written. 1 when the census cannot be read or
      paired. 2 on a usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import schemas  # noqa: E402

DEFAULT_LOG = ROOT / "tests" / "docker" / "run.log"
DEFAULT_BINDINGS = ROOT / "data" / "vehicle" / "class_bindings.json"
DEFAULT_CALIBRATION = ROOT / "data" / "vehicle" / "mass_model_calibration.json"
DEFAULT_OUT = ROOT / "data" / "physics" / "mass_calibration.json"

SCHEMA = schemas.PHYSICS_MASS_CALIBRATION
CALIBRATION_SCHEMA = schemas.VEHICLE_MASS_MODEL_CALIBRATION
PROBE_TAG = "[P72] MASS"
LINE_RE = re.compile(r"^\[P72\] MASS (\S+) config=(\S+) live=(\S+)\s*$")
SCALE_ROUND = 6
METRIC_ROUND = 4
# The leave-one-out band. A predicted engine mass within this fraction of the
# measured one counts as covered. The value is a reporting band, not a gate.
COVERAGE_TOLERANCE = 0.20
FIT_CONVENTION = (
    "scale = real_analogue_mass_kg / engine_mass; "
    "engine_mass = real_analogue_mass_kg / scale"
)


class CensusError(ValueError):
    """The census log or its held pairing does not satisfy the contract."""


def _number(value: object) -> float | None:
    """Return a real number, rejecting a bool and a numeric string."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def bound_classes(path: Path) -> list[str]:
    """Return the game classes in class_bindings.json, in file order."""
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CensusError(f"{path}: cannot read the class bindings: {exc}") from exc
    if not isinstance(loaded, list) or not loaded:
        raise CensusError(f"{path}: the class bindings must be a non-empty array")
    classes: list[str] = []
    for index, raw in enumerate(loaded):
        if not isinstance(raw, dict):
            raise CensusError(f"{path}: binding[{index}] must be an object")
        name = raw.get("game_class")
        if not isinstance(name, str) or not name.strip():
            raise CensusError(f"{path}: binding[{index}].game_class must be a string")
        classes.append(name)
    if len(set(classes)) != len(classes):
        raise CensusError(f"{path}: a game class repeats in the bindings")
    return classes


def held_masses(path: Path) -> dict[str, dict[str, object]]:
    """Return the census rows keyed by game class id.

    Each row carries the sourced real mass and its basis. The id field is the
    game class the row binds, so the join with the probe log is exact.
    """
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CensusError(f"{path}: cannot read the held masses: {exc}") from exc
    if not isinstance(loaded, dict):
        raise CensusError(f"{path}: the held masses must be a JSON object")
    if loaded.get("schema") != CALIBRATION_SCHEMA:
        raise CensusError(f"{path}: schema must be {CALIBRATION_SCHEMA}")
    rows = loaded.get("rows")
    if not isinstance(rows, list) or not rows:
        raise CensusError(f"{path}: rows must be a non-empty array")
    held: dict[str, dict[str, object]] = {}
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raise CensusError(f"{path}: rows[{index}] must be an object")
        ident = raw.get("id")
        if not isinstance(ident, str) or not ident.strip():
            raise CensusError(f"{path}: rows[{index}].id must be a string")
        mass = _number(raw.get("real_mass_kg"))
        if mass is None or mass <= 0:
            raise CensusError(f"{path}: rows[{index}].real_mass_kg must be positive")
        held[ident] = raw
    return held


def parse_log(path: Path) -> dict[str, tuple[float, float]]:
    """Return class -> (config mass, live getMass) from the probe log.

    Every value must be numeric. A duplicate class or a non-numeric reading is
    an error, because a partial census is not a census.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise CensusError(f"{path}: cannot read the census log: {exc}") from exc
    readings: dict[str, tuple[float, float]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        # The captured log prefixes every line with the container name and a
        # timestamp; the raw RPT does not. Find the tag and match from there.
        tag = line.find(PROBE_TAG)
        if tag < 0:
            continue
        match = LINE_RE.match(line[tag:])
        if match is None:
            raise CensusError(f"{path}: malformed mass line: {line!r}")
        name, raw_config, raw_live = match.groups()
        if name in readings:
            raise CensusError(f"{path}: class {name} appears more than once")
        try:
            config_mass = float(raw_config)
            live_mass = float(raw_live)
        except ValueError as exc:
            raise CensusError(
                f"{path}: class {name} has a non-numeric reading "
                f"config={raw_config!r} live={raw_live!r}"
            ) from exc
        if live_mass <= 0:
            raise CensusError(f"{path}: class {name} has a non-positive live mass")
        readings[name] = (config_mass, live_mass)
    if not readings:
        raise CensusError(f"{path}: no {PROBE_TAG} line found")
    return readings


def _round(value: float, places: int) -> float:
    return round(value, places)


def build_rows(
    classes: Sequence[str],
    readings: dict[str, tuple[float, float]],
    held: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    """Pair every bound class with its reading and its held real mass.

    Fail closed: a class missing from the log, or a class with no held pair,
    refuses the whole build. An incomplete census is not a census.
    """
    missing_log = [name for name in classes if name not in readings]
    if missing_log:
        raise CensusError(
            "the census log misses bound class(es): " + ", ".join(missing_log)
        )
    missing_pair = [name for name in classes if name not in held]
    if missing_pair:
        raise CensusError(
            "the held masses miss bound class(es): " + ", ".join(missing_pair)
        )
    rows: list[dict[str, object]] = []
    for name in classes:
        config_mass, live_mass = readings[name]
        row = held[name]
        real_mass = _number(row.get("real_mass_kg"))
        if real_mass is None or real_mass <= 0:
            raise CensusError(f"{name}: the held real mass is not positive")
        scale = _round(real_mass / live_mass, SCALE_ROUND)
        if scale <= 0:
            raise CensusError(f"{name}: the scale is not positive")
        rows.append(
            {
                "game_class": name,
                "engine_mass_config": _round(config_mass, SCALE_ROUND),
                "engine_mass_live": _round(live_mass, SCALE_ROUND),
                "real_analogue_mass_kg": _round(real_mass, SCALE_ROUND),
                "mass_basis": row.get("mass_basis", ""),
                "scale": scale,
                "source": row.get("source", ""),
                "source_locator": row.get("source_locator", ""),
            }
        )
    return rows


def fit_rows(rows: Sequence[dict[str, object]]) -> tuple[float, dict[str, object]]:
    """Return the median scale and the leave-one-out report.

    The fit is the median of the per-class scales. The median resists the one
    weak pairing and matches the small-sample treatment in the held census.
    The leave-one-out error refits from the other classes and scores the held
    class, so a fit that only works because a row is in its own input shows up.
    """
    scales = [float(row["scale"]) for row in rows]
    scale = _round(statistics.median(scales), SCALE_ROUND)
    errors: list[float] = []
    covered = 0
    for index, row in enumerate(rows):
        others = scales[:index] + scales[index + 1 :]
        if not others:
            continue
        refit = statistics.median(others)
        if refit <= 0:
            continue
        predicted = float(row["real_analogue_mass_kg"]) / refit
        measured = float(row["engine_mass_live"])
        ape = abs(predicted - measured) / measured
        errors.append(ape)
        if ape <= COVERAGE_TOLERANCE:
            covered += 1
    n = len(rows)
    leave_one_out = {
        "convention": "each class is scored with the fit refit from the other classes",
        "n": n,
        "coverage": _round(covered / n, METRIC_ROUND),
        "coverage_tolerance": COVERAGE_TOLERANCE,
        "mdape": _round(statistics.median(errors), METRIC_ROUND) if errors else 0.0,
    }
    return scale, leave_one_out


def build_artefact(
    classes: Sequence[str],
    readings: dict[str, tuple[float, float]],
    held: dict[str, dict[str, object]],
) -> dict[str, object]:
    """Return the calibration artefact. The approved flag stays false."""
    rows = build_rows(classes, readings, held)
    scale, leave_one_out = fit_rows(rows)
    return {
        "schema": SCHEMA,
        "note": (
            "Calibration of the engine's own mass for the bound vehicle classes. "
            "The engine mass and the config mass are engine tuning values, measured "
            "in engine by the mass-census probe; they are never a real-world value. "
            "The real mass is a held catalogue analogue. The fit is a calibration "
            "scale, not a copied engine value. The approved flag stays false because "
            "nothing consumes this artefact yet."
        ),
        "fit": {
            "convention": FIT_CONVENTION,
            "estimator": "median",
            "scale": scale,
            "round": SCALE_ROUND,
        },
        "leave_one_out": leave_one_out,
        "counts": {"paired": len(rows)},
        "approved": False,
        "rows": rows,
    }


def check_log_present(path: Path) -> None:
    """Refuse when the census has not run. Print the operator command."""
    if path.is_file():
        return
    raise CensusError(
        f"not run yet: no census log at {path}\n"
        "  run the census probe, then build the calibration:\n"
        "    tools/docker_test.sh\n"
        "    python3 tools/validation/build_mass_calibration.py"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the engine mass calibration from the census log."
    )
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--bindings", type=Path, default=DEFAULT_BINDINGS)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    try:
        check_log_present(args.log)
        classes = bound_classes(args.bindings)
        readings = parse_log(args.log)
        held = held_masses(args.calibration)
        artefact = build_artefact(classes, readings, held)
    except (CensusError, OSError) as exc:
        print(f"mass calibration: cannot build the artefact: {exc}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(artefact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    rows = artefact["rows"]
    fit = artefact["fit"]
    count = len(rows) if isinstance(rows, list) else 0
    scale = fit["scale"] if isinstance(fit, dict) else "?"
    print(f"mass calibration: {count} paired classes, scale {scale} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
