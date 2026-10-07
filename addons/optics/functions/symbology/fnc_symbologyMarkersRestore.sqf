#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyMarkersRestore
 *
 * Reverses FUNC(symbologyMarkersApply) on map close.  Every converted mission
 * marker gets its recorded type and colour back with the local commands, and
 * every AEE unit marker is deleted locally.  Both caches are cleared.
 *
 * Returns: nothing.
 */
private _cache = missionNamespace getVariable [QGVAR(symbologyMarkerCache), []];
{
    _x params ["_name", "_type", "_colour"];
    _name setMarkerTypeLocal _type;
    _name setMarkerColorLocal _colour;
} forEach _cache;
missionNamespace setVariable [QGVAR(symbologyMarkerCache), []];

private _created = missionNamespace getVariable [QGVAR(symbologyUnitMarkers), []];
{
    deleteMarkerLocal _x;
} forEach _created;
missionNamespace setVariable [QGVAR(symbologyUnitMarkers), []];
