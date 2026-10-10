#include "..\..\script_component.hpp"
/*
Ground vehicles near the local unit, resolved once per tick.

Two tick consumers want the same list: fnc_calculateRouteDegradation and
fnc_calculateMudAccretion. Both ran their own
`nearEntities [["Car","Tank","Motorcycle"], 200]`, at opposite ends of the
same tick, so the engine walked the same neighbourhood twice and each
consumer re-read `speed` and `getMass` for the same vehicles.

This function answers the query once and caches it for the tick. The
cache key is the tick time, so a second caller in the same tick reuses the
list and the next tick rebuilds it.

The values are PER-MACHINE by nature: `nearEntities` returns whatever is
near the local unit, so a client and the server legitimately disagree.
That is why the consumers keep their own state rather than publishing it
as shared truth.

Args:
  0: radius (NUMBER, metres, default 200)
  1: unit (OBJECT, default the current unit)

Returns an array of vehicle objects, possibly empty.
*/

params [["_radius", 200, [0]], ["_unit", objNull, [objNull, []]]];

if (_unit isEqualType []) then { _unit = objNull; };

// No unit means no neighbourhood. A dedicated server has none, and calling
// nearEntities on objNull is wasted work. The caller gets an empty list and
// its own state decays, which is the correct server-side behaviour.
if (isNull _unit) exitWith { [] };

// One list per tick. diag_tickTime is monotonic and shared within a
// machine, so the key changes exactly once per frame.
private _cache = missionNamespace getVariable [QGVAR(nearbyVehiclesCache), []];
private _now = diag_tickTime;
if (_cache isNotEqualTo [] && {(_cache select 1) isEqualTo _now}) exitWith {
    _cache select 0
};

private _vehicles = _unit nearEntities [["Car", "Tank", "Motorcycle"], _radius];

// Drop destroyed handles here rather than at each consumer.
_vehicles = _vehicles select { !isNull _x };

missionNamespace setVariable [QGVAR(nearbyVehiclesCache), [_vehicles, _now]];

_vehicles
