#include "..\..\script_component.hpp"
#include "\z\aee\addons\lib\script_debug.hpp"
/*
 * Collect the separate objects in a thermal selection tree (issue #204).
 *
 * fnc_getThermalNestedObjects returns one object's DIRECT nested objects
 * (attachedObjects + getVehicleCargo), discovered per instance.  A nested
 * object must be painted as its OWN object, because setObjectTexture writes
 * only the target object's slots.  This function returns every object
 * reachable from a parent list, so the paint loop can run the same discovery
 * and paint on each.
 *
 * BOUNDED: _MAX_NESTED caps the returned objects.  A visited set keyed by str
 * object stops a cycle or a self-reference.  The per-object discovery behind
 * fnc_getThermalNestedObjects is itself depth- and object-capped and cached,
 * so a repeat call is a hashmap lookup, not a re-walk.
 *
 * Params:
 *   0: _parents (ARRAY of OBJECT) - the objects the paint loop already holds.
 *
 * Returns: ARRAY of OBJECT - the nested objects, the parents excluded.
 */
params [["_parents", [], [[]]]];

private _MAX_NESTED = 64;
// The module trace switch, resolved once for the collect rather than at the
// cap site inside the loop.
private _traceOn = AEE_TRACE_ON;

private _seen = [];
{
    _seen pushBackUnique (str _x);
} forEach _parents;

private _extra = [];
private _queue = +_parents;
while {(_queue isNotEqualTo []) && ((count _extra) < _MAX_NESTED)} do {
    private _parent = _queue deleteAt 0;
    {
        private _child = _x;
        private _key = str _child;
        if ((!isNull _child) && {!(_key in _seen)} && {(count _extra) < _MAX_NESTED}) then {
            _seen pushBack _key;
            _extra pushBack _child;
            _queue pushBack _child;
        };
    } forEach ([_parent] call FUNC(getThermalNestedObjects));
};

// A cap that drops content LOGS (logging is never a cost here), so a
// truncated tree is visible in the RPT instead of silent.
if ((count _extra) >= _MAX_NESTED) then {
    if (_traceOn) then {
        private _capMsg = format ["nested collect: cap %1 hit, further nested objects not painted", _MAX_NESTED];
        AEE_LOG_DEBUG(_capMsg);
    };
};

_extra
