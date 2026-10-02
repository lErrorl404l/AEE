#include "..\..\script_component.hpp"
/*
 * Per-selection model-space points (issue #204).
 *
 * The heat sources must warm the part they physically touch, not the first
 * entry of the selection list.  That needs each selection's position, and
 * the position resolution is an engine call: selectionPosition walks the
 * model.  It must run once per class, not once per source per tick.
 *
 * This function is the one resolver.  It returns one model-space point per
 * selection name, in the same order, and caches the array per class and
 * selection set.  fnc_getThermalSelectionLag and the four local heat
 * sources all read this cache instead of calling selectionPosition again.
 *
 * Point resolution, strongest first:
 *   1. the Memory LOD point, the same selectionPosition [name, "Memory"]
 *      fnc_getVehicleGeometry reads for the wheel points,
 *   2. the default-LOD selectionPosition when the memory point is absent,
 *   3. the model origin [0, 0, 0], so a selection with no point is
 *      indistinguishable from the centre and never invents a location.
 *
 * Params:
 *   0: _veh (OBJECT)
 *   1: _selNames (ARRAY of STRING)
 *
 * Returns: ARRAY of ARRAY - one [x, y, z] model-space point per name, in
 *   the same order as _selNames.
 */
params [["_veh", objNull, [objNull]], ["_selNames", [], [[]]]];

if (isNull _veh || {_selNames isEqualTo []}) exitWith { [] };

// Per-class cache: the model geometry is static for a class, so the point
// set is resolved once and read by every later caller.
private _cacheKey = format ["%1|%2", typeOf _veh, _selNames joinString ","];
private _cache = missionNamespace getVariable [QGVAR(thermalSelectionPointCache), -1];
if (_cache isEqualType 0) then {
    _cache = createHashMap;
    missionNamespace setVariable [QGVAR(thermalSelectionPointCache), _cache];
};
private _cached = _cache getOrDefault [_cacheKey, []];
if (count _cached > 0) exitWith { _cached };

private _points = [];
{
    private _pos = _veh selectionPosition [_x, "Memory"];
    if (!(_pos isEqualType []) || {count _pos != 3}) then { _pos = [0, 0, 0]; };
    if ((_pos isEqualTo [0, 0, 0]) && (_x != "")) then {
        _pos = _veh selectionPosition _x;
        if (!(_pos isEqualType []) || {count _pos != 3}) then { _pos = [0, 0, 0]; };
    };
    _points pushBack _pos;
} forEach _selNames;

_cache set [_cacheKey, _points];
_points
