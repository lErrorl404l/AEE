#include "..\..\script_component.hpp"
/*
 * aee_core_fnc_getGeoAnchor
 *
 * Read the world geographic anchor once and publish it.  This is the single
 * reader of the raw CfgWorlds keys; the pure builder FUNC(buildGeoAnchor)
 * turns them into the stable 9-element schema:
 *   [latCentre, lonCentre, zone, mapSize, lonWest, latSouth, lonEast, latNorth, sourceToken]
 *
 * The world does not change during a mission, so the result is cached in
 * missionNamespace under QGVAR(geoAnchor) and also published as
 * aee_core_geoAnchor for every module to read.
 *
 * Return: the 9-element anchor.
 */
private _cached = missionNamespace getVariable [QGVAR(geoAnchor), []];
if (_cached isNotEqualTo []) exitWith { _cached };

private _cfg = configFile >> "CfgWorlds" >> worldName;
private _mapSize = getNumber (_cfg >> "mapSize");
private _mapZone = getNumber (_cfg >> "mapZone");
private _mapArea = getArray (_cfg >> "mapArea");
private _latitude = getNumber (_cfg >> "latitude");
private _longitude = getNumber (_cfg >> "longitude");

private _anchor = [_mapSize, _mapZone, _mapArea, _latitude, _longitude] call FUNC(buildGeoAnchor);

missionNamespace setVariable [QGVAR(geoAnchor), _anchor];
missionNamespace setVariable ["aee_core_geoAnchor", _anchor];

_anchor
