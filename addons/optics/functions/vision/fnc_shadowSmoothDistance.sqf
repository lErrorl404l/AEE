#include "..\..\script_component.hpp"

/*
Shadow distance smoothing (aee-workshop-copy item 6, part 2).

Re-derived from fn_smoothdistance.sqf in Adaptive Shadows (Workshop
3792830104).  The mod publishes no licence, so this is a re-derived numeric
kernel, not copied code.  No mod content is copied.  The default rates
(increase 2000 m/s, decrease 1000 m/s) and the fast-decrease factor 1.35 are
UNSOURCED heuristics.

The kernel is pure: no missionNamespace, no GVAR or EGVAR, no engine command.
The driver reads the current shadow distance and passes it in.

Arguments:
  0: Number  - target depth in metres
  1: Number  - current depth in metres
  2: Number  - delta time in seconds
  3: Number  - increase rate in metres per second
  4: Number  - decrease rate in metres per second
  5: Boolean - fast decrease, multiplies the decrease rate by 1.35

Returns:
  Number - the stepped depth in metres
*/

params [
    ["_target", 0, [0]],
    ["_current", 0, [0]],
    ["_deltaTime", 0.1, [0]],
    ["_increaseSpeed", 2000, [0]],
    ["_decreaseSpeed", 1000, [0]],
    ["_fastDecrease", false, [true]]
];

private _difference = _target - _current;
if (abs _difference <= 0.01) exitWith {_target};

private _speed = _increaseSpeed max 0;
if (_difference < 0) then {
    _speed = _decreaseSpeed max 0;
    if (_fastDecrease) then {
        _speed = _speed * 1.35;
    };
};

private _step = _speed * ((_deltaTime max 0.001) min 0.5);

if (_difference > 0) then {
    _current + (_step min _difference)
} else {
    _current - (_step min (abs _difference))
}
