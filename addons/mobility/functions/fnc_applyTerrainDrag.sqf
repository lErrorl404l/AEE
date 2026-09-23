#include "..\script_component.hpp"

/*
Apply the terrain speed factor to a driven vehicle (issue #117).

The engine has no deterministic way to cap a driven vehicle's speed.
Verified against the BI wiki:

  - limitSpeed and forceSpeed act on AI units only; neither caps a player's
    throttle.
  - setVelocity SETS the vector and fights the PhysX solver; called per
    frame on a driven vehicle it jitters, and because the solver runs on
    the driver's machine a server-side call desyncs.

So the penalty is applied as a DRAG FORCE opposing the velocity, integrated
by the solver.  It is computed and applied on the machine that owns the
vehicle's physics (the driver's machine), it never teleports the object,
and the factor it uses is a pure function of the surface and the shared
ground state, so every machine computes the same number.

The force is applied only ABOVE the surface's target speed: below it the
vehicle drives normally, so a slow vehicle is not dragged to a stop.  The
target speed is the vehicle's own maximum times the terrain factor.

Gate: enabled, the vehicle is local, on the ground, moving and driven.
The candidate list is cached by the caller, as the rollover loop does.

Arguments:
  0: vehicle (OBJECT)

Return Value: BOOL - true when a drag force was applied
Example: [cursorGet3D cursorObject] call aee_mobility_fnc_applyTerrainDrag
Public: No
*/

params [["_vehicle", objNull, [objNull]]];

if (!GVAR(terrainDragEnabled)) exitWith { false };
if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { false };
if (isNull _vehicle || {!alive _vehicle}) exitWith { false };
if (_vehicle isKindOf "Air") exitWith { false };

// Local physics only: addForce changes the object on this machine.
if (!local _vehicle) exitWith { false };

// On the ground, rolling, and with a driver: nothing to do otherwise.
private _vel = velocity _vehicle;
private _speed = vectorMagnitude _vel;
if (_speed < 2) exitWith { false };
if (((getPosATL _vehicle) select 2) > 2) exitWith { false };
if (isNull (driver _vehicle)) exitWith { false };

// ─── The surface factor and the target speed ────────────────────────────
private _factor = [getPosATL _vehicle] call FUNC(getTerrainSpeedFactor);

// The vehicle's own maximum, from config.  A vehicle with no maxSpeed key
// gets no cap rather than a guessed one.
private _maxKmh = getNumber (configOf _vehicle >> "maxSpeed");
if (_maxKmh <= 0) exitWith { false };

private _target = _maxKmh * _factor / 3.6;   // m/s
if (_target <= 0.5) exitWith { false };

// Below the target speed the vehicle drives freely.
if (_speed <= _target) exitWith { false };

// ─── The drag force ─────────────────────────────────────────────────────
// Overspeed above the target, as a fraction.  The force opposes the
// velocity direction and scales with the overspeed and the mass, so a
// heavy vehicle needs a larger force for the same deceleration (F = m a).
private _overspeed = (_speed - _target) / _target;             // 0..n
private _overspeedFrac = _overspeed min 1;
private _mass = getMass _vehicle;
private _forceMag = GVAR(terrainDragScale) * _mass * _overspeedFrac;
private _dir = vectorNormalized _vel;
private _force = _dir vectorMultiply (-_forceMag);

_vehicle addForce [_force, [0, 0, 0]];

// Publish the state for the diagnostic channel and any HUD consumer.
missionNamespace setVariable [QGVAR(currentTerrainSpeedFactor), _factor];
missionNamespace setVariable [QGVAR(currentTerrainTargetSpeed), _target];

true
