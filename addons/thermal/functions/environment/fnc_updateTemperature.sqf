#include "..\..\script_component.hpp"

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

// Publish the UN-LAPSED base temperature for the ACE3 compat handoff
// (issue #181).  ACE's ace_weather_fnc_calculateTemperatureAtHeight applies
// its OWN 6.5 C/km lapse to ace_weather_currentTemperature on read, so the
// value written there must be the base BEFORE the elevation term below —
// writing the lapse-adjusted currentTemperature double-counts altitude.
missionNamespace setVariable [QEGVAR(core,currentTemperatureBase), _T_base];

// ─── Position ─────────────────────────────────────────────────────────────
private _pos2D = [0, 0];
if (_posASL isEqualTo []) then {
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player" && {!isNull _player}) then { _pos2D = getPos _player; };
};
if (_pos2D isEqualTo [0, 0] && _posASL isNotEqualTo []) then {
    _pos2D = _posASL select [0, 2];
};
if (_pos2D isEqualTo [0, 0]) then { _pos2D = [0, 0]; };

// ─── Elevation ────────────────────────────────────────────────────────────
// The reference altitude the core publishes. A bare EGVAR() use reads an
// undefined variable and returns nil.
private _elevation = missionNamespace getVariable [QEGVAR(core,referenceAltitude), 0];
if !(_elevation isEqualType 0) then { _elevation = 0; };
if (_elevation <= 0) then {
    _elevation = getTerrainHeightASL _pos2D;
};
// The setting is in degrees Celsius per 1000 m and the formula needs
// kelvin per metre, so the value is divided by 1000 here.
private _lapseRate = missionNamespace getVariable [QEGVAR(core,tempLapseRate), 6.5];
if !(_lapseRate isEqualType 0) then { _lapseRate = 6.5; };
private _T_elevation = _T_base - (_lapseRate / 1000) * _elevation;

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

// ─── Urban heat island ───────────────────────────────────────────────────
// A city is warmer than its countryside; the relation and its validity
// limits are in fnc_calculateUrbanHeatIsland (Oke 1973).  The user setting
// scales the computed intensity, so 0 disables the effect and 1 gives the
// published magnitude.
private _uhiSetting = missionNamespace getVariable [QEGVAR(core,urbanHeatIsland), 0];
if !(_uhiSetting isEqualType 0) then { _uhiSetting = 0; };
if (_uhiSetting > 0) then {
    private _signals = missionNamespace getVariable [QEGVAR(environmental,terrainSignals), []];
    private _structures = if (count _signals > 2) then { _signals select 2 } else { [] };
    // The built-up density at this position: the structure vote for the
    // biome, which is the fraction of sampled objects that are buildings.
    private _density = 0;
    if (_structures isEqualType []) then {
        {
            _density = _density max _x;
        } forEach _structures;
    };
    if !(_density isEqualType 0) then { _density = 0; };
    // Publish the built density: the microclimate pooling term yields to
    // it, because built-up ground drains and warms rather than pooling
    // cold air. The two models share one measurement.
    missionNamespace setVariable [QEGVAR(core,builtDensity), _density];
    private _pos = [0, 0, 0];
    private _unit = call CBA_fnc_currentUnit;
    if (!isNil "_unit" && {!isNull _unit}) then { _pos = getPosASL _unit; };
    private _uhi = [_pos, _density] call EFUNC(environmental,calculateUrbanHeatIsland);
    private _uhiOffset = _uhi * (_uhiSetting min 1);
    _T_shade = _T_shade + _uhiOffset;
};

// ─── Local microclimate ──────────────────────────────────────────────────
// Cold-air pooling in a hollow and canopy cooling, sampled over the radius
// the user set.  The mechanisms are in fnc_calculateMicroclimate.
private _mcRadius = missionNamespace getVariable [QEGVAR(core,microclimateRadius), 200];
if !(_mcRadius isEqualType 0) then { _mcRadius = 200; };
if (_mcRadius > 0) then {
    private _mcUnit = call CBA_fnc_currentUnit;
    if (!isNil "_mcUnit" && {!isNull _mcUnit}) then {
        private _mcPos = getPosASL _mcUnit;
        private _mcOffset = [_mcPos, _mcRadius] call EFUNC(environmental,calculateMicroclimate);
        _T_shade = _T_shade + _mcOffset;
    };
};

// ─── Water-body influence ────────────────────────────────────────────────
// A lake or sea moderates the air that crosses it and the effect fades
// inland as the internal boundary layer deepens.  The growth is published;
// fnc_calculateWaterInfluence holds it.
private _wiRadius = missionNamespace getVariable [QEGVAR(core,waterInfluenceRadius), 1000];
if !(_wiRadius isEqualType 0) then { _wiRadius = 1000; };
if (_wiRadius > 0) then {
    private _wiPos2D = _pos2D;
    if (isNil "_wiPos2D") then { _wiPos2D = [0, 0]; };
    private _wiOffset = [[_wiPos2D select 0, _wiPos2D select 1, 0], _wiRadius, 0, _T_wind] call EFUNC(environmental,calculateWaterInfluence);
    _T_shade = _T_shade + _wiOffset;
};

// ─── Output ───────────────────────────────────────────────────────────────
private _T_final = round (_T_shade * 10) / 10;

missionNamespace setVariable [QEGVAR(core,currentTemperature), _T_final];
_T_final
