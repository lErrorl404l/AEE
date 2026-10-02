#include "..\script_component.hpp"
/*
Apply the surface accretion load to a bound vehicle at run time (W2).

The engine exposes setMass at run time. Config mass is static, so the
accretion load is applied as a delta on the calibrated mass that the
config override already set. The base mass is captured once, before the
first delta, and restored when the load falls to zero.

Only a bound vehicle is coupled. A class the classifier cannot resolve
keeps its config mass. The load itself comes from the sourced layer model
in fnc_calculateAccretionMass.

The caller owns the machine that owns the vehicle. setMass takes a local
argument, and its effect is global, so the owning machine applies it once.

Arguments:
  0: vehicle (OBJECT)

Return Value: BOOL - true when the mass was read or written
Example: [cursorObject] call aee_mobility_fnc_applyAccretionMass
Public: No
*/

params [["_vehicle", objNull, [objNull]]];

if !(GVAR(vehicleCouplingEnabled)) exitWith { false };
if !(missionNamespace getVariable [QEGVAR(core,enabled), true]) exitWith { false };
if (isNull _vehicle) exitWith { false };
if (!alive _vehicle) exitWith { false };
// A land coupling only. Air and sea are not coupled, so the ground physics
// never reaches them. The accretion load is a land surface effect.
if !(_vehicle isKindOf "LandVehicle") exitWith { false };
if !(local _vehicle) exitWith { false };

// A bound vehicle only. The classifier resolves the class identity.
private _identity = [_vehicle] call FUNC(classifyVehicle);
if ((_identity select 8) == "none") exitWith { false };

// Capture the base mass once. The config override set the calibrated mass
// at load, so getMass here is the calibrated value, not a value source.
private _base = _vehicle getVariable [QGVAR(baseMassKg), -1];
if !(_base isEqualType 0) then { _base = -1; };
if (_base < 0) then {
    _base = getMass _vehicle;
    _vehicle setVariable [QGVAR(baseMassKg), _base];
};

private _snowDepth = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];
if !(_snowDepth isEqualType 0) then { _snowDepth = 0; };

private _delta = [_vehicle, _snowDepth] call FUNC(calculateAccretionMass);
private _target = _base + _delta;

if ((abs ((getMass _vehicle) - _target)) > 0.01) then {
    _vehicle setMass _target;
};

GVAR(accretionMassKg) = _delta;
GVAR(accretionBaseMassKg) = _base;

true
