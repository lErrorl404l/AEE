#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyMarkersRestore
 *
 * Reverses FUNC(symbologyMarkersApply) on map close.  Every converted mission
 * marker gets its recorded type and colour back with the local commands, and
 * every AEE unit marker is deleted locally.  Both caches are cleared.  The
 * engine indicator suppression is cleared too, because disableMapIndicators is
 * a persistent LOCAL effect, not scoped to the map display.
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

private _echelon = missionNamespace getVariable [QGVAR(symbologyUnitEchelonMarkers), []];
{
    deleteMarkerLocal _x;
} forEach _echelon;
missionNamespace setVariable [QGVAR(symbologyUnitEchelonMarkers), []];

// disableMapIndicators is a persistent LOCAL effect, not scoped to the map
// display, so the suppression FUNC(symbologyMarkersApply) set on map open
// must be reversed here or the engine indicators stay hidden for the rest of
// the session.  A no-op when the setting was off and nothing was suppressed.
disableMapIndicators [false, false, false, false];

// The last-known contact state is scoped to the open map: a unit that dies
// while the map is closed is not tracked, so the record starts empty on the
// next open.
missionNamespace setVariable [QGVAR(symbologyKilledUnits), []];
