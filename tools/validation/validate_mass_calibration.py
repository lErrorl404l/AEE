#!/usr/bin/env python3
"""Validate the engine mass calibration artefact.

The tool ``build_mass_calibration.py`` writes
``data/physics/mass_calibration.json`` from the in-engine mass census and the
held real masses. This gate checks the artefact is honest:

  * the schema is the calibration schema;
  * ``approved`` is a boolean, and a true flag names an approver;
  * the fit names the median estimator and a positive scale;
  * every row reproduces its scale from the held real mass and the measured
    engine mass;
  * the fit is frozen to a reference set and its scale equals the median of
    the reference row scales only, so an appended verification row never moves
    it; the full-sample median is reported as visible drift;
  * the row set equals the classes in ``data/vehicle/class_bindings.json``.

A missing artefact is a legal state: the census has not run yet, so there is
nothing to check. The gate is strict once the artefact exists.

Run:  python3 tools/validation/validate_mass_calibration.py
      python3 tools/validation/validate_mass_calibration.py --self-check
Exit: 0 on success or an absent artefact, 1 on any calibration error, 2 on a
      usage error.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import schemas  # noqa: E402

DEFAULT_PATH = ROOT / "data" / "physics" / "mass_calibration.json"
DEFAULT_BINDINGS = ROOT / "data" / "vehicle" / "class_bindings.json"

SCHEMA = schemas.PHYSICS_MASS_CALIBRATION
SCALE_ROUND = 6
SCALE_TOLERANCE = 1e-6
FIT_TOLERANCE = 1e-4


def _number(value: object) -> float | None:
    """Return a real number, rejecting a bool and a numeric string."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def bound_classes(path: Path) -> list[str]:
    """Return the game classes in class_bindings.json, in file order."""
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(loaded, list):
        return []
    classes: list[str] = []
    for raw in loaded:
        row = _mapping(raw)
        name = _text(row.get("game_class")) if row is not None else None
        if name is not None:
            classes.append(name)
    return classes


def reference_scales(
    rows: Sequence[dict[str, object]], reference_n: int
) -> list[float]:
    """Return the row scales of the frozen reference set."""
    return [
        float(rows[index]["scale"])
        for index in range(min(reference_n, len(rows)))
        if _number(rows[index].get("scale"))
    ]


def full_sample_median(rows: Sequence[dict[str, object]]) -> float | None:
    """Return the median scale over every row. This is the visible drift."""
    scales = [float(row["scale"]) for row in rows if _number(row.get("scale"))]
    if not scales:
        return None
    return round(statistics.median(scales), SCALE_ROUND)


def load_artefact(path: Path) -> dict[str, object]:
    """Read the artefact. Raise ValueError when the top level is not an object."""
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: the artefact must be a JSON object")
    return {str(key): item for key, item in loaded.items()}


def validate_artefact(
    payload: dict[str, object], expected_classes: Sequence[str]
) -> list[str]:
    """Return every error in the calibration artefact. Empty is valid."""
    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")

    approved = payload.get("approved")
    if not isinstance(approved, bool):
        errors.append("approved must be true or false")
    elif approved:
        # The tool never writes an approval. A true flag needs a named
        # approver, so the flag cannot be flipped without a trace.
        approval = _mapping(payload.get("approval"))
        if approval is None or _text(approval.get("approved_by")) is None:
            errors.append("approved is true without an approval.approved_by")

    rows_raw = payload.get("rows")
    rows: list[dict[str, object]] = []
    if not isinstance(rows_raw, list) or not rows_raw:
        errors.append("rows must be a non-empty array")
    else:
        seen: set[str] = set()
        for index, raw in enumerate(rows_raw):
            row = _mapping(raw)
            if row is None:
                errors.append(f"rows[{index}] must be an object")
                continue
            where = f"rows[{index}]"
            name = _text(row.get("game_class"))
            if name is None:
                errors.append(f"{where}.game_class must be a non-empty string")
            elif name in seen:
                errors.append(f"{where}.game_class {name} repeats")
            else:
                seen.add(name)
            live = _number(row.get("engine_mass_live"))
            real = _number(row.get("real_analogue_mass_kg"))
            scale = _number(row.get("scale"))
            if live is None or live <= 0:
                errors.append(f"{where}.engine_mass_live must be positive")
            if real is None or real <= 0:
                errors.append(f"{where}.real_analogue_mass_kg must be positive")
            if scale is None or scale <= 0:
                errors.append(f"{where}.scale must be positive")
            if (
                _text(row.get("source")) is None
                or _text(row.get("source_locator")) is None
            ):
                errors.append(f"{where} needs a source and a source_locator")
            if live is not None and real is not None and scale is not None:
                expected = round(real / live, SCALE_ROUND)
                if abs(scale - expected) > SCALE_TOLERANCE:
                    errors.append(
                        f"{where}.scale {scale} does not reproduce from "
                        f"real {real} / live {live} = {expected}"
                    )
            rows.append(row)

    fit = _mapping(payload.get("fit"))
    if fit is None:
        errors.append("fit must be an object")
    else:
        if fit.get("estimator") != "median":
            errors.append("fit.estimator must be median")
        if _text(fit.get("convention")) is None:
            errors.append("fit.convention must be non-empty")
        if fit.get("frozen") is not True:
            errors.append("fit.frozen must be true")
        scale = _number(fit.get("scale"))
        if scale is None or scale <= 0:
            errors.append("fit.scale must be positive")
        reference_n = fit.get("reference_n")
        if isinstance(reference_n, bool) or not isinstance(reference_n, int):
            errors.append("fit.reference_n must be an integer")
        elif not 1 <= reference_n <= len(rows):
            errors.append(
                f"fit.reference_n {reference_n} must be between 1 and {len(rows)}"
            )
        elif scale is not None:
            # The fit is frozen to a reference set. The scale is the median of
            # the reference row scales only, so an appended verification row
            # never moves it. The full-sample median is reported as drift.
            reference = reference_scales(rows, reference_n)
            if reference:
                median = round(statistics.median(reference), SCALE_ROUND)
                if abs(scale - median) > FIT_TOLERANCE:
                    errors.append(
                        f"fit.scale {scale} is not the reference median row "
                        f"scale {median}"
                    )

    leave_one_out = _mapping(payload.get("leave_one_out"))
    if leave_one_out is None:
        errors.append("leave_one_out must be an object")
    else:
        if leave_one_out.get("n") != len(rows):
            errors.append("leave_one_out.n must equal the row count")
        coverage = _number(leave_one_out.get("coverage"))
        if coverage is None or not 0.0 <= coverage <= 1.0:
            errors.append("leave_one_out.coverage must be between 0 and 1")
        mdape = _number(leave_one_out.get("mdape"))
        if mdape is None or mdape < 0:
            errors.append("leave_one_out.mdape must be non-negative")

    if expected_classes:
        expected = set(expected_classes)
        found = {row.get("game_class") for row in rows}
        missing = sorted(expected - {name for name in found if isinstance(name, str)})
        extra = sorted({name for name in found if isinstance(name, str)} - expected)
        if missing:
            errors.append("rows miss bound class(es): " + ", ".join(missing))
        if extra:
            errors.append("rows hold unbound class(es): " + ", ".join(extra))
    return errors


def _valid_fixture() -> dict[str, object]:
    real_a, live_a = 1000.0, 2000.0
    real_b, live_b = 3000.0, 6000.0
    rows = [
        {
            "game_class": "A_F",
            "engine_mass_config": live_a,
            "engine_mass_live": live_a,
            "real_analogue_mass_kg": real_a,
            "mass_basis": "gross",
            "scale": round(real_a / live_a, SCALE_ROUND),
            "source": "data/vehicle/catalogue/a.json",
            "source_locator": "a, row 1",
        },
        {
            "game_class": "B_F",
            "engine_mass_config": live_b,
            "engine_mass_live": live_b,
            "real_analogue_mass_kg": real_b,
            "mass_basis": "curb",
            "scale": round(real_b / live_b, SCALE_ROUND),
            "source": "data/vehicle/catalogue/b.json",
            "source_locator": "b, row 2",
        },
    ]
    return {
        "schema": SCHEMA,
        "fit": {
            "convention": "engine_mass = real_analogue_mass_kg / scale",
            "estimator": "median",
            "scale": 0.5,
            "round": SCALE_ROUND,
            "reference_n": len(rows),
            "frozen": True,
            "frozen_on": "2026-10-01",
            "frozen_basis": "test fixture",
            "recalibration_policy": "test fixture",
        },
        "leave_one_out": {
            "convention": "refit from the other classes",
            "n": 2,
            "coverage": 1.0,
            "coverage_tolerance": 0.2,
            "mdape": 0.0,
        },
        "approved": False,
        "rows": rows,
    }


def self_check() -> int:
    """Run embedded fixtures. Write no repository file."""
    fixture = _valid_fixture()
    expected = ["A_F", "B_F"]
    failures: list[str] = []
    if validate_artefact(fixture, expected):
        failures.append("a clean fixture was rejected")

    import copy

    tampered = copy.deepcopy(fixture)
    tampered["rows"][0]["scale"] = 99.0
    if not any(
        "does not reproduce" in error for error in validate_artefact(tampered, expected)
    ):
        failures.append("a tampered scale was accepted")

    flipped = copy.deepcopy(fixture)
    flipped["approved"] = True
    if not any(
        "without an approval" in error for error in validate_artefact(flipped, expected)
    ):
        failures.append("a bare approved flag was accepted")

    unfrozen = copy.deepcopy(fixture)
    unfrozen["fit"]["frozen"] = False
    if not any(
        "fit.frozen must be true" in error
        for error in validate_artefact(unfrozen, expected)
    ):
        failures.append("a non-frozen fit was accepted")

    # An appended verification row with a different scale must not move the
    # frozen fit.scale: the fit stays the median of the reference rows only.
    appended = copy.deepcopy(fixture)
    appended["rows"].append(
        {
            "game_class": "C_F",
            "engine_mass_config": 3000.0,
            "engine_mass_live": 3000.0,
            "real_analogue_mass_kg": 9000.0,
            "mass_basis": "gross",
            "scale": 3.0,
            "source": "data/vehicle/catalogue/c.json",
            "source_locator": "c, row 3",
        }
    )
    appended["leave_one_out"]["n"] = len(appended["rows"])
    if validate_artefact(appended, expected + ["C_F"]):
        failures.append("an appended verification row moved the frozen fit.scale")

    if failures:
        print("mass calibration: self-check FAIL")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print("mass calibration: self-check PASS")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the engine mass calibration artefact."
    )
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--bindings", type=Path, default=DEFAULT_BINDINGS)
    parser.add_argument(
        "--self-check", action="store_true", help="Run embedded fixtures."
    )
    args = parser.parse_args(argv)

    if args.self_check:
        return self_check()

    if not args.path.is_file():
        print(
            f"mass calibration: not produced yet: {args.path} is absent; "
            "run the census probe, then tools/validation/build_mass_calibration.py"
        )
        return 0

    try:
        payload = load_artefact(args.path)
        expected = bound_classes(args.bindings)
        errors = validate_artefact(payload, expected)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"mass calibration: FAIL\n  cannot read the artefact: {exc}")
        return 1
    if errors:
        print("mass calibration: FAIL")
        for error in errors:
            print(f"  {error}")
        return 1
    rows = payload.get("rows")
    count = len(rows) if isinstance(rows, list) else 0
    print(f"mass calibration: {count} calibrated classes -> {args.path} (valid)")
    if isinstance(rows, list):
        row_maps = [row for row in (_mapping(raw) for raw in rows) if row is not None]
        drift = full_sample_median(row_maps)
        fit = _mapping(payload.get("fit"))
        scale = _number(fit.get("scale")) if fit is not None else None
        if (
            drift is not None
            and scale is not None
            and abs(drift - scale) > FIT_TOLERANCE
        ):
            print(
                f"mass calibration: full-sample median {drift} drifts from the "
                f"frozen scale {scale} (the appended verification rows)"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
