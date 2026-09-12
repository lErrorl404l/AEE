#include "..\script_component.hpp"

/*
Solar glare veiling effect — LightShafts + DynamicBlur when looking
toward the sun.

Reads QGVAR(solarGlareIntensity) (0–1) produced by fnc_calculateSolarGlare.
Gates on EGVAR(core,opticsEnabled).

Uses LightShafts ppEffect for god-ray streaks and a subtle DynamicBlur
to wash out contrast when looking near the sun.

Reference values (from research):
  • LightShafts default: [0.01, 0.6, 0.45, 0.89]
  • DynamicBlur for glare: 0.1–0.3 at peak
  • Low sun near horizon = stronger veiling glare
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _intensity = missionNamespace getVariable [QGVAR(solarGlareIntensity), 0];
private _player    = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

private _active = missionNamespace getVariable [QGVAR(glareFXActive), false];

if (_intensity > 0.02) then {
    if (!_active) then {
        "LightShafts"  ppEffectEnable true;
        "DynamicBlur"  ppEffectEnable true;
        missionNamespace setVariable [QGVAR(glareFXActive), true];
    };

    // LightShafts: intensity scales the god-ray brightness
    private _shaftBrightness = linearConversion [0, 1, _intensity, 0.01, 0.45, true];
    "LightShafts" ppEffectAdjust [0.01, 0.6, _shaftBrightness, 0.89];
    "LightShafts" ppEffectCommit 1;

    // DynamicBlur: subtle veiling wash at peak glare
    private _blurAmount = linearConversion [0, 1, _intensity, 0, 0.2, true];
    "DynamicBlur" ppEffectAdjust [_blurAmount];
    "DynamicBlur" ppEffectCommit 1;
} else {
    if (_active) then {
        "LightShafts" ppEffectAdjust [0.01, 0.6, 0, 0.89];
        "LightShafts" ppEffectCommit 0.5;
        "DynamicBlur" ppEffectAdjust [0];
        "DynamicBlur" ppEffectCommit 0.5;

        [{
            "LightShafts" ppEffectEnable false;
            "DynamicBlur" ppEffectEnable false;
        }, [], 1] call CBA_fnc_waitAndExecute;

        missionNamespace setVariable [QGVAR(glareFXActive), false];
    };
};
