#!/usr/bin/env python3
"""Generate the runtime load resolver from the verified database.

The research database under data/ballistics/ is the source of truth. This
tool projects the load layer into one SQF function that resolves an
ammunition classname to the sourced load record (service velocity and
service pressure) for a cannon, autocannon or heavy machine gun round.

The small-arms muzzle velocity is derived from the cartridge curve in
fnc_deriveCartridge. A cannon has no such curve: the interior-ballistics
model is fitted to small arms and returns 0 above 20 mm. The service
velocity in the load record is then the value, because a found value
beats a formula (ADR-003).

Aliases come from the cartridge identity, the projectile designation and
the load id. A classname token that matches more than one load is
ambiguous: the runtime resolver returns nothing rather than guess.

Run:  python3 tools/validation/gen_runtime_loads.py
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
LOADS = DATA / "loads.json"
CARTRIDGES = DATA / "cartridges.json"
OUT = Path(__file__).parents[2] / "addons/ballistics/functions/fnc_getLoadData.sqf"

MIN_ALIAS = 3
# Words that name the record shape, not the round. They must never become
# an alias, or every load would match every classname.
GENERIC = {
    "load",
    "loads",
    "ball",
    "round",
    "shell",
    "service",
    "projectile",
    "cartridge",
    "tracer",
    "the",
    "and",
}


def norm(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def tokens(text):
    out = set()
    for tok in re.split(r"[^a-z0-9]+", (text or "").lower()):
        if len(tok) >= MIN_ALIAS and tok not in GENERIC:
            out.add(tok)
    return out


def value(record, field):
    entry = record.get("values", {}).get(field)
    return entry["value"] if entry else None


def source(record, field):
    entry = record.get("values", {}).get(field)
    return entry.get("grade", "") if entry else ""


def aliases_for(record, cartridges):
    """Every alias a load carries, before the ambiguity filter."""
    cartridge_id = record.get("cartridge_id", "")
    aliases = set()
    aliases |= tokens(cartridge_id)
    aliases.add(norm(cartridge_id))
    aliases |= tokens(record.get("load_id", ""))
    aliases |= tokens(record.get("projectile", ""))
    cart = cartridges.get(cartridge_id, {})
    aliases |= tokens(cart.get("name", ""))
    for name in cart.get("names", []) or cart.get("aliases", []) or []:
        aliases.add(norm(name))
    for exclude in cart.get("alias_exclude", []) or []:
        aliases.discard(norm(exclude))
    out = set()
    for a in aliases:
        if len(a) < MIN_ALIAS:
            continue
        # A bare millimetre form such as 30mm names a bore, not a round.
        # Two cartridges can share it (30x113 against 30x173), so it must
        # not select a load. The case form (30x173) and the round
        # designation (m789) are kept.
        if re.fullmatch(r"[0-9]+mm", a):
            continue
        # A pure digit run is a case length or a bore, not an identity.
        if a.isdigit():
            continue
        out.add(a)
    return out


def calibre_mm(record, cartridges):
    cart = cartridges.get(record.get("cartridge_id", ""), {})
    entry = cart.get("values", {}).get("calibre_mm")
    if entry and entry.get("value"):
        return float(entry["value"])
    value = cart.get("calibre_mm")
    return float(value) if isinstance(value, (int, float)) else 0.0


def row(record, keep):
    mv = value(record, "service_velocity_ms")
    if mv is None:
        return None
    aliases = sorted(keep)
    if not aliases:
        return None
    pressure = value(record, "service_pressure_mpa") or 0
    charge = value(record, "charge_mass_g") or 0
    return [
        "|".join(aliases),
        record.get("load_id", ""),
        record.get("cartridge_id", ""),
        float(mv),
        float(pressure),
        float(charge),
        source(record, "service_velocity_ms"),
    ]


TEMPLATE = """#include "..\\script_component.hpp"
/*
Load resolver (vehicle-weapon integration).

Resolves an ammunition classname to the sourced load record for a cannon,
autocannon or heavy machine gun round. This file is a GENERATED runtime
projection of data/ballistics/loads.json. It is written by
tools/validation/gen_runtime_loads.py and must not be edited by hand.

A load value is a FOUND value. Per ADR-003 a found value beats a derived
value, so this record supplies the service velocity where the
interior-ballistics model is deferred (a cannon calibre).

The resolver matches a whole classname token against the aliases. A token
that matches more than one load is ambiguous, so the resolver returns
nothing rather than guess. The result is cached by classname, because the
Fired event calls this on every shot.

Returns [load_id, cartridge_id, service_velocity_ms, service_pressure_mpa,
charge_mass_g, velocity_grade], or an empty array when nothing matches.

Arguments:
  0: ammo (STRING, the CfgAmmo classname, default "")
*/
params [["_ammo", "", [""]]];
if (_ammo == "") exitWith { [] };

private _cache = missionNamespace getVariable [QGVAR(loadCache), nil];
if (isNil "_cache") then {
    _cache = createHashMap;
    missionNamespace setVariable [QGVAR(loadCache), _cache];
};
private _cached = _cache getOrDefault [_ammo, []];
if (_cached isNotEqualTo []) exitWith { _cached };

// [aliases (lower-case, pipe separated), load_id, cartridge_id, mv m/s,
//  pressure MPa, charge g, velocity grade]
private _TABLE = [
__ROWS__
];

// The alias index is built once per mission. Each alias maps to the list
// of table rows that carry it, so the per-shot path is a token lookup.
private _index = missionNamespace getVariable [QGVAR(loadIndex), nil];
if (isNil "_index") then {
    _index = createHashMap;
    {
        _x params ["_aliases"];
        private _rowIndex = _forEachIndex;
        {
            private _bucket = _index getOrDefault [_x, []];
            _bucket pushBack _rowIndex;
            _index set [_x, _bucket];
        } forEach (_aliases splitString "|");
    } forEach _TABLE;
    missionNamespace setVariable [QGVAR(loadIndex), _index];
};

// Score each candidate row by how many classname tokens match its
// aliases. The strongest match wins. A tie means the identity is not
// specific enough, so nothing is returned rather than a guess.
private _scores = createHashMap;
{
    private _bucket = _index get _x;
    if (!isNil "_bucket") then {
        { _scores set [_x, (_scores getOrDefault [_x, 0]) + 1]; } forEach _bucket;
    };
} forEach ((toLower _ammo) splitString " _-.");

private _bestScore = 0;
private _bestRow = -1;
private _tied = false;
{
    if (_y > _bestScore) then {
        _bestScore = _y;
        _bestRow = _x;
        _tied = false;
    } else {
        if (_y == _bestScore) then { _tied = true; };
    };
} forEach _scores;

private _result = if (_bestRow < 0 || _tied) then { [] } else {
    private _row = _TABLE select _bestRow;
    [_row select 1, _row select 2, _row select 3, _row select 4, _row select 5, _row select 6]
};
_cache set [_ammo, _result];
_result
"""


def main():
    loads = json.loads(LOADS.read_text(encoding="utf-8"))
    cartridges = {
        c["cartridge_id"]: c for c in json.loads(CARTRIDGES.read_text(encoding="utf-8"))
    }
    # An alias shared by two loads of the same cartridge cannot pick one.
    # Count every load, including a load with no velocity (E105 mm holds an
    # M735 record with no service velocity), so the shared calibre alias is
    # dropped and only the round designation selects a load.
    aliases = [aliases_for(rec, cartridges) for rec in loads]
    counts = {}
    for rec, names in zip(loads, aliases):
        bucket = counts.setdefault(rec.get("cartridge_id", ""), {})
        for name in names:
            bucket[name] = bucket.get(name, 0) + 1
    rows = []
    for rec, names in zip(loads, aliases):
        # Keep the vehicle-weapon loads: the heavy machine gun (12.7 mm and
        # above) and the cannon and autocannon. A small-arms load is not a
        # vehicle weapon and is resolved by the cartridge curve instead.
        if calibre_mm(rec, cartridges) < 12.7:
            continue
        bucket = counts.get(rec.get("cartridge_id", ""), {})
        keep = {a for a in names if bucket.get(a, 0) == 1}
        built = row(rec, keep)
        if built:
            rows.append(built)
    rows.sort(key=lambda r: (r[2], r[1]))
    body = ",\n".join(
        '    ["{}", "{}", "{}", {}, {}, {}, "{}"]'.format(*r) for r in rows
    )
    text = TEMPLATE.replace("__ROWS__", body)
    OUT.write_text(text, encoding="utf-8")
    print(f"load rows: {len(rows)}, wrote {OUT.name} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
