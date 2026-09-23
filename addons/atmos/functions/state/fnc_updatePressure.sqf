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
    if (!isNil "_player") then { _pos2D = getPos _player; };
};
if (_pos2D isEqualTo [0, 0] && _posASL isNotEqualTo []) then {
    _pos2D = _posASL select [0, 2];
};

private _elevation = EGVAR(core,referenceAltitude);
if (_elevation <= 0) then {
    _elevation = getTerrainHeightASL (_pos2D select [0, 2]);
};

// ─── Barometric formula — hypsometric equation ───────────────────────────
// P_station = P_sea * (T_std / (T_std - lapse * elevation))^5.2559
// The lapse rate is the user setting when one is supplied, so the slider
// changes the model rather than decorating the UI.  The ICAO standard is
// 0.0065 K/m, and that stands when the setting is absent.
private _T_std = 288.15;       // K
private _lapseRate = missionNamespace getVariable [QEGVAR(core,tempLapseRate), 0.0065];
if !(_lapseRate isEqualType 0) then { _lapseRate = 0.0065; };
private _exponent = 5.2559;
private _ratio = _T_std / (_T_std - _lapseRate * _elevation);
private _P_station = _P_sea * (_ratio ^ _exponent);

private _P_final = round (_P_station * 10) / 10;

missionNamespace setVariable [QEGVAR(core,currentPressure), _P_final];
_P_final
