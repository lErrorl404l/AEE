#include "..\..\script_component.hpp"

/*
Shadow FPS governor (aee-workshop-copy item 6, part 2).

Re-derived from the governor block in fn_run.sqf in Adaptive Shadows (Workshop
3792830104).  The mod publishes no licence, so this is a re-derived numeric
kernel, not copied code.  No mod content is copied.  The 800 per second
reduction, the 120 per second recovery, the deadband 3 and the smoothing time
0.5 are UNSOURCED heuristics.

The kernel is pure: it does NOT read diag_fps or getShadowDistance or
missionNamespace.  The driver samples the frame rate and passes it in.

Arguments:
  0: Number - smoothed frame rate from the previous tick
  1: Number - raw frame rate this tick
  2: Number - target frame rate; 0 turns the governor off
  3: Number - deadband in frames per second
  4: Number - current ceiling in metres
  5: Number - effective minimum in metres
  6: Number - effective maximum in metres
  7: Number - delta time in seconds
  8: Number - exponential smoothing time in seconds

Returns:
  [fpsSmooth, ceiling]
*/

params [
    ["_fpsSmooth", 60, [0]],
    ["_fpsRaw", 60, [0]],
    ["_targetFPS", 0, [0]],
    ["_deadband", 3, [0]],
    ["_ceiling", 500, [0]],
    ["_effectiveMin", 0, [0]],
    ["_effectiveMax", 500, [0]],
    ["_deltaTime", 0.1, [0]],
    ["_smoothingTime", 0.5, [0]]
];

private _alpha = 1 - exp (-((_deltaTime max 0.001) / (_smoothingTime max 0.05)));
private _smooth = _fpsSmooth + ((_fpsRaw - _fpsSmooth) * _alpha);
private _newCeiling = _ceiling;

if (_targetFPS > 0) then {
    if (_smooth < (_targetFPS - (_deadband max 0))) then {
        private _pressure = (((_targetFPS - _smooth) / _targetFPS) max 0) min 1;
        private _reduction = _pressure * 800 * _deltaTime;
        _newCeiling = (_newCeiling - _reduction) max _effectiveMin;
    } else {
        if (_smooth > (_targetFPS + (_deadband max 0))) then {
            _newCeiling = (_newCeiling + (120 * _deltaTime)) min _effectiveMax;
        };
    };
} else {
    _newCeiling = _effectiveMax;
};

[_smooth, _newCeiling]
