#include "..\script_component.hpp"
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
    ["heat|m456", "105mm_m456_load", "105mm_m68", 1173.0, 0.0, 0.0, "documented"],
    ["apfsds|m829", "120mm_m829_load", "120mm_m256_smoothbore", 1679.45, 510.0, 8141.98, "documented"],
    ["heat|m830", "120mm_m830_load", "120mm_m256_smoothbore", 1139.95, 479.87, 0.0, "documented"],
    ["125mm2a46|125mmm88|125mmtanksmoothbore|2a46|apfsds|m88", "125mm_m88_load", "125mm_2a46", 1785.0, 0.0, 2000.0, "claimed"],
    ["127x108|127x108mm", "127x108_ap_load", "127x108", 810.0, 0.0, 0.0, "documented"],
    ["20mmautocannon|20x102|20x102mm|m55a2", "20x102_m55a2_load", "20x102", 1030.22, 417.13, 0.0, "documented"],
    ["hei|m792", "25x137_m792_load", "25x137", 1100.0, 0.0, 90.0, "documented"],
    ["apfsds|m919", "25x137_m919_load", "25x137", 1420.0, 386.11, 98.0, "documented"],
    ["30mmm230|30x113|30x113mm|hedp|m789", "30x113_m789_load", "30x113", 804.67, 309.92, 0.0, "documented"],
    ["30mmbushmasteriimk44|30x173|30x173mm|mk239", "30x173_mk239_load", "30x173", 1080.0, 345.0, 0.0, "claimed"],
    ["40mmmk19|40x53|40x53mm|hedp|m430", "40x53_m430_load", "40x53", 241.0, 0.0, 0.0, "documented"],
    ["m17", "50_bmg_m17", "50_bmg", 886.97, 379.2, 0.0, "documented"],
    ["m33", "50_bmg_m33", "50_bmg", 886.97, 379.2, 0.0, "documented"],
    ["api|m20", "50_bmg_m8_api_and_m20_api_t", "50_bmg", 886.97, 379.2, 0.0, "documented"]
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
