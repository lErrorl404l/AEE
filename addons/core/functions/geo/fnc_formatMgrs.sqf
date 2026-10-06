#include "..\..\script_component.hpp"
/*
 * aee_core_fnc_formatMgrs
 *
 * Format a UTM coordinate as a full MGRS grid reference.  Pure and
 * argument-driven: it reads no world, no config and no player.  The lettering
 * tables live in the generated data file addons/core/data/mgrs_tables.sqf,
 * loaded once into the mission variable aee_core_mgrsTables at preInit.
 *
 * DESIGN DEVIATION, recorded in the task evidence.  The plan prose gives the
 * signature fnc_formatMgrs(easting, northing, zone, precision), but the Grid
 * Zone Designation band letter is a function of LATITUDE, which that
 * signature omits.  This kernel therefore takes the latitude as a fifth
 * argument and derives the band from it.  That is what makes the emitted
 * string a correct full MGRS reference (zone + band + 100 km square +
 * digits), instead of a 100 km square with no band.
 *
 * The lettering and the series are defined by:
 *   DMA TM 8358.2 "The Universal Grids: UTM and UPS", Ed.1 1989
 *   DMA TM 8358.1 (the lettering figures)
 *   NGA MGRS guidance (Modified February 2009)
 *
 * Arguments:
 *   0: easting   <NUMBER> UTM easting, metres
 *   1: northing  <NUMBER> UTM northing, metres (southern carries +10000000)
 *   2: zone      <NUMBER> UTM zone number, 1..60
 *   3: precision <NUMBER> total digits, one of 2, 4, 6, 8, 10
 *   4: latitude  <NUMBER> latitude, degrees, positive north (gives the band)
 *
 * Return: <STRING> the MGRS reference, or "" when an argument is out of range
 * or a letter would fall outside the table.  The digits are TRUNCATED, never
 * rounded, and they label the SOUTH-WEST corner of the square.
 */
params [
    ["_easting", 0, [0]],
    ["_northing", 0, [0]],
    ["_zone", 0, [0]],
    ["_precision", 0, [0]],
    ["_latitude", 0, [0]]
];

if ((_zone < 1) || (_zone > 60)) exitWith { "" };
if ((_precision < 2) || (_precision > 10)) exitWith { "" };
if (((_precision / 2) != floor (_precision / 2))) exitWith { "" };

private _tables = aee_core_mgrsTables;
private _bands = _tables select 0;
private _columnSets = _tables select 1;
private _rows = _tables select 2;
private _evenOffset = _tables select 3;
private _zoneStrings = _tables select 4;
private _digitChars = _tables select 5;

private _perAxis = _precision / 2;

// Latitude band.  Bands start at 80 S in 8 degree steps; band X is 12 high.
private _bandIndex = floor ((_latitude + 80) / 8);
_bandIndex = ((_bandIndex) max 0) min 19;
private _band = _bands select _bandIndex;

// 100 km column.  The column set cycles every three zones.
private _e100k = floor (_easting / 100000);
if ((_e100k < 1) || (_e100k > 8)) exitWith { "" };
private _column = (_columnSets select ((_zone - 1) mod 3)) select (_e100k - 1);

// 100 km row.  AA scheme: odd zones start at A, even zones at F (offset five).
private _r100k = floor (_northing / 100000);
private _rowIndex = _r100k mod 20;
if ((_zone mod 2) == 0) then {
    _rowIndex = (_rowIndex + _evenOffset) mod 20;
};
private _row = _rows select _rowIndex;

// The digits label the south-west corner, so TRUNCATE the offset.
private _scale = 10 ^ (5 - _perAxis);
private _eastValue = floor ((_easting mod 100000) / _scale);
private _northValue = floor ((_northing mod 100000) / _scale);

private _eastStr = "";
private _northStr = "";
private _digit = 0;
for "_d" from 0 to (_perAxis - 1) do {
    _digit = (floor (_eastValue / (10 ^ (_perAxis - 1 - _d)))) mod 10;
    _eastStr = _eastStr + (_digitChars select _digit);
    _digit = (floor (_northValue / (10 ^ (_perAxis - 1 - _d)))) mod 10;
    _northStr = _northStr + (_digitChars select _digit);
};

(_zoneStrings select (_zone - 1)) + _band + _column + _row + _eastStr + _northStr
