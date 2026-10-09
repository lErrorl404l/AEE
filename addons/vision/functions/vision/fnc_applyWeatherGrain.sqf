#include "..\..\script_component.hpp"

/*
Rain-scaled film grain driver (aee-workshop-copy item 5).

Owns one FilmGrain through the core registry under the "optics" scope, key
"WeatherGrain", at priority 1747.  The source used 1747; no other AEE effect
uses it (tools/tests/test_weather_grain.py proves the priority free across
every ppEffectCreate call), and the registry bumps the priority if the engine
ever hands back a handle another scope already holds.

The kernel FUNC(weatherGrainParams) picks the six-element FilmGrain array
from rain and sunOrMoon.  This driver scales its intensity by two factors:

  aee_vision_weatherGrainIntensity  operator setting, range 0 to 1
  aee_environmental_worldLighting   element 2, the matcher grain scale
                                    (default 1 when the matcher has not run)

Lifecycle (the existing hysteresis pattern from fnc_managePostProcess):
  - engages above the rain on-threshold and disengages below the off-threshold
    (off < on), so a value at the boundary does not toggle every tick;
  - normal vision only: NVG and thermal own their own grain, so the effect
    stands down in a sensor mode;
  - stands down when the optics module is disabled.

Client-only.  Args: none.  Returns: nothing.
*/

if (!hasInterface) exitWith {};

private _unit = call CBA_fnc_currentUnit;
if (isNull _unit) exitWith {};

private _standDown = (currentVisionMode _unit != 0)
    || {!(missionNamespace getVariable [QEGVAR(core,opticsEnabled), true])};

private _hGrain = ["optics", "WeatherGrain", "FilmGrain", 1747, ""] call EFUNC(lib,createPPEffect);

private _active = missionNamespace getVariable [QGVAR(weatherGrainActive), false];

if (_standDown) exitWith {
    if (_hGrain >= 0) then {
        if (_active) then {
            _hGrain ppEffectEnable false;
            missionNamespace setVariable [QGVAR(weatherGrainActive), false];
        };
    };
};

private _rain = rain;
if !(_rain isEqualType 0) then { _rain = 0; };
private _sunOrMoon = sunOrMoon;
if !(_sunOrMoon isEqualType 0) then { _sunOrMoon = 1; };

// The matcher publishes the per-world grain scale as element 2 of
// aee_environmental_worldLighting.  Default 1 when it has not run.
private _profile = missionNamespace getVariable [QEGVAR(environmental,worldLighting), [1, 1, 1, 1]];
private _grainScale = 1;
if ((_profile isEqualType []) && {(count _profile) > 2}) then {
    _grainScale = _profile select 2;
};
if !(_grainScale isEqualType 0) then { _grainScale = 1; };

private _intensitySetting = missionNamespace getVariable [QGVAR(weatherGrainIntensity), 0.5];
if !(_intensitySetting isEqualType 0) then { _intensitySetting = 0.5; };
private _rainThreshold = missionNamespace getVariable [QGVAR(weatherGrainRainThreshold), 0.2];
if !(_rainThreshold isEqualType 0) then { _rainThreshold = 0.2; };

private _params = [_rain, _sunOrMoon] call FUNC(weatherGrainParams);
private _intensity = ((_params select 0) * _intensitySetting) * _grainScale;
private _sharpness = _params select 1;
private _size = _params select 2;

private _on = _rain > _rainThreshold;
private _off = _rain < (_rainThreshold * 0.5);

if (_on) then {
    if (_hGrain >= 0) then {
        if (!_active) then {
            _hGrain ppEffectEnable true;
            missionNamespace setVariable [QGVAR(weatherGrainActive), true];
        };
        // The last three elements stay 1, 1, 1: the colour invariant holds.
        _hGrain ppEffectAdjust [_intensity, _sharpness, _size, 1, 1, 1];
        _hGrain ppEffectCommit 1;
    };
} else {
    if (_hGrain >= 0) then {
        if (_active && _off) then {
            _hGrain ppEffectEnable false;
            missionNamespace setVariable [QGVAR(weatherGrainActive), false];
        };
    };
};
