#include "..\..\script_component.hpp"

/*
Ambient noise floor driver (issue #109).

Reads the engine weather (rain, wind) and AEE's computed foliage density and
local water, calls the pure kernel fnc_ambientNoiseLevel, and publishes the
floor as aee_weather_currentAmbientNoise.  Consumers gate a source against it
with fnc_acousticMasking.  The AI hearing model (#74) takes this beside
aee_weather_currentSoundPropagation.

The water term is the local surface-water fraction over a bounded five-point
probe around the listener, the same shape fnc_calculateWaterInfluence uses.
The floor is local and distance-independent.

Runs from the core environment tick after updateSoundPropagation.
*/

params [["_posASL", [], [[]]]];

private _rain = rain;
private _windMs = vectorMagnitude wind;
private _foliage = missionNamespace getVariable [QGVAR(currentFoliageDensity), 0.5];
if !(_foliage isEqualType 0) then { _foliage = 0.5; };

// ─── Local water fraction ─────────────────────────────────────────────────
// A water body only raises the floor when it is near the listener, so the
// term is a bounded local probe, not the map-wide water fraction.
private _waterFrac = 0;
if ((count _posASL) >= 2) then {
    private _px = _posASL select 0;
    private _py = _posASL select 1;
    private _radius = 25;
    private _samples = 0;
    private _water = 0;
    {
        _x params ["_dx", "_dy"];
        if (surfaceIsWater [_px + _dx, _py + _dy]) then { _water = _water + 1; };
        _samples = _samples + 1;
    } forEach [[0, 0], [_radius, 0], [-_radius, 0], [0, _radius], [0, -_radius]];
    if (_samples > 0) then { _waterFrac = _water / _samples; };
};

private _ambientDb = [_rain, _windMs, _foliage, _waterFrac] call FUNC(ambientNoiseLevel);

missionNamespace setVariable [QGVAR(currentAmbientNoise), _ambientDb];

if (missionNamespace getVariable [QEGVAR(diagnostics,diagnostic), false]) then {
    private _logMsg = format [
        "Ambient noise: %1 dB(A) rain=%2 wind=%3 foliage=%4 water=%5",
        [_ambientDb, 1] call CBA_fnc_formatNumber,
        [_rain, 2] call CBA_fnc_formatNumber,
        [_windMs, 1] call CBA_fnc_formatNumber,
        [_foliage, 2] call CBA_fnc_formatNumber,
        [_waterFrac, 2] call CBA_fnc_formatNumber
    ];
    AEE_LOG_INFO(_logMsg);
};

_ambientDb
