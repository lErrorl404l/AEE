#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbolPalette
 *
 * Pure symbol colour kernel.  Maps an affiliation and the chosen palette to
 * the symbol colour as RGBA in the range 0 to 1.  PURE: both inputs arrive
 * as arguments, so the kernel reads no setting, no world and no side.
 *
 * The colours are NATO APP-6(C) Table 1-4.  The OPFOR palette swaps the
 * friend and hostile values, so the same symbol grammar serves a red OPFOR
 * force.  The Auto palette returns the NATO set; the adapter resolves Auto
 * against the local side before this call.
 *
 * Arguments:
 *   0: _affiliation <STRING> "friend", "hostile", "neutral" or "unknown"
 *   1: _palette     <STRING> "NATO", "OPFOR" or "Auto"
 *
 * Return: <ARRAY> the colour [r, g, b, a], each 0 to 1.
 */
params [
    ["_affiliation", "friend", [""]],
    ["_palette", "NATO", [""]]
];

// APP-6(C) Table 1-4 display values.
private _friendColour = [0, 1, 1, 1];    // cyan,  Table 1-4 friend
private _hostileColour = [1, 0, 0, 1];   // red,   Table 1-4 hostile
private _neutralColour = [0, 1, 0, 1];   // green, Table 1-4 neutral
private _unknownColour = [1, 1, 0, 1];   // yellow, Table 1-4 unknown

// The OPFOR palette swaps friend and hostile.
if (_palette isEqualTo "OPFOR") then {
    private _swap = _friendColour;
    _friendColour = _hostileColour;
    _hostileColour = _swap;
};

private _colour = _friendColour;
if (_affiliation isEqualTo "hostile") then { _colour = _hostileColour; };
if (_affiliation isEqualTo "neutral") then { _colour = _neutralColour; };
if (_affiliation isEqualTo "unknown") then { _colour = _unknownColour; };

_colour
