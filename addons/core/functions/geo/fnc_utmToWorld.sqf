#include "..\..\script_component.hpp"
/*
 * aee_core_fnc_utmToWorld
 *
 * Map a UTM coordinate to a world position through the anchor box.  PURE:
 * it reads no world, no config, no player and no engine grid.  It is the
 * shared tail of FUNC(mgrsToWorld): the MGRS kernel parses its string and
 * derives the hemisphere, then calls this kernel for the projection and the
 * box inverse, so the two cannot drift.
 *
 * The chain is:
 *   easting, northing, zone, hemisphere
 *     -> latitude, longitude, FUNC(utmToLatLon)
 *     -> world [x, y, 0] metres on the anchor box
 *
 * The anchor box is inverted by the same linear rule as FUNC(worldToMgrs).
 * The returned z is 0: a grid reference is a horizontal position.
 *
 * Arguments:
 *   0: easting    <NUMBER> UTM easting, metres
 *   1: northing   <NUMBER> UTM northing, metres (southern carries +10000000)
 *   2: zone       <NUMBER> UTM zone number, 1..60
 *   3: hemisphere <STRING> "north" or "south"
 *   4: anchor     <ARRAY>  the 9-element anchor from FUNC(getGeoAnchor)
 *
 * Return: [x, y, 0] in world metres, or [0, 0, 0] when the anchor is unusable.
 */
params [
    ["_easting", 500000, [0]],
    ["_northing", 0, [0]],
    ["_zone", 31, [0]],
    ["_hemisphere", "north", [""]],
    ["_anchor", [], [[]]]
];

if ((count _anchor) < 9) exitWith { [0, 0, 0] };

private _latLon = [_easting, _northing, _zone, _hemisphere] call FUNC(utmToLatLon);
private _lat = _latLon select 0;
private _lon = _latLon select 1;

private _latCentre = _anchor select 0;
private _lonCentre = _anchor select 1;
private _mapSize = _anchor select 3;
private _lonWest = _anchor select 4;
private _latSouth = _anchor select 5;
private _lonEast = _anchor select 6;
private _latNorth = _anchor select 7;

private _x = 0;
private _y = 0;
if ((_lonEast > _lonWest) && (_latNorth > _latSouth) && (_mapSize > 0)) then {
    // The anchor box is the geographic bounds of the world square.
    _x = ((_lon - _lonWest) / (_lonEast - _lonWest)) * _mapSize;
    _y = ((_lat - _latSouth) / (_latNorth - _latSouth)) * _mapSize;
} else {
    // No box: invert the tangent plane at the anchor centre.  The world
    // centre maps back to the anchor centre, the same convention as the box
    // branch.  The WGS84 meridian radius of curvature
    // M = a(1-e2)/(1-e2 sin2)^1.5 gives metres per degree of latitude;
    // longitude scales by cos(latitude).
    private _a = 6378137;
    private _invF = 298.257223563;
    private _e2 = (1 / _invF) * (2 - (1 / _invF));
    private _sinLat = sin _latCentre;
    private _meridianRadius = _a * (1 - _e2) / ((1 - (_e2 * _sinLat * _sinLat)) ^ 1.5);
    private _metresPerDegLat = _meridianRadius * pi / 180;
    _y = ((_lat - _latCentre) * _metresPerDegLat) + (_mapSize / 2);
    _x = ((_lon - _lonCentre) * _metresPerDegLat * (cos _latCentre)) + (_mapSize / 2);
};

[_x, _y, 0]
