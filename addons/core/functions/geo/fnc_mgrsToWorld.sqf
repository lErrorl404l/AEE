#include "..\..\script_component.hpp"
/*
 * aee_core_fnc_mgrsToWorld
 *
 * Map an MGRS reference back to a world position through the anchor box.
 * PURE: it reads no world, no config, no player and no engine grid.  It
 * reverses FUNC(worldToMgrs).
 *
 * The chain is:
 *   MGRS string
 *     -> [easting, northing, zone, band], FUNC(parseMgrs)
 *     -> latitude, longitude, FUNC(utmToLatLon)
 *     -> world [x, y, 0] metres on the anchor box
 *
 * The band letter gives the hemisphere (bands C to M are south, N to X are
 * north).  The anchor box is inverted by the same linear rule as
 * FUNC(worldToMgrs).  The returned z is 0: MGRS is a horizontal reference.
 *
 * Arguments:
 *   0: mgrs   <STRING> a full MGRS reference
 *   1: anchor <ARRAY>  the 9-element anchor from FUNC(getGeoAnchor)
 *
 * Return: [x, y, 0] in world metres, or [0, 0, 0] when the input is unusable.
 */
params [
    ["_mgrs", "", [""]],
    ["_anchor", [], [[]]]
];

if ((count _anchor) < 9) exitWith { [0, 0, 0] };

private _parsed = [_mgrs] call FUNC(parseMgrs);
if ((count _parsed) < 3) exitWith { [0, 0, 0] };

private _easting = _parsed select 0;
private _northing = _parsed select 1;
private _zone = _parsed select 2;
private _band = _parsed select 3;

// The band letter gives the hemisphere.  Bands are ordered south to north,
// so index 0 to 9 (C to M) is south and index 10 to 19 (N to X) is north.
private _bands = (aee_core_mgrsTables) select 0;
private _bandIndex = -1;
for "_i" from 0 to ((count _bands) - 1) do {
    if (_band == (_bands select _i)) then { _bandIndex = _i; };
};
if (_bandIndex < 0) exitWith { [0, 0, 0] };
private _hemisphere = "north";
if (_bandIndex < 10) then { _hemisphere = "south"; };

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
    _x = ((_lon - _lonWest) / (_lonEast - _lonWest)) * _mapSize;
    _y = ((_lat - _latSouth) / (_latNorth - _latSouth)) * _mapSize;
} else {
    // No box: invert the tangent plane at the anchor centre.  The world
    // centre maps back to the anchor centre, the same convention as the box
    // branch.
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
