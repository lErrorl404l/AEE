#include "..\..\script_component.hpp"

params [
    ["_biome", "Cfa", [""]],
    ["_month", 1, [0]],
    ["_posASL", [], [[]]]
];

private _normals = [_biome] call EFUNC(weather,getClimateNormals);
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
// The pure formula is the kernel FUNC(calculateStationPressure).  The
// dispatcher selects the native kernel when the dev extension is ready and
// the SQF reference otherwise; both are the same formula.  The lapse rate
// setting is in degrees Celsius per 1000 m (6.5 is the ICAO standard).
private _lapseRate = missionNamespace getVariable [QEGVAR(core,tempLapseRate), 6.5];
if !(_lapseRate isEqualType 0) then { _lapseRate = 6.5; };

private _P_station = ["calculateStationPressure", [_P_sea, _elevation, _lapseRate]] call EFUNC(core,dispatchKernel);
if (_P_station isEqualType "") then { _P_station = parseNumber _P_station; };
if !(_P_station isEqualType 0) then {
    _P_station = [_P_sea, _elevation, _lapseRate] call FUNC(calculateStationPressure);
};

private _P_final = round (_P_station * 10) / 10;

missionNamespace setVariable [QEGVAR(core,currentPressure), _P_final];
_P_final
