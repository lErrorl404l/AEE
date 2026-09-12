#include "..\script_component.hpp"

params [
    ["_biome", "Cfa"],
    ["_month", 1],
    ["_posASL", []]
];

// Defensive: garbage params (nil / objNull from test edge cases) must not
// crash the function.  Coerce to the documented defaults.  (No strict
// type constraint in params above — a strict [""] check throws before
// this code can run.)
if !(_biome isEqualType "") then { _biome = "Cfa"; };
if !(_month isEqualType 0) then { _month = 1; };
if !(_posASL isEqualType []) then { _posASL = []; };
if ((count _posASL) == 1 && {(_posASL select 0) isEqualType []}) then {
    _posASL = _posASL select 0;
};

// ─── Base diurnal calculation ──────────────────────────────────────────────
private _normals = [_biome] call EFUNC(environmental,getClimateNormals);
private _tDay   = _normals select 2;
private _tNight = _normals select 3;

// Solar-elevation radiation model (replaces a fixed sinusoid): the sun's
// height for the date, time and latitude drives the diurnal curve.
private _diurnalWeight = [overcast] call EFUNC(core,calculateSolarRadiation);
private _monthIdx = (_month - 1) max 0 min 11;
private _T_base = (_tNight select _monthIdx)
    + ((_tDay select _monthIdx) - (_tNight select _monthIdx)) * _diurnalWeight;

// ─── Position ─────────────────────────────────────────────────────────────
private _pos2D = [0, 0];
if (_posASL isEqualTo []) then {
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player") then { _pos2D = getPos _player; };
};
if (_pos2D isEqualTo [0, 0] && _posASL isNotEqualTo []) then {
    _pos2D = _posASL select [0, 2];
};
if (_pos2D isEqualTo [0, 0]) then { _pos2D = [0, 0]; };

// ─── Elevation ────────────────────────────────────────────────────────────
private _elevation = EGVAR(core,referenceAltitude);
if (_elevation <= 0) then {
    _elevation = getTerrainHeightASL _pos2D;
};
private _T_elevation = _T_base - 0.0065 * _elevation;

// ─── Overcast ─────────────────────────────────────────────────────────────
private _T_overcast = _T_elevation - 4 * overcast;

// ─── Surface modifier ─────────────────────────────────────────────────────
private _surfaceMod = 0;
if (_pos2D isNotEqualTo [0, 0]) then {
    private _type = toLower (surfaceType _pos2D);
    _surfaceMod = switch (true) do {
        case (_type == "#gdtdesert"):        {  4   };
        case (_type == "#gdtsand"):          {  2   };
        case (_type == "#gdtice"):           { -5   };
        case (_type == "#gdtsnow"):          { -3   };
        case (_type == "#gdtconiferous"):    { -2   };
        case (_type == "#gdtforest"):        { -1.5 };
        default                              {  0   };
    };
};
private _T_surface = _T_overcast + _surfaceMod;

// ─── Wind chill (JAG/TTI metric formula) ────────────────────────────────
//   Twc = 13.12 + 0.6215*T - 11.37*(V*3.6)^0.16 + 0.3965*T*(V*3.6)^0.16
//   T = air temperature (°C), V = wind speed (m/s, converted to km/h)
//   Valid for T ≤ 10°C and V > 4.8 km/h (1.34 m/s).
//   Above those thresholds, wind chill = ambient (no meaningful chilling).
private _windSpeed = vectorMagnitude wind;
private _T_wind = _T_surface;
if (_T_base <= 10 && _windSpeed > 1.34) then {
    private _V_kmh = _windSpeed * 3.6;
    private _Vexp = _V_kmh ^ 0.16;
    private _windChillJAGTTI = 13.12 + 0.6215 * _T_surface - 11.37 * _Vexp + 0.3965 * _T_surface * _Vexp;
    // Clamp: JAG/TTI formula wind chill must be ≤ ambient temp
    if (_windChillJAGTTI < _T_surface) then {
        _T_wind = _windChillJAGTTI;
    };
};

// ─── Shade ────────────────────────────────────────────────────────────────
private _inShade = false;
if (_pos2D isNotEqualTo [0, 0]) then {
    private _eyePos = [_pos2D#0, _pos2D#1, _elevation + 1.5];
    private _abovePos = _eyePos vectorAdd [0, 0, 6];
    private _hits = lineIntersectsSurfaces [
        _eyePos, _abovePos,
        objNull, objNull, true, 1, "GEOM", "NONE"
    ];
    if (count _hits > 0) then { _inShade = true; };
};
private _T_shade = _T_wind - ([0, 3] select _inShade);

// ─── Module temperature offset ───────────────────────────────────────────
// Apply a fixed offset configured via EDEN/Zeus module
private _moduleOffset = missionNamespace getVariable [QEGVAR(core,moduleTempOffset), 0];
_T_shade = _T_shade + _moduleOffset;

// ─── Output ───────────────────────────────────────────────────────────────
private _T_final = round (_T_shade * 10) / 10;

missionNamespace setVariable [QEGVAR(core,currentTemperature), _T_final];
_T_final
