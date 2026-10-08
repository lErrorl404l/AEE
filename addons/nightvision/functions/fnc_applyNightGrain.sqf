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

The handle lives in the shared core registry under the "nightvision" scope,
key "FilmGrain".  It is created on the first normal-vision tick and released
when a sensor view takes over or the optics module is disabled.  Before the
registry the variable was read here and written nowhere, so the grain never
showed.
*/

// Read the handle before every guard so each exit can release it.  A sensor
// view, a death or a disabled module must not leave the grain live.
private _hGrain = missionNamespace getVariable [QGVAR(ppHandle_FilmGrain), -1];

if (!(missionNamespace getVariable [QEGVAR(core,opticsEnabled), true])) exitWith {
    if (_hGrain >= 0) then {
        ["nightvision", "FilmGrain"] call EFUNC(core,destroyPPEffect);
    };
};

private _player = call CBA_fnc_currentUnit;
// Run in the player's own view: on foot (cameraOn == player) or in
// the player's vehicle (pilot/passenger/gunner - cameraOn is the
// vehicle).  Skip spectator/UAV-terminal/external cameras.
private _veh = vehicle _player;
private _offView = isNil "_player" || {!alive _player} || {cameraOn != _player && {cameraOn != _veh}};
if (_offView) exitWith {
    missionNamespace setVariable [QGVAR(nightGrainActive), false];
    if (_hGrain >= 0) then {
        _hGrain ppEffectEnable false;
    };
};

// NVG (vision mode 1) and thermal (2) replace the eye with a sensor that
// has its own noise floor.  Applying the eye-noise FilmGrain on top of a
// clean NVG/thermal image destroys the view — the real devices do not have
// this grain.  Fade, then release the handle: the sensor path owns the
// screen, so the eye grain must not survive into it.
// Vision modes verified in-game: 0 = normal, 1 = NVG, 2 = thermal.
private _visionMode = currentVisionMode _player;
if (_visionMode == 1 || _visionMode == 2) exitWith {
    if (_hGrain >= 0) then {
        if (missionNamespace getVariable [QGVAR(nightGrainActive), false]) then {
            _hGrain ppEffectAdjust [0.01, 0.1, 0.5, 0.1, 0.1, 1];
            _hGrain ppEffectCommit 1;
            private _fadeHandle = _hGrain;
            [{
                params ["_fadeHandle"];
                if ((missionNamespace getVariable [QGVAR(ppHandle_FilmGrain), -1]) == _fadeHandle) then {
                    ["nightvision", "FilmGrain"] call EFUNC(core,destroyPPEffect);
                };
            }, [_fadeHandle], 1.5] call CBA_fnc_waitAndExecute;
        } else {
            ["nightvision", "FilmGrain"] call EFUNC(core,destroyPPEffect);
        };
    };
    missionNamespace setVariable [QGVAR(nightGrainActive), false];
};

// Create the grain handle on first use.  The registry is idempotent, so a
// later call returns the live handle instead of stacking a second FilmGrain
// at the same priority.
//
// Priority 2001, not 2000.  The thermal vision stack creates its own FilmGrain
// at 2000 (fnc_applyThermalVision.sqf), and the engine can hand two creators
// that ask for one effect type at one priority a SINGLE shared handle.  At a
// shared handle either teardown destroys the other owner's grain.  The
// priorities must stay disjoint across every AEE creator.
if (_hGrain < 0) then {
    _hGrain = ["nightvision", "FilmGrain", "FilmGrain", 2001, QGVAR(ppHandle_FilmGrain)] call EFUNC(core,createPPEffect);
};
if (_hGrain < 0) exitWith {};

private _sunOrMoon = sunOrMoon;  // 0 = full night, 1 = full day
private _rain     = ([] call EFUNC(core,getSmoothedWeather)) select 0;
private _fog      = missionNamespace getVariable [QEGVAR(core,currentFogDensity), 0];

private _nightGrainMax = missionNamespace getVariable [QGVAR(nightGrainMax), 0.7];
private _rainGrainMax  = missionNamespace getVariable [QGVAR(rainGrainMax), 0.4];
private _fogGrainMax   = missionNamespace getVariable [QGVAR(fogGrainMax), 0.15];

// ─── Force-disable in clear daylight ────────────────────────────────────
// If time was skipped or conditions changed fast, the ppEffect can linger
// from a previous night tick.  Force it off immediately when sun is high.
private _active = missionNamespace getVariable [QGVAR(nightGrainActive), false];
if (_active && _sunOrMoon > 0.6 && _rain <= 0.2 && _fog <= 0.1) exitWith {
    if (_hGrain >= 0) then {
        _hGrain ppEffectAdjust [0.01, 0.1, 0.5, 0.1, 0.1, 1];
        _hGrain ppEffectCommit 0.5;
        private _offHandle = _hGrain;
        [{
            params ["_offHandle"];
            if (_offHandle >= 0) then {
                if ((missionNamespace getVariable [QGVAR(ppHandle_FilmGrain), -1]) == _offHandle) then {
                    _offHandle ppEffectEnable false;
                };
            };
        }, [_offHandle], 0.75] call CBA_fnc_waitAndExecute;
    };
    missionNamespace setVariable [QGVAR(nightGrainActive), false];
};

// ─── Calculate grain intensity (0 = clean, 1 = maximum noise) ───────────
// Night contributes up to the night maximum; rain contributes up to the
// rain maximum; fog adds a small amount of haze grain.
private _nightGrain = 0;
private _rainGrain  = 0;
private _fogGrain   = 0;

if (_sunOrMoon < 0.5) then {
    // Night: more grain as it gets darker
    _nightGrain = linearConversion [0.5, 0, _sunOrMoon, 0, _nightGrainMax, true];
    // Rain at night is much worse
    if (_rain > 0.4) then {
        _rainGrain = linearConversion [0.4, 1, _rain, 0, _rainGrainMax, true];
    };
} else {
    // Daytime: grain only from heavy rain or dense fog
    if (_rain > 0.2) then {
        _rainGrain = linearConversion [0.2, 1, _rain, 0, 0.25, true];
    };
};

// Fog contributes a uniform haze
if (_fog > 0.1) then {
    _fogGrain = linearConversion [0.1, 0.8, _fog, 0, _fogGrainMax, true];
};

private _totalGrain = (_nightGrain + _rainGrain + _fogGrain) min 1;

// ─── Apply FilmGrain ppEffect ───────────────────────────────────────────
// Parameters: [intensity, grainSize, pixelSize, grainIntensity2, grainIntensity3, inversion]
_active = missionNamespace getVariable [QGVAR(nightGrainActive), false];

if (_totalGrain > 0.01) then {
    if (!_active && _hGrain >= 0) then {
        _hGrain ppEffectEnable true;
        missionNamespace setVariable [QGVAR(nightGrainActive), true];
    };

    private _grainSize = linearConversion [0, 1, _totalGrain, 0.5, 3.5, true];
    private _intensity = linearConversion [0, 1, _totalGrain, 0.5, 0.7, true];

    if (_hGrain >= 0) then {
        _hGrain ppEffectAdjust [0.01, _intensity, _grainSize, 1, 1, 1];
        _hGrain ppEffectCommit 2;
    };
} else {
    if (_active) then {
        if (_hGrain >= 0) then {
            _hGrain ppEffectAdjust [0.01, 0.1, 0.5, 0.1, 0.1, 1];
            _hGrain ppEffectCommit 1;
            private _offHandle = _hGrain;
            [{
                params ["_offHandle"];
                if (_offHandle >= 0) then {
                    if ((missionNamespace getVariable [QGVAR(ppHandle_FilmGrain), -1]) == _offHandle) then {
                        _offHandle ppEffectEnable false;
                    };
                };
            }, [_offHandle], 1.5] call CBA_fnc_waitAndExecute;
        };

        missionNamespace setVariable [QGVAR(nightGrainActive), false];
    };
};
