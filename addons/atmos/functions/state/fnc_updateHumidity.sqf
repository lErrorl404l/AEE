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

private _normals = [_biome] call EFUNC(environmental,getClimateNormals);
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
_RH = (_RH + _surfaceMod) max 0 min 100;

// ─── Diurnal coupling ─────────────────────────────────────────────────────
// Track the daily-mean temperature as a slow exponential moving average
// (~24 h time constant).  RH scales with the saturation vapour-pressure
// ratio: warm afternoon → RH drops, cool night → RH rises.
private _Tnow = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _Tref = missionNamespace getVariable [QGVAR(dailyMeanTemp), _Tnow];
private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
_Tref = _Tref + ((_Tnow - _Tref) * (_interval / 86400));
missionNamespace setVariable [QGVAR(dailyMeanTemp), _Tref];

_RH = _RH * (1 + (_Tref - _Tnow) * 0.05);
_RH = _RH max 0 min 100;

// Saturation under overcast or rain — hard constraint
if (overcast > 0.7 || rain > 0) then { _RH = 100; };

private _RH_final = round _RH;

missionNamespace setVariable [QEGVAR(core,currentHumidity), _RH_final];
_RH_final
