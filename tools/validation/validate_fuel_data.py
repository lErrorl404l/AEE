#!/usr/bin/env python3
"""Validate the ground-vehicle fuel and coolant constants (issue #111).

The corpus is ``data/physics/fuel.json`` (schema ``aee.physics.fuel/1``). It is
the only home for a ground-vehicle fuel or coolant constant. Every value
carries a ``source`` id that must resolve in the file's own ``sources`` array,
and a ``grade`` from the shared grade vocabulary.

The validator fails closed. It rejects a missing schema, a duplicated id, a
source id that resolves nowhere, an engine class whose fuel id resolves
nowhere, a fuel or rolling-resistance value outside its physical range, a
terrain multiplier below one, and a thermal band that is out of order.

Run:
    python3 tools/validation/validate_fuel_data.py
    python3 tools/validation/validate_fuel_data.py --self-check
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path

REPO = Path(__file__).parents[2]
DEFAULT_DATA = REPO / "data" / "physics" / "fuel.json"

SCHEMA = "aee.physics.fuel/1"

GRADES = {"standard", "documented", "claimed", "derived"}

# The ground-state vocabulary the mobility model publishes. A terrain
# multiplier is keyed by exactly these names.
GROUND_STATES = {"Normal", "Mud", "Dusty", "Frozen", "Snow"}

# The thermal constants the coolant model reads. A missing id is an error.
REQUIRED_THERMAL = {
    "thermostat_c",
    "coolant_normal_min_c",
    "coolant_normal_max_c",
    "coolant_hot_max_c",
    "coolant_critical_c",
    "coolant_overheat_derate",
    "oil_normal_max_c",
    "oil_limit_c",
    "heat_reject_fraction",
    "convection_natural_w_m2k",
    "convection_forced_w_m2k_per_ms",
    "coolant_tau_s",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_str(record: dict, key: str, where: str, errors: list[str]) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where}: missing or empty '{key}'")
        return ""
    return value


def _require_number(record: dict, key: str, where: str, errors: list[str]) -> float:
    value = record.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        errors.append(f"{where}: '{key}' is not a number")
        return 0.0
    return float(value)


def _check_grade(record: dict, where: str, errors: list[str]) -> None:
    grade = record.get("grade")
    if grade not in GRADES:
        errors.append(f"{where}: grade '{grade}' is not in {sorted(GRADES)}")


def validate(data: dict) -> list[str]:
    errors: list[str] = []

    if data.get("schema") != SCHEMA:
        errors.append(f"schema is '{data.get('schema')}', expected '{SCHEMA}'")

    # ─── Sources ────────────────────────────────────────────────────────────
    source_ids: set[str] = set()
    for source in data.get("sources", []):
        sid = _require_str(source, "source_id", "source", errors)
        if sid in source_ids:
            errors.append(f"source '{sid}': duplicated source_id")
        source_ids.add(sid)
        for key in ("title", "identifier"):
            _require_str(source, key, f"source '{sid}'", errors)
        tier = source.get("tier")
        if not isinstance(tier, int) or isinstance(tier, bool) or not (1 <= tier <= 5):
            errors.append(f"source '{sid}': tier '{tier}' is not 1..5")

    def check_source(record: dict, where: str) -> None:
        sid = _require_str(record, "source", where, errors)
        if sid and sid not in source_ids:
            errors.append(f"{where}: source '{sid}' resolves to no source record")
        _require_str(record, "locator", where, errors)
        _require_str(record, "basis", where, errors)
        _check_grade(record, where, errors)

    # ─── Engine classes ─────────────────────────────────────────────────────
    fuel_ids = {f.get("id") for f in data.get("fuels", [])}
    class_ids: set[str] = set()
    for entry in data.get("engine_classes", []):
        cid = _require_str(entry, "id", "engine_class", errors)
        where = f"engine_class '{cid}'"
        if cid in class_ids:
            errors.append(f"{where}: duplicated id")
        class_ids.add(cid)
        bsfc = _require_number(entry, "bsfc_g_kwh", where, errors)
        if not (100.0 <= bsfc <= 400.0):
            errors.append(f"{where}: bsfc_g_kwh {bsfc} outside 100..400")
        fuel = _require_str(entry, "fuel", where, errors)
        if fuel and fuel not in fuel_ids:
            errors.append(f"{where}: fuel '{fuel}' resolves to no fuel record")
        check_source(entry, where)

    if not class_ids:
        errors.append("no engine_classes recorded")

    # ─── Fuels ──────────────────────────────────────────────────────────────
    seen_fuels: set[str] = set()
    for entry in data.get("fuels", []):
        fid = _require_str(entry, "id", "fuel", errors)
        where = f"fuel '{fid}'"
        if fid in seen_fuels:
            errors.append(f"{where}: duplicated id")
        seen_fuels.add(fid)
        density = _require_number(entry, "density_g_l", where, errors)
        if not (500.0 <= density <= 1100.0):
            errors.append(f"{where}: density_g_l {density} outside 500..1100")
        lhv = _require_number(entry, "lhv_mj_kg", where, errors)
        if not (35.0 <= lhv <= 50.0):
            errors.append(f"{where}: lhv_mj_kg {lhv} outside 35..50")
        check_source(entry, where)

    # ─── Rolling resistance ─────────────────────────────────────────────────
    seen_rr: set[str] = set()
    for entry in data.get("rolling_resistance", []):
        rid = _require_str(entry, "id", "rolling_resistance", errors)
        where = f"rolling_resistance '{rid}'"
        if rid in seen_rr:
            errors.append(f"{where}: duplicated id")
        seen_rr.add(rid)
        crr = _require_number(entry, "crr", where, errors)
        if not (0.0 < crr < 1.0):
            errors.append(f"{where}: crr {crr} outside 0..1")
        check_source(entry, where)

    # ─── Terrain multipliers ────────────────────────────────────────────────
    seen_tm: set[str] = set()
    for entry in data.get("terrain_multipliers", []):
        tid = _require_str(entry, "id", "terrain_multiplier", errors)
        where = f"terrain_multiplier '{tid}'"
        if tid in seen_tm:
            errors.append(f"{where}: duplicated id")
        seen_tm.add(tid)
        if tid and tid not in GROUND_STATES:
            errors.append(
                f"{where}: id is not a mobility ground state {sorted(GROUND_STATES)}"
            )
        multiplier = _require_number(entry, "multiplier", where, errors)
        if multiplier < 1.0:
            errors.append(f"{where}: multiplier {multiplier} is below 1")
        check_source(entry, where)

    missing_states = GROUND_STATES - seen_tm
    if missing_states:
        errors.append(
            f"terrain_multipliers: missing ground states {sorted(missing_states)}"
        )

    # ─── Thermal ────────────────────────────────────────────────────────────
    thermal: dict[str, float] = {}
    for entry in data.get("thermal", []):
        tid = _require_str(entry, "id", "thermal", errors)
        where = f"thermal '{tid}'"
        if tid in thermal:
            errors.append(f"{where}: duplicated id")
        thermal[tid] = _require_number(entry, "value", where, errors)
        _require_str(entry, "unit", where, errors)
        check_source(entry, where)

    missing_thermal = REQUIRED_THERMAL - set(thermal)
    if missing_thermal:
        errors.append(f"thermal: missing constants {sorted(missing_thermal)}")

    if not missing_thermal:
        if not (thermal["coolant_normal_min_c"] < thermal["coolant_normal_max_c"]):
            errors.append(
                "thermal: coolant_normal_min_c is not below coolant_normal_max_c"
            )
        if not (thermal["coolant_normal_max_c"] <= thermal["coolant_hot_max_c"]):
            errors.append("thermal: coolant_normal_max_c is above coolant_hot_max_c")
        if not (thermal["coolant_hot_max_c"] < thermal["coolant_critical_c"]):
            errors.append("thermal: coolant_hot_max_c is not below coolant_critical_c")
        derate = thermal["coolant_overheat_derate"]
        if not (0.0 < derate <= 1.0):
            errors.append(f"thermal: coolant_overheat_derate {derate} outside 0..1")
        if not (0.0 < thermal["heat_reject_fraction"] < 1.0):
            errors.append("thermal: heat_reject_fraction outside 0..1")

    return errors


def _self_check() -> int:
    """Mutate a good corpus and prove each defect is caught."""
    data = load(DEFAULT_DATA)
    if validate(data):
        print("fuel data: FAIL (the committed corpus does not validate)")
        for error in validate(data):
            print(f"  {error}")
        return 1

    import copy

    cases = [
        ("bad schema", lambda d: d.update(schema="nope")),
        ("unknown source", lambda d: d["engine_classes"][0].update(source="ghost")),
        (
            "duplicate class",
            lambda d: d["engine_classes"].append(dict(d["engine_classes"][0])),
        ),
        ("bsfc out of range", lambda d: d["engine_classes"][0].update(bsfc_g_kwh=9999)),
        (
            "class fuel resolves nowhere",
            lambda d: d["engine_classes"][0].update(fuel="ghost"),
        ),
        ("crr out of range", lambda d: d["rolling_resistance"][0].update(crr=2.0)),
        (
            "unknown ground state",
            lambda d: d["terrain_multipliers"][0].update(id="Swamp"),
        ),
        (
            "multiplier below one",
            lambda d: d["terrain_multipliers"][0].update(multiplier=0.5),
        ),
        (
            "missing thermal id",
            lambda d: d.__setitem__(
                "thermal", [t for t in d["thermal"] if t["id"] != "coolant_critical_c"]
            ),
        ),
        (
            "coolant bands out of order",
            lambda d: next(
                t for t in d["thermal"] if t["id"] == "coolant_hot_max_c"
            ).update(value=99),
        ),
    ]
    failures = 0
    for name, mutate in cases:
        probe = copy.deepcopy(data)
        mutate(probe)
        if not validate(probe):
            print(f"  self-check FAIL: '{name}' was not caught")
            failures += 1
    if failures:
        print(f"fuel data: self-check FAIL ({failures} mutations survived)")
        return 1
    print(f"fuel data: self-check OK ({len(cases)} mutations caught)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--self-check" in args:
        return _self_check()
    path = DEFAULT_DATA
    if args and args[0] not in ("--self-check",):
        path = Path(args[0])
    try:
        data = load(path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"fuel data: FAIL\n  cannot read {path}: {exc}")
        return 1
    errors = validate(data)
    if errors:
        print("fuel data: FAIL")
        for error in errors:
            print(f"  {error}")
        return 1
    print(
        f"fuel data: {len(data['engine_classes'])} engine classes, "
        f"{len(data['fuels'])} fuels, {len(data['terrain_multipliers'])} terrain "
        f"multipliers, {len(data['thermal'])} thermal constants -> {path} (valid)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
