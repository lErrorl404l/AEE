#include "..\..\script_component.hpp"
/*
 * ECOTI MGRS marker-label formatter (pure kernel).
 *
 * Formats a marker position as an MGRS reference for the map overlay, the
 * briefing and the diary.  A label, when given, is prefixed.  PURE: the
 * position, the anchor and the precision arrive as arguments, so the kernel
 * reads no world, no marker and no engine grid.
 *
 * Arguments:
 *   0: _label     <STRING> optional label, for example a marker name
 *   1: _position  <ARRAY>  world position [x, y, z], metres
 *   2: _anchor    <ARRAY>  the 9-element geo anchor from EFUNC(lib,getGeoAnchor)
 *   3: _precision <NUMBER> MGRS total digits, one of 4, 6, 8 or 10
 *
 * Returns: <STRING> the label and the MGRS reference, or whichever is
 *          available when the other is empty.
 */
params [
    ["_label", "", [""]],
    ["_position", [0, 0, 0], [[]]],
    ["_anchor", [], [[]]],
    ["_precision", 10, [0]]
];

private _mgrs = "";
private _converted = [_position, _anchor, _precision] call EFUNC(lib,worldToMgrs);
if ((count _converted) >= 1) then {
    _mgrs = _converted select 0;
};

if (_mgrs isEqualTo "") exitWith { _label };
if (_label isEqualTo "") exitWith { _mgrs };

_label + " " + _mgrs
