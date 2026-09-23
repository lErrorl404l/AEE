#include "..\script_component.hpp"

/*
Vehicle rollover applier (issue #108).

Runs per frame and tips a vehicle whose sustained lateral acceleration
exceeds its rollover threshold.  The threshold physics lives in
fnc_calculateRolloverThreshold (pure, unit-tested); the SSF source lives
in fnc_calculateSSF.  This function is the thin applier.

Why addTorque: the engine has no "tilt" command.  setVectorUp does not
persist on a driven vehicle (the solver overwrites it), so the only sound
mechanism is a rotational impulse at the centre of mass.  addTorque applies
one; a single impulse is too small, so it is applied for as long as the
condition holds, which is the documented use.

The condition is SUSTAINED, not a single frame: a transient spike from a
kerb or a collision must not roll the vehicle.  A per-vehicle counter
increments while a_lat exceeds the threshold and resets when it does not,
so only a sustained corner tips it.  The counter uses the frame count, not
randomness, so it is deterministic.

Gate: enabled, a player is near enough to see it, the vehicle is on the
ground and moving.  Nothing is applied to a vehicle the local machine does
not own, because addTorque is local physics.

Arguments:
  0: vehicle (OBJECT)

Return Value: BOOL - true when a roll impulse was applied
Example: [cursorObject] call aee_mobility_fnc_applyRollover
Public: No
*/

params [["_vehicle", objNull, [objNull]]];

if (!GVAR(rolloverEnabled)) exitWith { false };
if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { false };
if (isNull _vehicle || {!alive _vehicle}) exitWith { false };
if (_vehicle isKindOf "Air") exitWith { false };

// Local physics only. addTorque changes the object on this machine, so the
// machine must own the vehicle or the impulse is fought by the network.
// `local` is the engine's ownership test for exactly this.
if (!local _vehicle) exitWith { false };

// On the ground and moving: a stationary or airborne vehicle does not roll
// from cornering.
private _vel = velocity _vehicle;
private _speed = vectorMagnitude _vel;
if (_speed < 3) exitWith { false };
if (((getPosATL _vehicle) select 2) > 2) exitWith { false };

// ─── Lateral acceleration a_lat = V * omega ─────────────────────────────
// omega is the yaw rate.  It is derived from the change in heading over
// the tick; the frame delta comes from diag_deltaTime so the value is a
// real acceleration, not a per-frame count.
private _heading = getDir _vehicle;
private _key = netId _vehicle;
private _state = missionNamespace getVariable [QGVAR(rolloverState), createHashMap];
private _prev = _state getOrDefault [_key, [-999, _heading, 0]];

private _dt = diag_deltaTime;
if (_dt <= 0) then { _dt = 0.05; };

private _dHeading = _heading - (_prev select 1);
// Wrap the heading difference to -180..180 so crossing north is small.
if (_dHeading > 180) then { _dHeading = _dHeading - 360; };
if (_dHeading < -180) then { _dHeading = _dHeading + 360; };
private _omega = (_dHeading * 0.0174532925) / _dt;   // rad/s

private _aLat = _speed * (abs _omega);               // m/s^2
private _aLatG = _aLat / 9.80665;                    // in g

// ─── Threshold ──────────────────────────────────────────────────────────
private _ssfArr = [_vehicle] call FUNC(calculateSSF);
private _ssf = _ssfArr select 0;

// Ground slope across the track: use the vehicle's roll (bank) angle.  A
// banked surface lowers the threshold, which fnc_calculateRolloverThreshold
// applies.
private _up = vectorUp _vehicle;
private _bankDeg = acos ((_up select 2) max -1 min 1) * 57.2957795;

private _thr = [_ssf, _bankDeg, GVAR(rolloverDynamicFactor)]
    call FUNC(calculateRolloverThreshold);
private _appliedG = _thr select 1;

// ─── Sustained condition ────────────────────────────────────────────────
private _held = _prev select 2;
private _rolled = false;
if (_appliedG > 0 && _aLatG > _appliedG) then {
    _held = _held + 1;
} else {
    _held = 0;
};

if (_held >= GVAR(rolloverHoldFrames)) then {
    // Roll about the longitudinal axis.  The vehicle's forward vector is
    // the axis; the torque sign follows the turn direction so the body
    // leans out of the corner, as a real rollover does.
    private _forward = _vehicle vectorModelToWorld [0, 1, 0];
    private _sign = if (_omega >= 0) then { -1 } else { 1 };
    private _axis = vectorNormalized _forward;
    private _magnitude = GVAR(rolloverTorqueScale) * (getMass _vehicle);
    private _torque = _axis vectorMultiply (_sign * _magnitude);
    _vehicle addTorque _torque;
    _rolled = true;
    _held = 0;   // one impulse per sustained event, not every frame
};

_state set [_key, [time, _heading, _held]];
missionNamespace setVariable [QGVAR(rolloverState), _state];

missionNamespace setVariable [QGVAR(currentRolloverG), _aLatG];
missionNamespace setVariable [QGVAR(currentRolloverThresholdG), _appliedG];

_rolled
