#include "..\..\script_component.hpp"

/*
Solar glare veiling effect — LightShafts + DynamicBlur when looking
toward the sun.

Reads QGVAR(solarGlareIntensity) (0–1) produced by fnc_calculateSolarGlare.
Gates on EGVAR(core,opticsEnabled).

Applies LightShafts ppEffect here (single owner) for god-ray streaks.
Stores the DynamicBlur intensity in QGVAR(glareBlur); the arbiter
(fnc_managePostProcess) applies it.

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

// DynamicBlur: subtle veiling wash at peak glare (arbiter applies it)
private _blurAmount = linearConversion [0, 1, _intensity, 0, (missionNamespace getVariable [QGVAR(glareBlurMax), 0.2]), true];
missionNamespace setVariable [QGVAR(glareBlur), [0, _blurAmount] select (_intensity > 0.02)];

if (_intensity > 0.02) then {
    if (!_active) then {
        "LightShafts" ppEffectEnable true;
        missionNamespace setVariable [QGVAR(glareFXActive), true];
    };

    // LightShafts: intensity scales the god-ray brightness.
    // LightShafts is an ADVANCED post-process effect (BIS wiki): it cannot
    // be created by ppEffectCreate (that returns -1), its adjustments are
    // immediate, and they do NOT require ppEffectCommit.  The string-LHS
    // form is correct here — the engine provisions the effect itself.
    // Unlike ChromAberration/DynamicBlur/ColorCorrections/FilmGrain, which
    // are handle-based in Arma 2.22, the advanced effects still accept the
    // string name.
    private _shaftBrightness = linearConversion [0, 1, _intensity, 0.01, 0.45, true] * (missionNamespace getVariable [QGVAR(solarGlareIntensity), 1.0]);
    "LightShafts" ppEffectAdjust [0.01, 0.6, _shaftBrightness, 0.89];
} else {
    if (_active) then {
        "LightShafts" ppEffectAdjust [0.01, 0.6, 0, 0.89];

        [{
            "LightShafts" ppEffectEnable false;
        }, [], 1] call CBA_fnc_waitAndExecute;

        missionNamespace setVariable [QGVAR(glareFXActive), false];
        missionNamespace setVariable [QGVAR(glareBlur), 0];
    };
};
