#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyPaletteFriendly
 *
 * Resolves the friendly side token from the palette.  The NATO palette makes
 * WEST the friendly side, the OPFOR palette makes EAST the friendly side.
 * The Auto palette returns the local side the caller passes.
 *
 * Arguments:
 *   0: _palette   <STRING> "NATO", "OPFOR" or "Auto"
 *   1: _localSide <STRING> the local side token, "WEST" or "EAST"
 *
 * Return: <STRING> the friendly side token.
 */
params [
    ["_palette", "Auto", [""]],
    ["_localSide", "WEST", [""]]
];

private _friendly = _localSide;
if (_palette isEqualTo "NATO") then { _friendly = "WEST"; };
if (_palette isEqualTo "OPFOR") then { _friendly = "EAST"; };

_friendly
