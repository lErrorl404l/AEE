#include "..\..\script_component.hpp"
/*
 * aee_cartography_fnc_mapStateReadout
 *
 * Pure kernel.  Formats a map click-query result into the mod's weather-report
 * style text block.  The rows arrive as arguments, so the kernel reads no
 * world, no player and no AEE state: the caller supplies every value and its
 * source.
 *
 * Arguments:
 *   0: _title <STRING> the block header, without the surrounding markers
 *   1: _rows  <ARRAY>  each [label <STRING>, value <STRING>]
 *
 * Return: <STRING> a multi-line block:
 *   === <title> ===
 *   <label>: <value>
 *   ...
 *   A row with an empty value is skipped, so a caller never prints a blank.
 */
params [
    ["_title", "", [""]],
    ["_rows", [], [[]]]
];

private _out = "=== " + _title + " ===";
{
    private _label = _x select 0;
    private _value = _x select 1;
    if (_value isNotEqualTo "") then {
        _out = _out + "\n" + _label + ": " + _value;
    };
} forEach _rows;

_out
