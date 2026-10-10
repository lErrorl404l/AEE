#include "..\..\script_component.hpp"

/*
Relative humidity from biome normals, precipitation, surface type, and
the diurnal temperature cycle.

RH couples to the diurnal temperature curve: at constant vapour content,
RH = 100 × e/e_sat(T), so RH falls as temperature rises.  A slow
exponential moving average of temperature (~24 h) gives the daily mean;
warm afternoons depress RH and cool nights raise it, matching the
observed diurnal RH curve.

Stored in QEGVAR(core,currentHumidity).
*/

params [
    ["_biome", "Cfa", [""]],
    ["_month", 1, [0]],
    ["_posASL", [], [[]]]
];

private _normals = [_biome] call EFUNC(weather,getClimateNormals);
private _humidityArray = _normals select 4;
private _RH = _humidityArray select ((_month - 1) max 0 min 11);

// ─── Position for surface modifier ────────────────────────────────────────
private _pos2D = [0, 0];
if (_posASL isEqualTo []) then {
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player" && {!isNull _player}) then { _pos2D = getPos _player; };
};
if (_pos2D isEqualTo [0, 0] && _posASL isNotEqualTo []) then {
    _pos2D = _posASL select [0, 2];
};

private _surfaceMod = 0;
if (_pos2D isNotEqualTo [0, 0]) then {
    // surfaceType returns the surface CLASS NAME with no '#' prefix
    // (GdtDesert).  Normalise to the bare token before comparing.
    private _type = toLower (surfaceType _pos2D);
    if (_type find "#gdt" == 0) then { _type = _type select [4]; }
    else { if (_type find "gdt" == 0) then { _type = _type select [3]; }; };
    _surfaceMod = switch (true) do {
        case (_type == "desert"):      { -15 };
        case (_type == "sand"):        { -10 };
        case (_type == "ice"):         { -10 };
        case (_type == "snow"):        {   5 };
        case (_type == "jungle"):      {  10 };
        case (_type == "rainforest"):  {  12 };
        case (_type == "forest"):      {   5 };
        case (_type == "coniferous"):  {   5 };
        case (_type == "swamp"):       {   8 };
        case (_type == "marsh"):       {   8 };
        case (_type == "water"):       {   5 };
        default                        {   0 };
    };
};
// ─── Diurnal coupling ─────────────────────────────────────────────────────
// Track the daily-mean temperature as a slow exponential moving average
// (~24 h time constant).  RH scales with the saturation vapour-pressure
// ratio: warm afternoon → RH drops, cool night → RH rises.
private _Tnow = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _Tref = missionNamespace getVariable [QGVAR(dailyMeanTemp), _Tnow];
private _interval = EGVAR(core,updateInterval);
_Tref = _Tref + ((_Tnow - _Tref) * (_interval / 86400));
missionNamespace setVariable [QGVAR(dailyMeanTemp), _Tref];

// The surface modifier, the diurnal coupling and the overcast-or-rain
// saturation are the pure kernel FUNC(calculateRelativeHumidity).  The
// dispatcher selects the native kernel when the dev extension is ready and
// the SQF reference otherwise; both are the same formula.
private _RH_final = ["calculateRelativeHumidity", [_RH, _surfaceMod, _Tref, _Tnow, overcast, rain]] call EFUNC(core,dispatchKernel);
if (_RH_final isEqualType "") then { _RH_final = parseNumber _RH_final; };
if !(_RH_final isEqualType 0) then {
    _RH_final = [_RH, _surfaceMod, _Tref, _Tnow, overcast, rain] call FUNC(calculateRelativeHumidity);
};

missionNamespace setVariable [QEGVAR(core,currentHumidity), _RH_final];
_RH_final
