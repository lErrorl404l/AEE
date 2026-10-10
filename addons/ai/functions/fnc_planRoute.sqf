#include "..\script_component.hpp"

/*
Data-driven pathfinding driver (reusable AI substrate).

Runs at DECISION TIME, never per-frame (issue #81).  A caller - a mission or
another AI layer - asks for a route for a group through AEE's computed state.

The engine pathfinder finds A path; this driver finds THE right path.  The
engine's selectBestPlaces cannot take AEE's data: its expression variables are
engine-fixed, and there is no mud, fire or flood variable.  So this is the
two-step pattern the issue requires:

  1. selectBestPlaces generates terrain-flavoured candidates (hills, forest,
     houses) from the engine's own surface data.
  2. Each candidate is scored by FUNC(routeCost) from AEE's published hazard
     state and by FUNC(routeExposure) from the repo's visibility model.
  3. The best-scored candidate becomes the group's move waypoint, with the
     speed mode set from the repo's terrain speed factor (FM 5-430-00-1).

The route is planned on AEE data even where the units cannot see it - the
"seeing blind" behaviour.  No object is created and no unit is teleported: the
driver only adds one waypoint.

Gate: the AEE AI > Pathfinding setting, default off.  Off returns nil.

State read (each with a safe default; the repo's own producers):
  aee_mobility_routePassability      fnc_calculateRouteDegradation
  aee_persistence_flashFloodRisk     fnc_calculateFlashFloodRisk
  aee_core_currentFireRisk           fnc_calculateFireSpreadRisk
  aee_core_currentLightningRisk      fnc_calculateLightning
  aee_vision_viewDistanceTarget      fnc_calculateViewDistance (Koschmieder)

Publishes:
  aee_ai_routePlan   Array: the winning [position, score, speedFactor].

Arguments:
  0: Group  - the group to plan for
  1: Array  - the search centre, the objective or the threat, [x, y]
  2: Number - the search radius, metres (default 250)
  3: Number - the candidate count (default 8)

Returns:
  Array or nil - [position, score, speedFactor], or nil when the setting is
  off, the group is null, or no candidate was returned.
*/

params [
    ["_group", grpNull, [grpNull]],
    ["_center", [0, 0, 0], [[]]],
    ["_radius", 250, [0]],
    ["_count", 8, [0]]
];

if (!(missionNamespace getVariable [QGVAR(pathfinding), false])) exitWith { nil };
if (isNull _group) exitWith { nil };

// ── AEE state (the repo's own published values) ────────────────────────────
private _passability = [QEGVAR(mobility,routePassability), 1, 1] call EFUNC(lib,readState);
private _floodRisk   = [QEGVAR(persistence,flashFloodRisk), 0, 1] call EFUNC(lib,readState);
private _fireRisk    = [QEGVAR(core,currentFireRisk), 0, 1] call EFUNC(lib,readState);
private _lightning   = [QEGVAR(core,currentLightningRisk), 0, 1] call EFUNC(lib,readState);
private _viewRange   = [QEGVAR(vision,viewDistanceTarget), 0, 1] call EFUNC(lib,readState);

// ── Candidate generation (step 1) ──────────────────────────────────────────
// The expression weights terrain flavour for a flanking route: hills, forest,
// houses and meadow are preferred; sea is avoided.  Engine variables only;
// AEE data is applied in step 2.
private _expr = "((6*hills + 2*forest + 4*houses + 2*meadow) - sea + (2*trees))";
private _candidates = selectBestPlaces [_center, _radius, _expr, 100, _count];

private _bestPos = [];
private _bestScore = -1e30;
private _bestSpeed = 1;

{
    private _pos = _x select 0;
    private _base = _x select 1;
    if !(_base isEqualType 0) then { _base = 1; };

    private _exposure = [_pos distance2D _center, _viewRange] call FUNC(routeExposure);

    private _score = [_base, [
        ["passability", _passability],
        ["floodRisk", _floodRisk],
        ["fireRisk", _fireRisk],
        ["lightningRisk", _lightning],
        ["exposure", _exposure]
    ]] call FUNC(routeCost);

    if (_score > _bestScore) then {
        _bestScore = _score;
        _bestPos = _pos;
        _bestSpeed = [_pos] call EFUNC(mobility,getTerrainSpeedFactor);
    };
} forEach _candidates;

if (_bestPos isEqualTo []) exitWith { nil };

// ── Speed mode from the terrain speed factor (step 3) ──────────────────────
// The thresholds are a modelling choice, UNSOURCED.
private _speedMode = "LIMITED";
if (_bestSpeed >= 0.75) then { _speedMode = "FULL"; }
else { if (_bestSpeed >= 0.5) then { _speedMode = "NORMAL"; }; };

// ── Waypoint (step 4) ──────────────────────────────────────────────────────
private _wp = _group addWaypoint [_bestPos, 15, 150];
_wp setWaypointType "MOVE";
_wp setWaypointSpeed _speedMode;
_wp setWaypointBehaviour "AWARE";

private _plan = [_bestPos, _bestScore, _bestSpeed];
missionNamespace setVariable [QGVAR(routePlan), _plan];

_plan
