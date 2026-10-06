#include "..\..\script_component.hpp"
/*
 * aee_core_fnc_worldToMgrs
 *
 * Map a world position to MGRS through the anchor box.  PURE: it reads no
 * world, no config, no player and no engine grid.  The anchor from task 1
 * supplies the geographic box.
 *
 * The chain is:
 *   world [x, y, z] metres
 *     -> latitude, longitude on the anchor box (a local linear projection)
 *     -> UTM, FUNC(latLonToUtm)
 *     -> MGRS, FUNC(formatMgrs)
 *
 * The anchor box maps the world square [0, mapSize] x [0, mapSize] linearly
 * to the box, with the south-west corner at (0, 0).  When the anchor has no
 * usable box (sourceToken "cfgworlds") the function falls back to a local
 * tangent plane at the anchor centre, with the WGS84 meridian radius of
 * curvature giving metres per degree of latitude.
 *
 * Arguments:
 *   0: position  <ARRAY>  world position [x, y, z], metres
 *   1: anchor    <ARRAY>  the 9-element anchor from FUNC(getGeoAnchor)
 *   2: precision <NUMBER> MGRS total digits, one of 2, 4, 6, 8, 10
 *
 * Return: [mgrsString, latDeg, lonDeg, easting, northing, zone].  The MGRS
 * string is "" when the anchor is unusable.
 */
params [
    ["_position", [0, 0, 0], [[]]],
    ["_anchor", [], [[]]],
    ["_precision", 10, [0]]
];

if ((count _anchor) < 9) exitWith { ["", 0, 0, 0, 0, 0] };

private _latCentre = _anchor select 0;
private _lonCentre = _anchor select 1;
private _mapSize = _anchor select 3;
private _lonWest = _anchor select 4;
private _latSouth = _anchor select 5;
private _lonEast = _anchor select 6;
private _latNorth = _anchor select 7;

private _x = _position select 0;
private _y = _position select 1;

private _lat = 0;
private _lon = 0;
if ((_lonEast > _lonWest) && (_latNorth > _latSouth) && (_mapSize > 0)) then {
    // The anchor box is the geographic bounds of the world square.
    _lon = _lonWest + ((_x / _mapSize) * (_lonEast - _lonWest));
    _lat = _latSouth + ((_y / _mapSize) * (_latNorth - _latSouth));
} else {
    // No box: a local tangent plane at the anchor centre.  The world centre
    // (mapSize/2, mapSize/2) maps to the anchor centre, the same convention
    // as the box branch.  The WGS84 meridian radius of curvature
    // M = a(1-e2)/(1-e2 sin2)^1.5 is the source of metres per degree of
    // latitude; longitude scales by cos(latitude).
    private _a = 6378137;
    private _invF = 298.257223563;
    private _e2 = (1 / _invF) * (2 - (1 / _invF));
    private _sinLat = sin _latCentre;
    private _meridianRadius = _a * (1 - _e2) / ((1 - (_e2 * _sinLat * _sinLat)) ^ 1.5);
    private _metresPerDegLat = _meridianRadius * pi / 180;
    _lat = _latCentre + ((_y - (_mapSize / 2)) / _metresPerDegLat);
    _lon = _lonCentre + ((_x - (_mapSize / 2)) / (_metresPerDegLat * (cos _latCentre)));
};

private _utm = [_lat, _lon] call FUNC(latLonToUtm);
private _easting = _utm select 0;
private _northing = _utm select 1;
private _zone = _utm select 2;

private _mgrs = [_easting, _northing, _zone, _precision, _lat] call FUNC(formatMgrs);

[_mgrs, _lat, _lon, _easting, _northing, _zone]
