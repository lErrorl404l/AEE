#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_buildGeoAnchor
 *
 * Build the world geographic anchor from the RAW CfgWorlds values.
 * Pure: this function reads no config, no player and no world state.
 * The reader FUNC(getGeoAnchor) supplies the raw values.
 *
 * Arguments:
 *   0: mapSize   <NUMBER> world side length in metres
 *   1: mapZone   <NUMBER> UTM zone number from CfgWorlds
 *   2: mapArea   <ARRAY>  the raw mapArea[] value (four numbers, or [])
 *   3: latitude  <NUMBER> the raw CfgWorlds latitude key (BIS sign)
 *   4: longitude <NUMBER> the raw CfgWorlds longitude key (east positive)
 *
 * Return (9 elements):
 *   [latCentre, lonCentre, zone, mapSize, lonWest, latSouth, lonEast, latNorth, sourceToken]
 *
 * mapArea[] ELEMENT ORDER IS AUTHORITATIVE FROM BIS.  The shipped
 * Addons/functions_f/a3/functions_f/Map/fn_posDegtoWorld.sqf reads
 *   _UTMworldBottomLeft = [mapArea select 0, mapArea select 1]
 *   _UTMworldTopRight   = [mapArea select 2, mapArea select 3]
 * and passes each pair to bis_fnc_posDegToUTM, whose parameter 0 is
 * LONGITUDE and parameter 1 is LATITUDE.  Therefore
 *   mapArea = [lonBottomLeft, latBottomLeft, lonTopRight, latTopRight]
 *           = [lonWest, latSouth, lonEast, latNorth].
 * Verified against the shipped world configs on 2026-10-06.
 *
 * sourceToken is "mapArea" when the box is present and usable, else
 * "cfgworlds".  A box is usable when it holds four numbers that form a
 * positive-area rectangle inside valid geographic bounds.  The shipped
 * Tanoa mapArea[] = {-20.267975, 174.00284, -20.135265, 174.14566} reads,
 * in the authoritative order, a latitude of about 174 degrees - not a
 * latitude - so Tanoa falls back to the CfgWorlds keys.  Enoch ships an
 * empty mapArea[] = {} and also falls back.
 *
 * The CfgWorlds latitude key is INVERTED (BIS: positive is south), so the
 * fallback negates it.  A zero latitude falls back to 40 north, a zero
 * longitude to 0, and a missing zone to 0 - the same fallback the old
 * latitude reader used.
 */
params [
    ["_mapSize", 0, [0]],
    ["_mapZone", 0, [0]],
    ["_mapArea", [], [[]]],
    ["_latitude", 0, [0]],
    ["_longitude", 0, [0]]
];

if !(_mapSize isEqualType 0) then { _mapSize = 0; };
if !(_mapZone isEqualType 0) then { _mapZone = 0; };

// BIS stores the latitude sign inverted; this is the one sign correction.
private _latitudeTrue = -_latitude;
if !(_latitudeTrue isEqualType 0) then { _latitudeTrue = 40; };
if (_latitudeTrue == 0) then { _latitudeTrue = 40; };

private _longitudeVal = _longitude;
if !(_longitudeVal isEqualType 0) then { _longitudeVal = 0; };

private _lonWest = 0;
private _latSouth = 0;
private _lonEast = 0;
private _latNorth = 0;
private _useMapArea = false;

if (_mapArea isEqualType []) then {
    if (count _mapArea == 4) then {
        _lonWest = _mapArea select 0;
        _latSouth = _mapArea select 1;
        _lonEast = _mapArea select 2;
        _latNorth = _mapArea select 3;
        if (
            (_lonWest isEqualType 0) && (_latSouth isEqualType 0)
            && (_lonEast isEqualType 0) && (_latNorth isEqualType 0)
        ) then {
            if (
                (_lonWest < _lonEast) && (_latSouth < _latNorth)
                && (_lonWest >= -180) && (_lonEast <= 180)
                && (_latSouth >= -90) && (_latNorth <= 90)
            ) then {
                _useMapArea = true;
            };
        };
    };
};

private _latCentre = _latitudeTrue;
private _lonCentre = _longitudeVal;
private _sourceToken = "cfgworlds";

if (_useMapArea) then {
    _latCentre = (_latSouth + _latNorth) / 2;
    _lonCentre = (_lonWest + _lonEast) / 2;
    _sourceToken = "mapArea";
} else {
    // No usable box: the four box fields are not meaningful.
    _lonWest = 0;
    _latSouth = 0;
    _lonEast = 0;
    _latNorth = 0;
};

[_latCentre, _lonCentre, _mapZone, _mapSize, _lonWest, _latSouth, _lonEast, _latNorth, _sourceToken]
