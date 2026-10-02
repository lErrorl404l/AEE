#include "..\..\script_component.hpp"
/*
 * Per-selection thermal lag from the heat source (issue #204).
 *
 * The heat gradient across a vehicle is physical: the engine bay warms
 * first and a part further from the block lags.  The previous phase came
 * from the selection's POSITION IN THE LIST (_forEachIndex), which is the
 * model's declaration order, not a distance and not a physical quantity.
 *
 * This function measures the real model-space distance between each
 * selection and the vehicle's heat source, then normalises it against the
 * widest distance so the result is a 0..1 lag fraction:
 *
 *   lag = distance(selection, source) / max(distance over the selections)
 *
 * The normalisation divides by the largest distance present, so no
 * calibration constant is introduced.  The caller scales the fraction into
 * its delay, as before.
 *
 * SOURCE.  The heat source is the engine/propulsion point.  It is read
 * from the hit-point map fnc_getHitPointMaterials already builds: the
 * selection the damage model labels "engine" (HitEngine, HitMotor and
 * HitFuel all map there) sits over the block.  If the hit-point map gives
 * no engine selection, or its position does not resolve, the front axle is
 * used - the memory-LOD wheel points fnc_getVehicleGeometry already reads
 * (wheel_1_1_axis / wheel_2_1_axis are station 1, the front, where the
 * engine bay sits on the land vehicles this path covers).  If neither
 * resolves, the model centre is the source and every selection shares the
 * centre distance, so a selection with no usable point gets lag 0; no
 * spread is invented.
 *
 * PART POSITION.  selectionPosition [name, "Memory"] is the memory-LOD
 * point, the same call fnc_getVehicleGeometry uses for the wheel points.
 * A selection with no memory point falls back to the default-LOD
 * selectionPosition, then to the model centre.
 *
 * Params:
 *   0: _veh (OBJECT)
 *   1: _selNames (ARRAY of STRING)
 *
 * Returns: ARRAY of NUMBER - one lag fraction in 0..1 per selection, in
 *   the same order as _selNames.
 */
params [["_veh", objNull, [objNull]], ["_selNames", [], [[]]]];

if (isNull _veh || {_selNames isEqualTo []}) exitWith { [] };

// Per-class cache: the selection set and the model geometry are static for
// a class, so the lag array is computed once.  getThermalSelections already
// caches the set per class, so the key matches call for call.
private _cacheKey = format ["%1|%2", typeOf _veh, _selNames joinString ","];
private _cache = missionNamespace getVariable [QGVAR(thermalLagCache), -1];
if (_cache isEqualType 0) then {
    _cache = createHashMap;
    missionNamespace setVariable [QGVAR(thermalLagCache), _cache];
};
private _cached = _cache getOrDefault [_cacheKey, []];
if (count _cached > 0) exitWith { _cached };

// ─── The heat source: the engine / propulsion point ──────────────────────
private _source = [0, 0, 0];
private _hpMap = [_veh] call FUNC(getHitPointMaterials);
private _engineSel = "";
{
    if (_y == "engine") exitWith { _engineSel = _x; };
} forEach _hpMap;
if (_engineSel != "") then {
    private _ep = _veh selectionPosition [_engineSel, "Memory"];
    if ((_ep isEqualType []) && {count _ep == 3} && {_ep isNotEqualTo [0, 0, 0]}) then {
        _source = _ep;
    };
};
if (_source isEqualTo [0, 0, 0]) then {
    // Front axle, the memory-LOD wheel points the geometry reader uses.
    private _axles = [];
    {
        private _ap = _veh selectionPosition [_x, "Memory"];
        if ((_ap isEqualType []) && {count _ap == 3} && {_ap isNotEqualTo [0, 0, 0]}) then {
            _axles pushBack _ap;
        };
    } forEach ["wheel_1_1_axis", "wheel_2_1_axis"];
    if (_axles isNotEqualTo []) then {
        private _sum = [0, 0, 0];
        { _sum = _sum vectorAdd _x; } forEach _axles;
        _source = _sum vectorMultiply (1 / (count _axles));
    };
};

// ─── Per-selection distance, normalised to the widest ────────────────────
// The model points come from the shared per-class cache
// (fnc_getThermalSelectionPoints), so the model is walked once per class
// however many sources ask for a part position.
private _points = [_veh, _selNames] call FUNC(getThermalSelectionPoints);
private _distances = [];
private _maxDistance = 0;
{
    private _pos = _x;
    private _d = _pos distance _source;
    _distances pushBack _d;
    if (_d > _maxDistance) then { _maxDistance = _d; };
} forEach _points;

// A source that never resolved leaves every distance equal, so every lag is
// 0 - the parts stay uniform.  No spread is invented.
private _lags = [];
{
    _lags pushBack (if (_maxDistance > 0) then { (_x / _maxDistance) max 0 min 1 } else { 0 });
} forEach _distances;

_cache set [_cacheKey, _lags];
_lags
