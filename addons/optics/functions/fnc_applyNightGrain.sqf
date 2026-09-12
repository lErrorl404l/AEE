#include "..\script_component.hpp"

/*
Night / low-light visual grain — FilmGrain post-process effect that
scales with lighting and weather conditions.

Pattern adapted from Real Lighting and Weather (fn_nightTime.sqf).
Uses ppEffectCreate with linearConversion for dynamic scaling.

Gate:    GVAR(enabled) && hasInterface
Reads:   sunOrMoon, rain, overcast, EGVAR(core,currentFogDensity)
Sets:    FilmGrain ppEffect (client-side only)

The grain simulates the eye's noise floor in low light and the
visual degradation from precipitation obscuring the view.
*/

if (!EGVAR(core,enabled)) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

private _sunOrMoon = sunOrMoon;  // 0 = full night, 1 = full day
private _rain     = rain;
private _fog      = missionNamespace getVariable [QEGVAR(core,currentFogDensity), 0];

// ─── Calculate grain intensity (0 = clean, 1 = maximum noise) ───────────
// Night contributes up to 0.7 grain; rain contributes up to 0.3;
// fog adds a small amount of haze grain.
private _nightGrain = 0;
private _rainGrain  = 0;
private _fogGrain   = 0;

if (_sunOrMoon < 0.5) then {
    // Night: more grain as it gets darker
    _nightGrain = linearConversion [0.5, 0, _sunOrMoon, 0, 0.7, true];
    // Rain at night is much worse
    if (_rain > 0.4) then {
        _rainGrain = linearConversion [0.4, 1, _rain, 0, 0.4, true];
    };
} else {
    // Daytime: grain only from heavy rain or dense fog
    if (_rain > 0.2) then {
        _rainGrain = linearConversion [0.2, 1, _rain, 0, 0.25, true];
    };
};

// Fog contributes a uniform haze
if (_fog > 0.1) then {
    _fogGrain = linearConversion [0.1, 0.8, _fog, 0, 0.15, true];
};

private _totalGrain = (_nightGrain + _rainGrain + _fogGrain) min 1;

// ─── Apply FilmGrain ppEffect ───────────────────────────────────────────
// Parameters: [intensity, grainSize, pixelSize, grainIntensity2, grainIntensity3, inversion]
private _active = missionNamespace getVariable [QGVAR(nightGrainActive), false];

if (_totalGrain > 0.01) then {
    if (!_active) then {
        "FilmGrain" ppEffectEnable true;
        missionNamespace setVariable [QGVAR(nightGrainActive), true];
    };

    private _grainSize = linearConversion [0, 1, _totalGrain, 0.5, 3.5, true];
    private _intensity = linearConversion [0, 1, _totalGrain, 0.5, 0.7, true];

    "FilmGrain" ppEffectAdjust [0.01, _intensity, _grainSize, 1, 1, true];
    "FilmGrain" ppEffectCommit 2;
} else {
    if (_active) then {
        "FilmGrain" ppEffectAdjust [0.01, 0.1, 0.5, 0.1, 0.1, true];
        "FilmGrain" ppEffectCommit 1;

        [{
            "FilmGrain" ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;

        missionNamespace setVariable [QGVAR(nightGrainActive), false];
    };
};
