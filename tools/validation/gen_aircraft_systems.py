#!/usr/bin/env python3
"""Generate the runtime aircraft systems lookup from the catalogue.

The aircraft catalogue holds one entry per real aircraft variant. An entry
carries a value, a unit, a source, a locator, a state and a grade per field.
This generator reads the shared catalogue loader output through the aircraft
profile and writes one SQF file:

  addons/flight/functions/fnc_getAircraftSystems.sqf  the systems row lookup

The systems row carries the numeric systems fields in fixed order, then the
enum systems fields. The generated file states the ordered field-name tuple,
so a consumer indexes a value by name. An absent field is a labelled zero.

The lookup is a thin consumer of the generated matcher. It resolves the class
through the matcher, then returns the systems row of the unique catalogue
entry. It reads no config value and no source registry at runtime. An unknown
class returns [].

Run:  python3 tools/validation/gen_aircraft_systems.py
      python3 tools/validation/gen_aircraft_systems.py --data-dir PATH
      python3 tools/validation/gen_aircraft_systems.py --check
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

# A package import (tests) and a direct script run both resolve the sibling
# modules. The repository root goes on the path first.
_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

ROOT = _REPO
DEFAULT_DATA = ROOT / "data" / "aircraft"
SYSTEMS_OUT = ROOT / "addons" / "flight" / "functions" / "fnc_getAircraftSystems.sqf"

# The aircraft profile selects the type enum and the named derivations. The
# type enum is fixed_wing and rotary_wing.
PROFILE = catalogue.AIRCRAFT_PROFILE

# The numeric systems fields, in fixed projection order. The order is the
# contract a consumer indexes by name.
SYSTEMS_FIELDS = (
    "fuel_capacity",
    "fuel_consumption_rate",
    "fuel_density_kg_l",
    "sfc_kg_kwh",
    "fuel_cg_arm_m",
    "engine_idle_ng",
    "engine_max_ng",
    "engine_max_np",
    "engine_max_torque_nm",
    "engine_max_tgt_c",
    "engine_oil_pressure_min_kpa",
    "engine_oil_pressure_max_kpa",
    "transmission_torque_limit_nm",
    "hydraulic_pressure_kpa",
    "generator_power_kw",
    "bus_voltage_v",
    "battery_capacity_ah",
    "cabin_pressure_max_kpa",
)

# The enum systems fields, in fixed projection order, appended after the
# numeric fields.
SYSTEMS_ENUM_FIELDS = (
    "fuel_type",
    "engine_oil_type",
    "oxygen_system",
)

# The full ordered field-name tuple. The row holds one value per name, in
# this order.
SYSTEMS_ROW_FIELDS = SYSTEMS_FIELDS + SYSTEMS_ENUM_FIELDS

SYSTEMS_TEMPLATE = """#include "..\\script_component.hpp"
/*
Aircraft systems runtime lookup (issue #117).

Function: aee_flight_fnc_getAircraftSystems.

This file is GENERATED. The generator tools/validation/gen_aircraft_systems.py
writes it from the validated aircraft catalogue under data/aircraft/. Do not
edit it by hand. Edit the corpus and regenerate it.

The lookup is a thin consumer of aee_flight_fnc_getAircraftMatch. It returns
the systems row of a unique match, or an empty array. The systems row is a
fixed-order array. A consumer indexes a value by name through the ordered
field-name tuple.

The row holds the numeric systems fields first, in order:

  SYSTEMS_FIELDS
  __FIELDS__

then the enum systems fields, in order:

  SYSTEMS_ENUM_FIELDS
  __ENUM_FIELDS__

A field the corpus does not hold is a labelled absent zero. The numeric
fields carry a figure. The enum fields carry a token or a zero. The lookup
reads no config value and no source registry. It returns no default.

Arguments:
  0: className (STRING, the CfgVehicles classname, default "")
*/
params [["_className", "", [""]]];
if (_className == "") exitWith { [] };

private _match = [_className] call FUNC(getAircraftMatch);
if (_match isEqualTo []) exitWith { [] };

private _catalogue = _match select 0;
private _variant = _match select 1;

private _table = [
__ROWS__
];
private _row = _table select {
    ((_x select 0) == _catalogue) && { (_x select 1) == _variant }
};
if (_row isEqualTo []) exitWith { [] };
(_row select 0) select 2
"""


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _text(value: object) -> str | None:
    """Return a non-empty string, or None."""
    if isinstance(value, str) and value.strip():
        return value
    return None


def resolve_row(record: object) -> list[catalogue.ResolvedField] | None:
    """Return the graded systems fields of a record, or None when no row emits.

    A row emits for every entry whose identity is complete: a catalogue id, a
    variant id and a supported aircraft type. A missing value never refuses the
    row. It resolves to a labelled absent zero, so a held entry always
    projects. The row holds the numeric systems fields then the enum systems
    fields, in the fixed ``SYSTEMS_ROW_FIELDS`` order.
    """
    entry = _mapping(record)
    if entry is None:
        return None
    if _text(entry.get("catalogue_id")) is None:
        return None
    if _text(entry.get("variant_id")) is None:
        return None
    vehicle_type = entry.get("vehicle_type")
    if not isinstance(vehicle_type, str):
        return None
    if vehicle_type not in PROFILE.vehicle_types:
        return None
    values = _mapping(entry.get("values"))
    if values is None:
        values = {}
    return [
        catalogue.resolve_field(values, field, PROFILE) for field in SYSTEMS_ROW_FIELDS
    ]


def build_row(record: object) -> list[object] | None:
    """Return one runtime row, or None when the record has no identity.

    The row is ``[catalogue_id, variant_id, [systems values]]``. Every value
    is graded in ``resolve_row``: a held value, a named derivation or a
    labelled zero.
    """
    fields = resolve_row(record)
    if fields is None:
        return None
    entry = _mapping(record)
    assert entry is not None

    catalogue_id = _text(entry.get("catalogue_id")) or ""
    variant_id = _text(entry.get("variant_id")) or ""
    return [catalogue_id, variant_id, [field.value for field in fields]]


def build_rows(records: Iterable[object]) -> list[list[object]]:
    """Build every row and sort it. The order is catalogue then variant."""
    rows: list[list[object]] = []
    for record in records:
        row = build_row(record)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda row: (str(row[0]), str(row[1])))
    return rows


def load_rows(data_dir: Path = DEFAULT_DATA) -> list[list[object]]:
    """Read the catalogue layer through the aircraft profile and build rows."""
    load = catalogue.load(data_dir, profile=PROFILE)
    return build_rows(entry.to_mapping() for entry in load.entries)


def _sqf(value: object) -> str:
    """Render one SQF literal. A string is quoted and escaped."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value.replace('"', '""') + '"'
    return str(value)


def format_row(row: Sequence[object]) -> str:
    """Render one row in the fixed three-column shape."""
    values = row[2]
    assert isinstance(values, (list, tuple))
    rendered = ", ".join(_sqf(item) for item in values)
    return f"    [{_sqf(row[0])}, {_sqf(row[1])}, [{rendered}]]"


def render_systems(rows: Sequence[Sequence[object]]) -> str:
    """Render the systems lookup file for the given rows."""
    body = ",\n".join(format_row(row) for row in rows)
    return (
        SYSTEMS_TEMPLATE.replace("__ROWS__", body)
        .replace("__FIELDS__", ", ".join(SYSTEMS_FIELDS))
        .replace("__ENUM_FIELDS__", ", ".join(SYSTEMS_ENUM_FIELDS))
    )


def write_outputs(data_dir: Path = DEFAULT_DATA) -> list[list[object]]:
    """Write the generated file and return the rows."""
    rows = load_rows(data_dir)
    SYSTEMS_OUT.write_text(render_systems(rows), encoding="utf-8")
    return rows


def check_outputs(
    data_dir: Path,
    out: Path = SYSTEMS_OUT,
) -> int:
    """Return 0 when the generated file matches a fresh render.

    Check mode writes nothing. A missing or stale file returns 1, so a stale
    generated lookup fails the gate.
    """
    rows = load_rows(data_dir)
    expected = render_systems(rows)
    if not out.is_file():
        print(f"aircraft systems: {out} is missing; run the generator")
        return 1
    if out.read_text(encoding="utf-8") != expected:
        print(f"aircraft systems: {out} is stale; run the generator")
        return 1
    print(f"aircraft systems: {len(rows)} rows -> {out.name} (fresh)")
    return 0


def main(argv: Sequence[str]) -> int:
    data_dir = DEFAULT_DATA
    if "--data-dir" in argv:
        index = argv.index("--data-dir")
        if index + 1 < len(argv):
            data_dir = Path(argv[index + 1])
    if "--check" in argv:
        return check_outputs(data_dir)
    rows = write_outputs(data_dir)
    load = catalogue.load(data_dir, profile=PROFILE)
    print(
        f"aircraft systems rows: {len(rows)} from "
        f"{len(load.entries)} catalogue entries, wrote {SYSTEMS_OUT.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
