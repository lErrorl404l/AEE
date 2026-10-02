#include "..\script_component.hpp"
/*
Apply the wet/ice grip loss to a moving vehicle at run time (W2).

The engine exposes no command that changes tyre or track friction at run
time. A script must emulate a grip loss by adding a force. The available
tractive force is the friction coefficient times the normal force. A loss
of friction d_mu removes d_mu times m times g of force. That lost force is
applied opposite the velocity, so the engine decelerates as it would on
the slipperier surface.

The friction coefficient is the sourced wet/ice continuum in
fnc_calculateWetTraction. The dry reference is the same model's dry value.
Standard gravity is 9.80665 m/s2 (ISO 80000-3, CODATA).

addForce clears the applied force after each simulation step. The caller
must call this function every frame while the condition holds.

Arguments:
  0: vehicle (OBJECT)

Return Value: BOOL - true when a grip-loss force was applied
Example: [cursorObject] call aee_mobility_fnc_applyGripLoss
Public: No
*/

params [["_vehicle", objNull, [objNull]]];

GVAR(gripLossForceN) = 0;

if !(GVAR(vehicleCouplingEnabled)) exitWith { false };
if !(missionNamespace getVariable [QEGVAR(core,enabled), true]) exitWith { false };
if (isNull _vehicle) exitWith { false };
if (!alive _vehicle) exitWith { false };
// A ground vehicle only. This applies a force, so a person, a building or
// any other non-vehicle must never reach it. LandVehicle excludes the men
// (CAManBase), aircraft and ships the old Air test left partly open.
if !(_vehicle isKindOf "LandVehicle") exitWith { false };
if !(local _vehicle) exitWith { false };

// A dry, firm surface loses no grip. This cheap gate keeps the per-frame
// cost near zero in the common case.
private _wetness = missionNamespace getVariable [QEGVAR(core,surfaceWetness), 0];
if !(_wetness isEqualType 0) then { _wetness = 0; };
private _ground = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _slipperyGround = _ground in ["Snow", "Frozen", "Mud"];
if ((_wetness <= 0.05) && {!_slipperyGround}) exitWith { false };

private _vel = velocity _vehicle;
private _speed = vectorMagnitude _vel;
if (_speed < 1) exitWith { false };
if (((getPosATL _vehicle) select 2) > 2) exitWith { false };

private _mass = getMass _vehicle;
if (_mass <= 0) exitWith { false };

// The per-vehicle friction from the shared sourced model.
private _mu = [_vehicle, _mass, _speed, false] call FUNC(calculateWetTraction);
private _dryMu = GVAR(dryFrictionMu);
if !(_dryMu isEqualType 0) then { _dryMu = 0.8; };

private _deltaMu = (_dryMu - _mu) max 0;
GVAR(gripDeltaMu) = _deltaMu;

if (_deltaMu <= 0) exitWith { false };

// Coulomb friction: the lost tractive force is d_mu * m * g.
private _forceN = _deltaMu * _mass * 9.80665;
private _dir = vectorNormalized _vel;
_vehicle addForce [_dir vectorMultiply (-_forceN), [0, 0, 0]];

GVAR(gripLossForceN) = _forceN;
true
