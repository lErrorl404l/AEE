#include "..\..\script_component.hpp"
/*
Per-selection solar exposure from the surface orientation (issue #204).

The old rule was binary: a wheel/undercarriage selection got exposure 0.15
and every other selection got 1.0.  A roof and a side panel therefore
received identical solar loading and the sun could not make a top warmer
than a side, or a day side warmer than a shade side.

This function derives a per-selection exposure from the model geometry.
The outward direction of a selection is a PROXY: it is the unit vector from
the object's bounding centre to the selection's model-space point (the
Memory LOD point when the model declares one, else the default-LOD
selection centre).  A memory point is a position, not a surface normal, so
this is a proxy for the true normal, not the normal itself.  A selection
whose point does not resolve keeps exposure 1.0 (the old value), so no
spread is invented for geometry the model does not carry.

Physics.  The core flux (EGVAR(core,currentSolarFlux)) is the HORIZONTAL
plane irradiance, G = G0 * sin(sun elevation), set by
fnc_calculateSolarRadiation.  A surface with unit normal n receives
cos(incidence) of the normal-incidence flux.  Relative to that horizontal
reference the fraction is

    exposure = cos(incidence) / sin(sun elevation)
             = dot(n, sunDir) / sin(sun elevation)

A horizontal roof keeps exposure 1.0, exactly the value the binary rule
gave it, and only tilted surfaces change.  The division is the derivation
of the horizontal reference, not a fitted constant.  The result is clamped
0..1 because the solver takes a fraction.  The wheel/undercarriage rule
stays as a FLOOR: those parts are mostly self-shadowed, so 0.15 is the
lower bound.

Cost.  The model geometry is static for a class, so the outward directions
are cached per class.  The sun direction is read and transformed once per
call.  No geometry scan runs per tick.

Arguments:
  0: object (OBJECT)
  1: selection names (ARRAY of STRING)

Return Value: ARRAY of NUMBER - one exposure in 0..1 per selection, in the
  same order as the input names.
*/

params [["_veh", objNull, [objNull]], ["_selNames", [], [[]]]];

if (isNull _veh || {_selNames isEqualTo []}) exitWith { [] };

// ─── Per-class outward direction ─────────────────────────────────────────
// The selection set and the model points are static for a class, so the
// direction array is computed once.  The key matches the per-class cache
// shape fnc_getThermalSelectionLag uses.
private _cacheKey = format ["%1|%2", typeOf _veh, _selNames joinString ","];
private _cache = missionNamespace getVariable [QGVAR(selSunDirCache), -1];
if (_cache isEqualType 0) then {
    _cache = createHashMap;
    missionNamespace setVariable [QGVAR(selSunDirCache), _cache];
};
private _dirs = _cache getOrDefault [_cacheKey, []];
if (count _dirs == 0) then {
    private _centre = boundingCenter _veh;
    if (!(_centre isEqualType []) || {count _centre != 3}) then { _centre = [0, 0, 0]; };
    _dirs = [];
    {
        private _pos = _veh selectionPosition [_x, "Memory"];
        if (!(_pos isEqualType []) || {count _pos != 3}) then { _pos = [0, 0, 0]; };
        if ((_pos isEqualTo [0, 0, 0]) && (_x != "")) then {
            _pos = _veh selectionPosition _x;
            if (!(_pos isEqualType []) || {count _pos != 3}) then { _pos = [0, 0, 0]; };
        };
        private _off = _pos vectorDiff _centre;
        private _mag = vectorMagnitude _off;
        // 1 mm degeneracy guard: a shorter offset is the centre itself, not
        // an outward direction, so the selection keeps no orientation.
        if (_mag > 1e-3) then {
            _dirs pushBack (_off vectorMultiply (1 / _mag));
        } else {
            _dirs pushBack [0, 0, 0];
        };
    } forEach _selNames;
    _cache set [_cacheKey, _dirs];
};

// ─── Sun direction in model space ────────────────────────────────────────
private _az = missionNamespace getVariable [QEGVAR(core,currentSunAzimuth), 0];
if !(_az isEqualType 0) then { _az = 0; };
private _elev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), 0];
if !(_elev isEqualType 0) then { _elev = 0; };
private _cosElev = cos _elev;
private _sinElev = sin _elev;
// World sun vector: X is east, Y is north, Z is up.  The azimuth is the
// bearing east of north, so the horizontal part is [sin az, cos az].
private _sunWorld = [
    (sin _az) * _cosElev,
    (cos _az) * _cosElev,
    _sinElev
];
// Model basis to world: vectorDir is model +Y, vectorUp is model +Z, and
// the cross product is model +X.  A dot product in this basis is
// frame-independent, so the object's facing enters here once per call.
private _fwd = vectorDir _veh;
private _up = vectorUp _veh;
private _side = _fwd vectorCrossProduct _up;
private _sunModel = [
    _sunWorld vectorDotProduct _side,
    _sunWorld vectorDotProduct _fwd,
    _sunWorld vectorDotProduct _up
];

// ─── Exposure per selection ──────────────────────────────────────────────
// A sun at or below the horizon carries no flux, so every selection keeps
// the neutral value.
private _neutral = _sinElev <= 0;
private _exposures = [];
{
    private _exp = 1;
    private _n = _dirs param [_forEachIndex, [0, 0, 0]];
    if (!_neutral && {_n isNotEqualTo [0, 0, 0]}) then {
        private _dot = _n vectorDotProduct _sunModel;
        _exp = if (_dot > 0) then { (_dot / _sinElev) min 1 } else { 0 };
    };
    // Wheel/undercarriage floor: tyres are mostly self-shadowed, so the old
    // low value stays as a lower bound.
    if ((_x find "wheel" >= 0) || {_x find "undercarriage" >= 0}) then {
        _exp = _exp max 0.15;
    };
    _exposures pushBack _exp;
} forEach _selNames;

_exposures
