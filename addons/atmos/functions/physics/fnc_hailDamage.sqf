#include "..\..\script_component.hpp"

/*
Hail damage on impact (#151 follow-on).

The particle pipeline renders the hail; this is the damage half.  It runs
on the machine that owns the unit, because a unit's damage is a
player-owned side effect: a dedicated server cannot damage a remote
client's unit without a network message.  Each client applies it to its own
unit, which the engine then replicates.

The energy it reads is deterministic - a function of the convective state,
which is a function of position, mission time and engine weather - so every
machine computes the same value and no variable is broadcast.

The energy-to-damage mapping is NOT a published injury law.  NWS publishes
no joules-to-injury threshold, so this function does not invent one.  It
maps the kinetic energy onto the engine's own damage scale the same way
fnc_handleCollisionDamage does: a light stone is a bruise, a large one is a
wound, and the engine decides what that means for the unit.  A unit under
hard cover takes nothing.

Damage scale (engine damage points, where 1.0 is a fatal wound):
    24 J (5 cm stone)    -> about 0.02, a bruise
   392 J (10 cm stone)   -> about 0.35, a wound that needs treatment
The linearConversion bounds are the computed energies of the NWS severe
stone (25.4 mm) and the largest modelled stone (101.6 mm); they are a model
mapping, not a clinical threshold, and the comment says so.

Arguments:
  0: unit (OBJECT) - the unit to damage

Return Value: NUMBER - the damage applied (0 when nothing applied)
Example: [player] call aee_atmos_fnc_hailDamage
Public: No
*/

params [["_unit", objNull, [objNull]]];

if (isNull _unit || {!alive _unit}) exitWith { 0 };
if (isDedicated) exitWith { 0 };

private _energyArr = missionNamespace getVariable [QEGVAR(core,hailEnergy), [0, 0, 0, 0]];
private _energy = 0;
if (_energyArr isEqualType [] && {count _energyArr >= 4}) then {
    _energy = _energyArr select 3;
};
if (_energy <= 0) exitWith { 0 };

// A unit under hard cover is protected.  The engine's own line-of-sight
// check is the honest test: a stone must reach the unit to hurt it, and
// this refuses to damage through a roof or a vehicle hull.
if (!isNull objectParent _unit) exitWith { 0 };

// Energy to the engine damage scale, bounds from the computed energies of
// the smallest and largest modelled stones (see the header).
private _damage = linearConversion [24, 392, _energy, 0.02, 0.35, true];

// Apply: ACE medical when present, otherwise the engine damage model.  The
// pattern is fnc_updateDiveState's.
if (isClass (configFile >> "CfgPatches" >> "ace_medical")) then {
    [_unit, _damage, "body", "Hail"] call ace_medical_fnc_addDamageToUnit;
} else {
    _unit setDamage ((getDammage _unit) + _damage) min 1;
};

AEE_LOG_INFO("hail damage applied")
