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
["LandVehicle", "HandleDamage", {
    params ["_unit", "_selection", "_damage", "_source", "_projectile",
            "_hitIndex", "_instigator", "_hitPoint"];
    // Only land vehicles; cheap gate for everything else.
    if !(_unit isKindOf "LandVehicle") exitWith { _damage };
    // The module's own switch, so a mission can disable the whole armour
    // model without unloading the addon.
    if !(missionNamespace getVariable [QGVAR(armourEnabled), true]) exitWith { _damage };
    if !(missionNamespace getVariable [QGVAR(penetrationGate), true]) exitWith { _damage };
    [_unit, _selection, _damage, _source, _projectile, _hitIndex,
     _instigator, _hitPoint] call FUNC(penetrationGate);
}, QGVAR(penetrationGateHandler)] call EFUNC(core,installObjectEngineHandler);

// Uniform per-module state dump (plan T3): one state line per second.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;

