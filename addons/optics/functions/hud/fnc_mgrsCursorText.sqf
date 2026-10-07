#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_mgrsCursorText
 *
 * Format the map cursor readout.  PURE: the MGRS reference and the
 * elevation arrive as arguments, so the kernel reads no map control and no
 * terrain.  The engine cursor tooltip is engine-side and cannot be
 * replaced, so this readout is drawn adjacent to it.
 *
 * Arguments:
 *   0: _mgrs      <STRING> the MGRS reference, or "" when unavailable
 *   1: _elevation <NUMBER> terrain height at the cursor, metres ASL
 *
 * Return: <STRING> the readout, never empty.
 */
params [
    ["_mgrs", "", [""]],
    ["_elevation", 0, [0]]
];

if !(_elevation isEqualType 0) then { _elevation = 0; };

private _elevText = (str (round _elevation)) + " m";
if (_mgrs isEqualTo "") exitWith { "ELEV " + _elevText };

_mgrs + "  " + _elevText
