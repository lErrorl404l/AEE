#include "..\script_component.hpp"

/*
Route cost kernel (reusable AI substrate).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

The "weight destinations" stage of the data-driven pathfinder.  The engine
selectBestPlaces returns terrain-flavoured candidates with an engine score;
this kernel folds AEE's OWN computed hazard state into that score, so the AI
routes on data it may not be able to see ("seeing blind").  The AI navigates
by the flood zone, the mud, the fire front and the lit open ground, not by
what its units can see.

The caller supplies a flat value map of [key, value] pairs, in any order and
with any subset of keys, exactly as fnc_perceptionSample does.  A HashMap is
deliberately not accepted: reading one needs an engine command the pure
boundary forbids.  Recognised keys, each a 0..1 value published by the named
producer (the repo's own state):

  key            producer                             meaning
  passability    aee_mobility_routePassability         route condition, 1 = firm
  floodRisk      aee_persistence_flashFloodRisk        flash-flood index
  fireRisk       aee_core_currentFireRisk              fire danger index
  lightningRisk  aee_core_currentLightningRisk         lightning strike risk
  exposure       FUNC(routeExposure)                   observability, 1 = exposed

The score is the base scaled by a product of independent survival factors, so
one severe hazard dominates and no hazard is cancelled by a bonus:

  score = base * passability * (1 - floodRisk) * (1 - fireRisk)
                * (1 - lightningRisk) * (1 - exposure)

Every hazard factor is clamped to 0..1.  A missing or malformed key
contributes 1, so a partial map is safe.  The PRODUCT combination treats the
hazards as independent and a route as usable only when every one is
survivable; it is a modelling choice, UNSOURCED.  The inputs are the repo's
own state and the base is the caller's terrain score.

Arguments:
  0: Number - the terrain base score (default 1, trusted as supplied)
  1: Array  - the value map, an array of [key, value] pairs

Returns:
  Number - the route score.  Higher is more suitable.
*/

params [
    ["_base", 1, [0]],
    ["_map", [], [[]]]
];

if !(_base isEqualType 0) then { _base = 1; };

private _score = _base;

{
    if ((_x isEqualType []) && {((count _x) >= 2)}) then {
        private _key = _x select 0;
        private _value = _x select 1;

        if ((_key isEqualType "") && (_value isEqualType 0)) then {
            _value = ((_value max 0) min 1);

            if (_key == "passability") then {
                _score = _score * _value;
            };
            if ((_key == "floodRisk") || (_key == "fireRisk") || (_key == "lightningRisk") || (_key == "exposure")) then {
                _score = _score * (1 - _value);
            };
        };
    };
} forEach _map;

_score
