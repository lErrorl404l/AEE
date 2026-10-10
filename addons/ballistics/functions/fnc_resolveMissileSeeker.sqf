#include "..\script_component.hpp"

/*
Missile seeker tick (driver).

One tick of a missile seeker: it resolves the geometry, gates acquisition
with hysteresis, computes the proportional-navigation command, advances the
state machine, and publishes the result.  It is the single engine-touching
entry point for the seeker model; the physics lives in the pure kernels it
calls (calculateLosRate, calculateSeekerTrack, calculateProportionalNavigation,
calculateSeekerState), and the detection range is computed by the caller with
calculateIRSeekerRange or calculateRadarRange so this driver invents nothing.

Arguments:
  0: _missile (OBJECT) the missile
  1: _target  (OBJECT) the target
  2: _spec    (ARRAY)  seeker specification:
       0 detectRangeM    seeker detection range, m (from the IR or radar kernel)
       1 fovHalfDeg      half field of view, deg
       2 trackLimitRad   LOS-rate track limit, rad/s; <= 0 disables it
       3 navConstant     N' (3 to 5)
       4 maxAccel        PN command clamp, m/s2; <= 0 disables it
       5 boostTimeS      boost duration, s
       6 terminalRangeM  terminal phase entry range, m
       7 impactRangeM    impact range, m
  3: _dt      (NUMBER) time since the previous tick, s

Returns the published state array:
  [state, tracked, inFov, rangeM, losRateRad, commandMps2]
Public: No
*/

params [
    ["_missile", objNull, [objNull]],
    ["_target", objNull, [objNull]],
    ["_spec", [], [[]]],
    ["_dt", 0, [0]]
];

if (isNull _missile || {isNull _target}) exitWith { [] };
if ((count _spec) < 8) exitWith { [] };
if (_dt <= 0) exitWith { [] };

private _enabled = missionNamespace getVariable [QGVAR(missileSeekerEnabled), false];
if (!_enabled) exitWith { [] };

_spec params [
    ["_detectRangeM", 0, [0]],
    ["_fovHalfDeg", 30, [0]],
    ["_trackLimitRad", 0, [0]],
    ["_navConstant", 4, [0]],
    ["_maxAccel", 0, [0]],
    ["_boostTimeS", 0, [0]],
    ["_terminalRangeM", 0, [0]],
    ["_impactRangeM", 0, [0]]
];

private _missilePos = getPosASL _missile;
private _missileVel = velocity _missile;
private _targetPos = getPosASL _target;
private _targetVel = velocity _target;

private _los = _targetPos vectorDiff _missilePos;
private _rangeM = vectorMagnitude _los;
if (_rangeM <= 0) exitWith { [] };
private _losUnit = vectorNormalized _los;

// ─── Line-of-sight rate ────────────────────────────────────────────────────
// The previous LOS unit vector is stored on the missile so the rate is the
// change over the tick.  The first tick has no previous vector, so the rate
// is 0 and the previous vector is seeded here.
private _prevLos = _missile getVariable [QGVAR(seekerPrevLos), []];
private _losRate = 0;
if ((count _prevLos) >= 3) then {
    _losRate = [_prevLos, _losUnit, _dt] call FUNC(calculateLosRate);
};
_missile setVariable [QGVAR(seekerPrevLos), _losUnit];

// ─── Field of view ─────────────────────────────────────────────────────────
// The seeker looks along the missile velocity.  The target is in view when
// the angle between the nose direction and the LOS is inside the half-FOV.
private _inFov = false;
private _forward = vectorNormalized _missileVel;
if ((vectorMagnitude _forward) > 0) then {
    _inFov = (_forward vectorDotProduct _losUnit) >= (cos _fovHalfDeg);
};

// ─── Signal and acquisition gate ───────────────────────────────────────────
// The signal is the detection range over the actual range: at 1.0 the target
// sits on the detection edge, above 1.0 it is inside it.  The gate applies
// the issue's hysteresis (acquire at 1.0, hold at 0.5).
private _signal = 0;
if (_rangeM > 0) then { _signal = _detectRangeM / _rangeM; };

private _wasTracking = _missile getVariable [QGVAR(seekerTracked), false];
private _tracked = [
    _signal,
    1,
    _inFov,
    _losRate,
    _trackLimitRad,
    _wasTracking
] call FUNC(calculateSeekerTrack);
_missile setVariable [QGVAR(seekerTracked), _tracked];

// ─── Proportional navigation ───────────────────────────────────────────────
// Closing velocity is the LOS-axis component of the closing motion.
private _closingVelocity = _losUnit vectorDotProduct (_missileVel vectorDiff _targetVel);
private _command = 0;
if (_tracked) then {
    _command = [
        _navConstant,
        _closingVelocity,
        _losRate,
        _maxAccel
    ] call FUNC(calculateProportionalNavigation);
};

// ─── State machine ─────────────────────────────────────────────────────────
private _state = _missile getVariable [QGVAR(seekerState), 0];
private _launchTime = _missile getVariable [QGVAR(seekerLaunchTime), -1];
if (_launchTime < 0) then {
    _launchTime = CBA_missionTime;
    _missile setVariable [QGVAR(seekerLaunchTime), _launchTime];
    // A round that is already in flight is launched; the PRE_LAUNCH state is
    // only for a round still on the rail.
    if (_state == 0) then { _state = 1; };
};
private _boostElapsedS = CBA_missionTime - _launchTime;

private _nextState = [
    _state,
    _rangeM,
    _tracked,
    _boostElapsedS,
    _boostTimeS,
    _terminalRangeM,
    _impactRangeM
] call FUNC(calculateSeekerState);
_missile setVariable [QGVAR(seekerState), _nextState];

// ─── Publish ───────────────────────────────────────────────────────────────
private _result = [_nextState, _tracked, _inFov, _rangeM, _losRate, _command];
missionNamespace setVariable [QGVAR(seekerState), _nextState];
missionNamespace setVariable [QGVAR(seekerTracked), _tracked];
missionNamespace setVariable [QGVAR(seekerRangeM), _rangeM];
missionNamespace setVariable [QGVAR(seekerLosRateRad), _losRate];
missionNamespace setVariable [QGVAR(seekerCommandMps2), _command];

_result
