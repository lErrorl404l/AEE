#include "..\..\script_component.hpp"
/*
 * aee_core_fnc_parseMgrs
 *
 * Parse a full MGRS grid reference back to a UTM coordinate.  Pure and
 * argument-driven: it reads no world, no config and no player.  It reverses
 * FUNC(formatMgrs).  The lettering tables live in the generated data file
 * addons/core/data/mgrs_tables.sqf, loaded once into the mission variable
 * aee_core_mgrsTables at preInit.
 *
 * An MGRS string names a 100 km square and a digit group.  The northing of
 * that square repeats every 2,000,000 m, so the string alone is ambiguous.
 * The latitude band removes the ambiguity: this kernel tries each of the five
 * northing cycles and keeps the one whose latitude, from the inverse UTM
 * kernel FUNC(utmToLatLon), is nearest the band centre.
 *
 * The lettering is defined by:
 *   DMA TM 8358.1 (the lettering figures)
 *   DMA TM 8358.2 "The Universal Grids: UTM and UPS", Ed.1 1989
 *   NGA MGRS guidance (Modified February 2009)
 *
 * Arguments:
 *   0: mgrs <STRING> a full MGRS reference, for example "15SWC8081751205"
 *
 * Return: [easting, northing, zone, band] or [] when the string is malformed.
 */
params [
    ["_mgrs", "", [""]]
];

private _length = count _mgrs;
if (_length < 5) exitWith { [] };
private _digitCount = _length - 5;
if ((_digitCount < 0) || (_digitCount > 10)) exitWith { [] };
if (((_digitCount / 2) != floor (_digitCount / 2))) exitWith { [] };

private _tables = aee_core_mgrsTables;
private _bands = _tables select 0;
private _columnSets = _tables select 1;
private _rows = _tables select 2;
private _evenOffset = _tables select 3;
private _digitChars = _tables select 5;

// Decimal value of a digit string, or the index of a single character in an
// array of characters.  A character that is not in the array gives -1.
private _valueOf = {
    params ["_str", "_chars"];
    private _result = 0;
    private _char = "";
    private _hit = -1;
    for "_i" from 0 to ((count _str) - 1) do {
        _char = _str select [_i, 1];
        _hit = -1;
        for "_j" from 0 to ((count _chars) - 1) do {
            if (_char == (_chars select _j)) then { _hit = _j; };
        };
        _result = (_result * 10) + _hit;
    };
    _result
};

private _zone = [_mgrs select [0, 2], _digitChars] call _valueOf;
if ((_zone < 1) || (_zone > 60)) exitWith { [] };

private _band = _mgrs select [2, 1];
private _bandIndex = [_band, _bands] call _valueOf;
if ((_bandIndex < 0) || (_bandIndex > 19)) exitWith { [] };

private _perAxis = _digitCount / 2;
private _eastStr = (_mgrs select [5, _digitCount]) select [0, _perAxis];
private _northStr = (_mgrs select [5, _digitCount]) select [_perAxis, _perAxis];

private _columnSet = _columnSets select ((_zone - 1) mod 3);
private _columnIndex = [(_mgrs select [3, 1]), _columnSet] call _valueOf;
if ((_columnIndex < 0) || (_columnIndex > 7)) exitWith { [] };
private _e100k = _columnIndex + 1;

private _rowIndex = [(_mgrs select [4, 1]), _rows] call _valueOf;
if ((_rowIndex < 0) || (_rowIndex > 19)) exitWith { [] };
private _rowBase = _rowIndex;
if ((_zone mod 2) == 0) then {
    _rowBase = _rowIndex - _evenOffset;
    if (_rowBase < 0) then { _rowBase = _rowBase + 20; };
};

private _scale = 10 ^ (5 - _perAxis);
private _east = (_e100k * 100000) + (([_eastStr, _digitChars] call _valueOf) * _scale);
private _northLow = (_rowBase * 100000) + (([_northStr, _digitChars] call _valueOf) * _scale);

// Resolve the 2,000,000 m northing cycle with the latitude band.
private _latSouth = -80 + (_bandIndex * 8);
private _latNorth = _latSouth + 8;
if (_bandIndex == 19) then { _latNorth = 84; };
private _bandCentre = (_latSouth + _latNorth) / 2;
private _hemisphere = "north";
if (_bandIndex < 10) then { _hemisphere = "south"; };

private _bestNorthing = _northLow;
private _bestDistance = 1000;
private _candidate = 0;
private _latLon = [];
private _lat = 0;
private _distance = 0;
for "_k" from 0 to 4 do {
    _candidate = _northLow + (_k * 2000000);
    _latLon = [_east, _candidate, _zone, _hemisphere] call FUNC(utmToLatLon);
    _lat = _latLon select 0;
    _distance = abs (_lat - _bandCentre);
    if (_distance < _bestDistance) then {
        _bestDistance = _distance;
        _bestNorthing = _candidate;
    };
};

[_east, _bestNorthing, _zone, _band]
