#include "script_component.hpp"

AEE_MODULE_POST_INIT

if (is3DEN) exitWith {};

// ─── Penetration gate (issue #126) ────────────────────────────────────────
// The HandleDamage gate: scale vehicle damage by the round's real RHA
// penetration vs the STANAG protection class.  The global listener
// fires for every damage event; fnc_penetrationGate returns the
// original value for non-projectile/non-vehicle damage (no effect).
// ACE3 rule: the gate returns _oldDamage when stopped (never re-inflates
// _damage), so ACE3's delta stays at zero.
//
// The handler is installed on BOTH "LandVehicle" and "Man" (issue #251).
// installObjectEngineHandler matches by isKindOf, and a Man is not a kind
// of LandVehicle, so installing on LandVehicle alone left the soldier
// branch of fnc_penetrationGate (issue #119) dead: the inner
// `isKindOf "Man"` test was never reached.  Both installs share one code
// block and one gate body.
private _penetrationHandler = {
    params ["_unit", "_selection", "_damage", "_source", "_projectile",
            "_hitIndex", "_instigator", "_hitPoint"];
    // Land vehicles and infantry only; cheap gate for everything else.
    if !(_unit isKindOf "LandVehicle" || {_unit isKindOf "Man"}) exitWith { _damage };
    // The module's own switch, so a mission can disable the whole armour
    // model without unloading the addon.
    if !(missionNamespace getVariable [QGVAR(armourEnabled), true]) exitWith { _damage };
    if !(missionNamespace getVariable [QGVAR(penetrationGate), true]) exitWith { _damage };
    [_unit, _selection, _damage, _source, _projectile, _hitIndex,
     _instigator, _hitPoint] call FUNC(penetrationGate);
};

["LandVehicle", "HandleDamage", _penetrationHandler, QGVAR(penetrationGateHandler)]
    call EFUNC(lib,installObjectEngineHandler);
["Man", "HandleDamage", _penetrationHandler, QGVAR(penetrationGateManHandler)]
    call EFUNC(lib,installObjectEngineHandler);

// ─── Shot response (issue #161) ──────────────────────────────────────────
// On a direct, penetrating, vital hit: setUnconscious at once and bias the
// fall with the round's momentum.  The entity HitPart event runs on the
// shooter's PC; its argument is a nested array of hit records.
["CAManBase", "HitPart", {
    if !(missionNamespace getVariable [QGVAR(shotResponse), true]) exitWith {};
    if (isNil "_this" || {!(_this isEqualType [])} || {(count _this) == 0}) exitWith {};
    private _hit = _this;
    if ((_this select 0) isEqualType []) then { _hit = _this select 0; };
    if !(_hit isEqualType []) exitWith {};
    _hit call FUNC(applyShotResponse);
}, QGVAR(shotResponse)] call EFUNC(lib,installObjectEngineHandler);

// Uniform per-module state dump (plan T3): one state line per second.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;

