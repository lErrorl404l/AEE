#include "..\..\script_component.hpp"
/*
 * ECOTI HUD grid-reference formatter (pure kernel).
 *
 * Splits an engine grid reference into a readable pair.  A 10-figure map
 * reference gives two four-figure halves; an 8-figure gives six-figure
 * halves with a leading zero; anything shorter is returned unchanged.
 *
 * Ported from workshop 3759527903 FPANO_ECOTI/scripts/FPANO_fnc_hud.sqf
 * (the mapGridPosition branch).
 *
 * Params:
 *   0: _gridRaw (STRING) - mapGridPosition of the player.
 *
 * Returns: STRING, the display grid.
 */
params [["_gridRaw", "", [""]]];

private _gridText = _gridRaw;
private _gridLen = count _gridRaw;

if (_gridLen >= 8) then {
    _gridText = (_gridRaw select [0, 4]) + " - " + (_gridRaw select [4, 4]);
} else {
    if (_gridLen >= 6) then {
        _gridText = "0" + (_gridRaw select [0, 3]) + " - 0" + (_gridRaw select [3, 3]);
    };
};

_gridText
