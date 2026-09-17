#include "..\script_component.hpp"
/*
Measure the local player's G-load from velocity deltas (issue #135).

Arma exposes no G-force command, so the load is derived the standard
scripted way: sample the unit's world velocity each tick, form the
acceleration vector from the change, and resolve it along the unit's
up vector (the Gz axis — the headward load a pilot actually feels).
A stationary/normal-1G baseline is the reference: 1 G is the standing
load, so the reported value is total Gz = |a·up| / g, which reads ~1.0
on the ground, >1 under pull-up, <1 in push-over.

The state (previous velocity + timestamp) lives on the unit, so the
measurement survives across the 1 Hz tick without a global.

Input:  [_unit] - the unit to measure
Output: [gLoad, gzDelta] - total Gz magnitude (1 = normal) and the
        signed acceleration along +up in g (negative = push-over)
*/

params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith { [1, 0] };

private _vel = velocity _unit;
private _now = diag_tickTime;
private _prev = _unit getVariable [QGVAR(gState), [_vel, _now, 0]];

_prev params ["_prevVel", "_prevTime", "_prevG"];
private _dt = _now - _prevTime;
if (_dt <= 0 || _dt > 2) exitWith { [1, 0] };  // first sample / gap: neutral

// Acceleration = dv/dt.  Resolve along the unit's up vector (Gz).
private _a = (_vel vectorDiff _prevVel) vectorMultiply (1 / _dt);
private _up = vectorUp _unit;          // Gz axis (headward)
private _aUp = _a vectorDotProduct _up;
private _g = _aUp / 9.81 + 1.0;  // +1 for the standing 1G baseline

// Smooth with the previous sample (1 Hz raw deltas are noisy).
private _gSmooth = 0.6 * _g + 0.4 * _prevG;
private _gMax = _gSmooth max 1.0;  // never report below 1G standing

_unit setVariable [QGVAR(gState), [_vel, _now, _gSmooth]];

[_gMax, _g]
