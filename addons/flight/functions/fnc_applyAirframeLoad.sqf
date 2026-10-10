#include "..\script_component.hpp"

/*
Apply the density and icing flight penalties to one locally-owned aircraft.

This is the flight consumer the AEE atmosphere lacked.  Two computed states
previously reached no airframe:

  - the lift ratio rho / AERO_ISA_SEA_LEVEL_DENSITY (aee_flight_currentLiftRatio), and
  - the FAR 25 Appendix C icing state (aee_atmos_airframeIcing and
    aee_atmos_iceAccretion_kg).

The pure kernel fnc_calculateAeroPenalty turns the two states into a bounded
lift loss and drag rise.  This function applies them:

  - lost lift as a downward addForce, weight * lift loss,
  - added drag as an addForce opposing the velocity,
  - ice mass as a setMass delta on the airframe, captured once and restored
    when the ice sheds.

MP SAFETY.  addForce and setMass change the object on the applying machine.
Only the owning machine may apply them, so the local test below is the gate.
The dedicated server never registers the caller's per-frame loop, and a
remote client never applies to another machine's airframe.

BOUNDS.  The kernel caps the lift loss and the drag rise, so the scripted
layer stays a perturbation and cannot stall the airframe.  The ice mass is
the atmos model's own bounded value.

Arguments:
  0: vehicle (OBJECT)

Return Value: BOOL - true when at least one penalty was applied
Example: [cursorObject] call aee_flight_fnc_applyAirframeLoad
Public: No
*/

params [["_vehicle", objNull, [objNull]]];

if (!GVAR(flightAeroPenalty)) exitWith { false };
if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { false };
if (isNull _vehicle || {!alive _vehicle}) exitWith { false };
if !(_vehicle isKindOf "Air") exitWith { false };
// A parachute is an Air object but has no aerofoil or engine to penalise.
if (_vehicle isKindOf "ParachuteBase") exitWith { false };

// Local physics only: addForce and setMass change the object here.
if (!local _vehicle) exitWith { false };

private _pos = getPosATL _vehicle;
if ((_pos select 2) < 1) exitWith { false };

private _vel = velocity _vehicle;
private _speed = vectorMagnitude _vel;
if (_speed < 5) exitWith { false };

private _mass = getMass _vehicle;
if (_mass <= 0) exitWith { false };

// ─── The two inputs ─────────────────────────────────────────────────────────
private _liftRatio = missionNamespace getVariable [QGVAR(currentLiftRatio), -1];
if !(_liftRatio isEqualType 0) then { _liftRatio = -1; };

private _density = missionNamespace getVariable [QEGVAR(core,currentAirDensity), AERO_ISA_SEA_LEVEL_DENSITY];
if !(_density isEqualType 0) then { _density = AERO_ISA_SEA_LEVEL_DENSITY; };

// Prefer the published lift ratio; fall back to the density directly when the
// lift kernel has not run this tick.
if (_liftRatio <= 0) then {
    _liftRatio = (_density max 0) / AERO_ISA_SEA_LEVEL_DENSITY;
};

private _ice = missionNamespace getVariable [QEGVAR(atmos,airframeIcing), 0];
if !(_ice isEqualType 0) then { _ice = 0; };

private _penalty = [_liftRatio, _ice] call FUNC(calculateAeroPenalty);
private _liftLoss = _penalty select 0;
private _dragRise = _penalty select 1;

// ─── Lost lift, downward ────────────────────────────────────────────────────
// Weight times the lift-loss fraction.  The kernel caps the fraction, so the
// force is a bounded deficit and never the whole weight.
if (_liftLoss > 0) then {
    _vehicle addForce [[0, 0, -(_mass * STANDARD_GRAVITY * _liftLoss)], [0, 0, 0]];
};

// ─── Added drag, opposing the velocity ──────────────────────────────────────
// The added drag is the drag-rise fraction times the dynamic pressure area,
// with the declared effective drag area Cd*S.  The speed gate above keeps the
// term bounded.
if (_dragRise > 0 && _speed > 0) then {
    private _extraDragN = _dragRise * 0.5 * (_density max 0) * AERO_DRAG_AREA_M2 * _speed * _speed;
    private _dir = vectorNormalized _vel;
    _vehicle addForce [_dir vectorMultiply (-_extraDragN), [0, 0, 0]];
};

// ─── Ice mass, setMass delta ────────────────────────────────────────────────
// The atmos model publishes one bounded ice mass.  It is applied to every
// local airframe in range, an approximation documented in ADR-017.
private _iceKg = missionNamespace getVariable [QEGVAR(atmos,iceAccretion_kg), 0];
if !(_iceKg isEqualType 0) then { _iceKg = 0; };
_iceKg = _iceKg max 0;

private _base = _vehicle getVariable [QGVAR(airBaseMassKg), -1];
if !(_base isEqualType 0) then { _base = -1; };
if (_base < 0) then {
    // First tick: the engine mass is the calibrated base, before any delta.
    _base = _mass;
    _vehicle setVariable [QGVAR(airBaseMassKg), _base];
};

private _target = _base + _iceKg;
if ((abs ((getMass _vehicle) - _target)) > 0.01) then {
    _vehicle setMass _target;
};

// ─── Publish for the diagnostic channel and any HUD consumer ────────────────
GVAR(airLiftLoss) = _liftLoss;
GVAR(airDragRise) = _dragRise;
GVAR(airIceMassKg) = _iceKg;
GVAR(airLiftRatioApplied) = _liftRatio;

_liftLoss > 0 || _dragRise > 0 || _iceKg > 0
