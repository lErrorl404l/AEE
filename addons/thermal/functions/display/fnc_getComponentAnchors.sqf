#include "..\..\script_component.hpp"
/*
Component anchor registry (issue #128, ADR-001).

The engine exposes named selections and hit points as FIXED anchors (ADR-001).
This function turns those anchors into a per-class registry that maps a
COMPONENT ROLE (engine, wheel, turret, glass ...) to the model selections that
name that part, so per-component physics can drive the part by role instead of
re-deriving selection names at every consumer.

Two anchor sources, in order of authority:

  1. HIT POINTS (getAllHitPointsDamage).  The damage model GUARANTEES these
     exist on a vehicle (HitEngine, HitLFWheel, HitGlass1, HitTurret), and it
     returns the model selection each one damages.  This is the strongest
     anchor: the engine requires it for the damage model to work, so every
     mod's vehicle carries it.  The hit-point name classifies to a role
     (fnc_classifyComponentRole) and its selection is recorded under that role.
  2. MODEL SELECTION NAMES (selectionNames).  Some roles have no hit point
     (a wheel that is only cosmetic, a glass panel with no damage model).  The
     model's own selection names are classified the same way and added.

The result is cached per vehicle CLASS: the hit-point set and the model
selections are fixed for a class and cannot change at run time.

ENGINE CEILINGS (what this cannot reach; recorded so the next worker does not
retry them):

  - This is a RUNTIME registry.  It reads anchors the engine already exposes;
    it cannot add a selection to a model (a model edit is required for that).
  - A model with no hit points and no role-bearing selection names yields an
    empty registry.  The engine holds no other per-part anchor to fall back on.
  - selectionNames returns the FIRST LOD only; a part named solely in another
    LOD is not seen here (the same limit fnc_getThermalSelections documents).
  - The role vocabulary is a naming convention, not an engine enum.  An
    unrecognised part returns no role; no role is invented.

Params:
  0: _vehicle (OBJECT)

Returns: HASHMAP - component role (STRING) -> ARRAY of selection names (STRING).
  Empty for a null object or an object with no classified anchors.
*/

params [["_vehicle", objNull, [objNull]]];

private _anchors = createHashMap;
if (isNull _vehicle) exitWith { _anchors };

// Cache per class - the anchors are static for a class.
private _cacheKey = typeOf _vehicle;
private _cache = missionNamespace getVariable [QGVAR(componentAnchorCache), -1];
if (_cache isEqualType 0) then {
    _cache = createHashMap;
    missionNamespace setVariable [QGVAR(componentAnchorCache), _cache];
};
private _cached = _cache getOrDefault [_cacheKey, -1];
if !(_cached isEqualType 0) exitWith { _cached };

// ─── Source 1: the guaranteed hit-point anchors ──────────────────────────
// getAllHitPointsDamage returns [names[], selections[], damages[]] - three
// parallel arrays.  The names are LOWERCASE engine-standard identifiers.
private _hpData = getAllHitPointsDamage _vehicle;
if ((count _hpData) >= 2) then {
    private _hpNames = _hpData select 0;
    private _hpSels = _hpData select 1;
    private _hpCount = (count _hpNames) min (count _hpSels);
    for "_i" from 0 to (_hpCount - 1) do {
        private _role = (_hpNames select _i) call FUNC(classifyComponentRole);
        private _sel = _hpSels select _i;
        if ((_role != "") && (_sel != "")) then {
            private _list = _anchors getOrDefault [_role, []];
            _list pushBackUnique _sel;
            _anchors set [_role, _list];
        };
    };
};

// ─── Source 2: the model selection names ─────────────────────────────────
// Catches roles the damage model omits.  selectionNames is the first LOD.
{
    private _role = _x call FUNC(classifyComponentRole);
    if (_role != "") then {
        private _list = _anchors getOrDefault [_role, []];
        _list pushBackUnique _x;
        _anchors set [_role, _list];
    };
} forEach (selectionNames _vehicle);

_cache set [_cacheKey, _anchors];
_anchors
