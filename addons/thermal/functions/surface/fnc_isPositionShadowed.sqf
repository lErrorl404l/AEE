#include "..\..\script_component.hpp"
/*
 * Thermal shadow detection (issue #204).
 *
 * Shadowed ground is COOLER than sunlit ground in real LWIR: the
 * direct solar loading is blocked, so a shadowed patch only receives
 * diffuse sky radiation and convection.  On a clear day this is a
 * several-degree depression - a building's shadow, a tree's shade, a
 * vehicle's cast shade all read visibly cooler in TI.
 *
 * The engine's shadow pass (setShadow / the renderer) does not expose
 * per-position shadow state to scripts, so the mod detects it by
 * RAYCAST: a line from the position toward the sun.  If any surface
 * (building, tree, vehicle) blocks the line, the position is in
 * shadow.  The sun's direction comes from the core solar model
 * (currentSunAzimuth/currentSunElevation).
 *
 * Cheap: the ray is a single lineIntersectsSurfaces call from ~1 m
 * above the ground toward the sun at a fixed range.  Cached per
 * position cell (5 m) so repeated queries in the same area share one
 * result for the frame.
 *
 * Params:
 *   0: _pos (ARRAY, PositionASL) - the ground position to test.
 *
 * Returns: BOOL - true if the position is in direct solar shadow.
 */
params [["_pos", [], [[]]]];
if (count _pos < 3) exitWith { false };

// No sun at night -> no solar shadow (the whole scene is uniformly
// shadowed; a shadow term only matters when there IS direct sun).
private _radiation = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), 0];
if !(_radiation isEqualType 0) then { _radiation = 0; };
if (_radiation <= 0.05) exitWith { false };

// Cache per 5 m cell for the frame.
private _cell = format [
    "%1_%2",
    round ((_pos select 0) / 5),
    round ((_pos select 1) / 5)
];
private _cache = missionNamespace getVariable [QGVAR(shadowCache), createHashMap];
private _frame = diag_frameNo;
private _entry = _cache getOrDefault [_cell, []];
if (count _entry == 2 && {(_entry select 0) == _frame}) exitWith {
    _entry select 1
};

// Sun direction from the core solar model.
private _azimuth = missionNamespace getVariable [QEGVAR(core,currentSunAzimuth), 180];
if !(_azimuth isEqualType 0) then { _azimuth = 180; };
private _elevation = missionNamespace getVariable [QEGVAR(core,currentSunElevation), 45];
if !(_elevation isEqualType 0) then { _elevation = 45; };
_elevation = _elevation max 1 min 89;

// Sun unit vector (azimuth east of north, elevation above horizon).
private _azR = _azimuth * (pi / 180);
private _elR = _elevation * (pi / 180);
private _sunDir = [
    (sin _azR) * (cos _elR),
    (cos _azR) * (cos _elR),
    sin _elR
];

// Ray from ~1 m above the position toward the sun, 200 m range (the
// horizon distance for a shadow-casting object of interest).
private _origin = [_pos select 0, _pos select 1, (_pos select 2) + 1];
private _end = _origin vectorAdd (_sunDir vectorMultiply 200);

// Any surface intersecting the ray = the position is in shadow.
private _hits = lineIntersectsSurfaces [
    _origin, _end,
    objNull, objNull,
    true, 1,    // sort nearest first, one result
    "GEOM", "NONE"
];
private _shadowed = count _hits > 0;
if (_shadowed && {count _hits > 0}) then {
    // Ignore the ground itself (the terrain at the origin): only a hit
    // WELL ABOVE the origin (a shadow-caster) counts.  A hit within
    // ~0.5 m is the ground plane being hit tangentially.
    private _first = _hits select 0;
    if (count _first >= 3 && {((_first select 0) distance _origin) < 1.0}) then {
        _shadowed = false;
    };
};

_cache set [_cell, [_frame, _shadowed]];
_shadowed
