#include "..\script_component.hpp"

params [
    ["_biome", "Cfa", [""]],
    ["_month", 1, [0]],
    ["_posASL", [], [[]]]
];

private _normals = [_biome] call EFUNC(environmental,getClimateNormals);
private _humidityArray = _normals select 4;
private _RH = _humidityArray select ((_month - 1) max 0 min 11);

// Saturation under overcast or rain
if (overcast > 0.7 || rain > 0) then { _RH = 100; };

// ─── Position for surface modifier ────────────────────────────────────────
private _pos2D = [0, 0];
if (_posASL isEqualTo []) then {
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player") then { _pos2D = getPos _player; };
};
if (_pos2D isEqualTo [0, 0] && _posASL isNotEqualTo []) then {
    _pos2D = _posASL select [0, 2];
};

private _surfaceMod = 0;
if (_pos2D isNotEqualTo [0, 0]) then {
    private _type = toLower (surfaceType _pos2D);
    _surfaceMod = switch (true) do {
        case (_type == "#gdtdesert"):      { -15 };
        case (_type == "#gdtsand"):        { -10 };
        case (_type == "#gdtice"):         { -10 };
        case (_type == "#gdtsnow"):        {   5 };
        case (_type == "#gdtjungle"):      {  10 };
        case (_type == "#gdtrainforest"):  {  12 };
        case (_type == "#gdtforest"):      {   5 };
        case (_type == "#gdtconiferous"):  {   5 };
        case (_type == "#gdtswamp"):       {   8 };
        case (_type == "#gdtmarsh"):       {   8 };
        case (_type == "#gdtwater"):       {   5 };
        default                            {   0 };
    };
};
_RH = (_RH + _surfaceMod) max 0 min 100;

private _RH_final = round _RH;

missionNamespace setVariable [QEGVAR(core,currentHumidity), _RH_final];
_RH_final
