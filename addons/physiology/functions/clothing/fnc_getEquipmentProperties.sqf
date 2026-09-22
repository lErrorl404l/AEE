#include "..\..\script_component.hpp"
/*
Comprehensive equipment library - the orchestrator (issue #119).

Returns the soldier's complete per-slot signature, matching the game's
slot structure exactly (uniform, vest, headgear, goggles, backpack).
Each slot classifies independently (fnc_getUniformProperties /
fnc_getVestProperties / fnc_getHelmetProperties / fnc_getGoggleProperties /
fnc_getPackProperties) and carries its own [weight kg, armor NIJ 0..3,
nirReflectance, clo].

Consumers read the slot they care about: a head hit faces the helmet's
armour, a torso hit faces the vest's (fnc_penetrationGate), the movement
coupling uses the combined weight + clo, gloves ride in the uniform.

The library is DYNAMIC: every item is classified by its classname's
FAMILY keywords (the codebase's dynamic pattern).  A mod we have never
seen resolves correctly as long as its classnames carry the family
signal.  The keyword tiers carry the researched values from
equipment-library.md (equipment + eyewear/facewear tables).

Arguments:
  0: unit (OBJECT, default player)

Returns [uniform, vest, helmet, goggle, pack, combined]:
  each slot entry is [weightKg, armorLevel, nirReflectance, cloTotal]
  combined - weight sums (incl. the pack contents), armour = max,
    NIR = the surface-weighted average, clo = the sum
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith {
    private _e = [4.5, 0, 0.40, 0.75];
    [_e, _e, _e, _e, _e, [8.0, 0, 0.40, 0.75]]
};

private _uniform = [_unit] call FUNC(getUniformProperties);
private _vest = [_unit] call FUNC(getVestProperties);
private _helmet = [_unit] call FUNC(getHelmetProperties);
private _goggle = [_unit] call FUNC(getGoggleProperties);
private _pack = [_unit] call FUNC(getPackProperties);

// The pack contents add their carried weight (the engine load command:
// 0..1 of the pack's max capacity).
private _packContents = load (unitBackpack _unit);

// The combined signature: weight sums, armour = max (the vest
// dominates), NIR = the uniform-dominant surface-weighted average, clo
// sums.
private _combined = [
    (_uniform select 0) + (_vest select 0) + (_helmet select 0)
        + (_goggle select 0) + (_pack select 0) + _packContents,
    (_vest select 1) max (_helmet select 1) max (_goggle select 1),
    (_uniform select 2) + (_vest select 2) * 0.3 + (_helmet select 2) * 0.2
        + (_pack select 2) * 0.1 + (_goggle select 2) * 0.1,
    (_uniform select 3) + (_vest select 3) + (_helmet select 3)
        + (_goggle select 3) + (_pack select 3)
];
_combined set [2, (_combined select 2) / 1.7];

// The weapons the soldier carries join the load. They are not a slot, so
// they add after the slots are summed. Magazines are a separate capture
// and are not counted yet (ADR-004).
_combined set [0, (_combined select 0) + ([_unit] call FUNC(getWeaponLoad))];

// The magazines are the heaviest repeated item, so they join the load
// too. A magazine's mass is its empty mass plus the rounds it holds.
_combined set [0, (_combined select 0) + ([_unit] call FUNC(getMagazineLoad))];

[_uniform, _vest, _helmet, _goggle, _pack, _combined]
