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
// Climate normals at sea level (fnc_getClimateNormals: the world's reference
// station, else the nearest WMO 1991-2020 station).  The day's maximum and
// minimum are interpolated between the mid-month normals of the date.
private _normals = [_biome] call EFUNC(weather,getClimateNormals);
private _tDay   = _normals select 2;
private _tNight = _normals select 3;
// Run the solar model for the sun state (position, declination) it publishes.
[overcast] call EFUNC(lighting,calculateSolarRadiation);
date params ["_dy", "_dm", "_dd"];
private _midFrac = (_dd - 15.2) / 30.44;               // months from mid-month
private _m0 = (_dm - 1) + (floor _midFrac);
private _w = _midFrac - (floor _midFrac);
private _i0 = ((_m0 mod 12) + 12) mod 12;
private _i1 = (_i0 + 1) mod 12;
private _tMax = ((_tDay select _i0) * (1 - _w)) + ((_tDay select _i1) * _w);
private _tMin = ((_tNight select _i0) * (1 - _w)) + ((_tNight select _i1) * _w);

// Diurnal course: Parton & Logan (1981, Agric. Meteorol. 23:205), the
// APSIM implementation (Utilities.cpp, as ported in the weaana package):
// a sine from C hours after sunrise to sunset peaking A hours after noon,
// then an exponential decay to the minimum, A = 1.5 h, B = 4, C = 1 h.
// The clock is local apparent solar time (the engine's), so sunrise and
// sunset are 12 -/+ half the day length; the day length is the real one,
// from the sun's declination and the latitude with the standard -0.833 deg
// sunrise altitude (refraction and semi-diameter).
private _lat = ([] call EFUNC(lib,getWorldLocation)) select 0;
private _dec = missionNamespace getVariable [QEGVAR(core,currentSunDeclination), 0];
if !(_dec isEqualType 0) then { _dec = 0; };
private _cosH0 = ((sin -0.833) - (sin _lat) * (sin _dec)) / ((cos _lat) * (cos _dec));
private _dayLen = 24 * ((acos ((_cosH0 max -1) min 1)) / 180);
private _A = 1.5;
private _B = 4;
private _C = 1;
private _hour = dayTime;
private _rise = 12 - (_dayLen / 2) + _C;
private _set = 12 + (_dayLen / 2);
private _T_base = _tMin;
if (_dayLen >= 24) then {
    _T_base = _tMin + (_tMax - _tMin) * (0.5 + 0.5 * (cos ((_hour - 12 - _A) * 15)));
} else {
    if (_dayLen > _C) then {
        if (_hour >= _rise && _hour < _set) then {
            _T_base = _tMin + (_tMax - _tMin) * (sin (180 * (_hour - _rise) / (_dayLen + 2 * _A)));
        } else {
            private _since = if (_hour >= _set) then { _hour - _set } else { (24 - _set) + _hour };
            private _tSet = _tMin + (_tMax - _tMin) * (sin (180 * (_dayLen - _C) / (_dayLen + 2 * _A)));
            _T_base = _tMin + (_tSet - _tMin) * exp (-_B * _since / (24 - _dayLen));
        };
    };
};

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
// The day's mean temperature at this height: the humidity model holds the
// day's vapour pressure at it (fnc_calculateRelativeHumidity).
missionNamespace setVariable [QEGVAR(core,currentDayMeanTemp), ((_tMax + _tMin) / 2) - (_lapseRate / 1000) * _elevation];

// Air temperature is the screen (shaded, ventilated) value: cloud is in the
// station normals, wind chill is a perceived index (published by
// aee_strain_fnc_calculateColdWeatherPerformance as windChillTemp) and the
// sun's radiant load is in the mean radiant temperature (fnc_calculateMRT),
// so none of them is added to the air temperature here.
private _T_shade = _T_elevation;

// ─── Module temperature offset ───────────────────────────────────────────
// Apply a fixed offset configured via EDEN/Zeus module
private _moduleOffset = missionNamespace getVariable [QEGVAR(core,moduleTempOffset), 0];
_T_shade = _T_shade + _moduleOffset;

// ─── Volcanic winter ──────────────────────────────────────────────────────
// A large eruption cools the surface for one to three years (Robock 2000).
// The atmos volcanic model publishes the regional cooling (issue #25).
private _volcanicCooling = missionNamespace getVariable [QEGVAR(atmos,volcanicWinterRegionalCooling_C), 0];
if !(_volcanicCooling isEqualType 0) then { _volcanicCooling = 0; };
_T_shade = _T_shade - _volcanicCooling;

// ─── Urban heat island ───────────────────────────────────────────────────
// A city is warmer than its countryside; the relation and its validity
// limits are in fnc_calculateUrbanHeatIsland (Oke 1973).  The user setting
// scales the computed intensity, so 0 disables the effect and 1 gives the
// published magnitude.
private _uhiSetting = missionNamespace getVariable [QEGVAR(core,urbanHeatIsland), 0];
if !(_uhiSetting isEqualType 0) then { _uhiSetting = 0; };
if (_uhiSetting > 0) then {
    private _signals = missionNamespace getVariable [QEGVAR(weather,terrainSignals), []];
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
    private _uhi = [_pos, _density] call EFUNC(weather,calculateUrbanHeatIsland);
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
        private _mcOffset = [_mcPos, _mcRadius] call EFUNC(weather,calculateMicroclimate);
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
    private _wiOffset = [[_wiPos2D select 0, _wiPos2D select 1, 0], _wiRadius, 0, _T_shade] call EFUNC(weather,calculateWaterInfluence);
    _T_shade = _T_shade + _wiOffset;
};

// ─── Output ───────────────────────────────────────────────────────────────
private _T_final = round (_T_shade * 10) / 10;

missionNamespace setVariable [QEGVAR(core,currentTemperature), _T_final];
_T_final
