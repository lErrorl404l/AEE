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
  combined - weight sums (the worn slots, the carried weapons and
    magazines, and the container contents), armour = max, NIR = the
    surface-weighted average, clo = the sum
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith {
    private _e = [4.5, 0, 0.40, 0.75];
    [_e, _e, _e, _e, _e, [8.0, 0, 0.40, 0.75]]
};

// ─── CACHED (20 s, keyed on the loadout) ─────────────────────────────────
// MEASURED: this function costs 32 ms per call (performance counters,
// 2026-10-01).  It makes EIGHT loadout walks (five worn slots plus weapons,
// magazines and container contents), each weighing every carried item through
// the material library.  applyMovementSpeed calls it once per second in EVERY
// vision mode, so it was a 32 ms frame stall every single second, and
// applyClothingThermal calls it again at 10 Hz in thermal.  A soldier's kit
// changes only when they pick something up, so a 20 s cache removes the cost
// with no perceptible delay on a movement-speed coefficient.  The cache is
// ALSO keyed on the loadout, so a pickup is seen at once.
private _nowT = diag_tickTime;
private _cache = missionNamespace getVariable [QGVAR(equipCache), -1];
if (_cache isEqualType 0) then {
    _cache = createHashMap;
    missionNamespace setVariable [QGVAR(equipCache), _cache];
};
private _cacheKey = netId _unit;
// The cached signature is the unit's loadout. A time-to-live alone is not
// enough: a soldier who picks something up keeps the same netId, so a
// TTL-only hit would return the pre-pickup load and the movement coupling
// would not see the change. getUnitLoadout is one engine call, far cheaper
// than the eight walks the cache exists to avoid.
private _signature = getUnitLoadout _unit;
private _hit = _cache getOrDefault [_cacheKey, []];
if ((_hit isNotEqualTo [])
    && {(_nowT - (_hit select 0)) < 20}
    && {(_hit select 2) isEqualTo _signature}) exitWith {
    _hit select 1
};

private _uniform = [_unit] call FUNC(getUniformProperties);
private _vest = [_unit] call FUNC(getVestProperties);
private _helmet = [_unit] call FUNC(getHelmetProperties);
private _goggle = [_unit] call FUNC(getGoggleProperties);
private _pack = [_unit] call FUNC(getPackProperties);

// The combined signature: weight sums, armour = max (the vest
// dominates), NIR = the uniform-dominant surface-weighted average, clo
// sums.
private _slots = (_uniform select 0) + (_vest select 0) + (_helmet select 0)
    + (_goggle select 0) + (_pack select 0);
private _combined = [
    _slots,
    (_vest select 1) max (_helmet select 1) max (_goggle select 1),
    (_uniform select 2) + (_vest select 2) * 0.3 + (_helmet select 2) * 0.2
        + (_pack select 2) * 0.1 + (_goggle select 2) * 0.1,
    (_uniform select 3) + (_vest select 3) + (_helmet select 3)
        + (_goggle select 3) + (_pack select 3)
];
_combined set [2, (_combined select 2) / 1.7];

// The weapons the soldier carries join the load. They are not a slot, so
// they add after the slots are summed.
private _weapons = [_unit] call FUNC(getWeaponLoad);
_combined set [0, (_combined select 0) + _weapons];

// The magazines are the heaviest repeated item, so they join the load
// too. A magazine's mass is its empty mass plus the rounds it holds.
private _magazines = [_unit] call FUNC(getMagazineLoad);
_combined set [0, (_combined select 0) + _magazines];

// The container contents and the carried small kit (NVG, radio, GPS,
// medical kit, tools, weapon attachments) close the load.  The engine
// `load` command is not used: it returns 0..1 of the container capacity,
// a fraction and not a mass, so the contents are weighed item by item.
// The walk skips the worn slots, the carried weapons and the magazines,
// so nothing is counted twice.
private _inventory = [_unit] call FUNC(getInventoryLoad);
_combined set [0, (_combined select 0) + _inventory];

// The four resolvers and their sum: one line that explains a carried load,
// which is otherwise a single number with no way to see where it came from.
// The values are the ones already computed, not a second call.
private _logMsg = format [
    "load %1 kg = slots %2 + weapons %3 + magazines %4 + inventory %5",
    round ((_combined select 0) * 10) / 10, _slots, _weapons, _magazines, _inventory
];
AEE_LOG_DEBUG(_logMsg);

private _result = [_uniform, _vest, _helmet, _goggle, _pack, _combined];
_cache set [_cacheKey, [_nowT, _result, _signature]];
missionNamespace setVariable [QGVAR(equipCache), _cache];

_result
