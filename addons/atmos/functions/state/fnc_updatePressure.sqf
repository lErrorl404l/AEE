#include "..\..\script_component.hpp"

params [
    ["_biome", "Cfa", [""]],
    ["_month", 1, [0]],
    ["_posASL", [], [[]]]
];

private _normals = [_biome] call EFUNC(environmental,getClimateNormals);
private _P_sea = _normals select 0;

// ─── Elevation from explicit pos or local player ──────────────────────────
private _pos2D = [0, 0];
if (_posASL isEqualTo []) then {
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player" && {!isNull _player}) then { _pos2D = getPos _player; };
};
if (_pos2D isEqualTo [0, 0] && _posASL isNotEqualTo []) then {
    _pos2D = _posASL select [0, 2];
};

// The reference altitude the core publishes. A bare EGVAR() use reads an
// undefined variable and returns nil, which made the barometric term take
// a nil elevation and the terrain fallback never run.
private _elevation = missionNamespace getVariable [QEGVAR(core,referenceAltitude), 0];
if !(_elevation isEqualType 0) then { _elevation = 0; };
if (_elevation <= 0) then {
    _elevation = getTerrainHeightASL (_pos2D select [0, 2]);
};

// ─── Barometric formula — hypsometric equation ───────────────────────────
// P_station = P_sea * (1 - lapse * elevation / T_std) ^ 5.2559
// The setting is in degrees Celsius per 1000 m (6.5 is the ICAO
// standard), so it is divided by 1000 to get kelvin per metre before it
// enters the formula. Two faults met here: passing the setting through
// unconverted put a 1000-times lapse rate into the term, and the ratio
// was inverted, so pressure rose with height instead of falling. At
// 1000 m the inverted form gave 1142 hPa against the ISA value of
// 898 hPa.
private _T_std = 288.15;       // K
private _lapseRate = missionNamespace getVariable [QEGVAR(core,tempLapseRate), 6.5];
if !(_lapseRate isEqualType 0) then { _lapseRate = 6.5; };
private _lapsePerM = _lapseRate / 1000;
private _exponent = 5.2559;
private _ratio = 1 - (_lapsePerM * _elevation / _T_std);
_ratio = _ratio max 0.05;
private _P_station = _P_sea * (_ratio ^ _exponent);

private _P_final = round (_P_station * 10) / 10;

missionNamespace setVariable [QEGVAR(core,currentPressure), _P_final];
_P_final
