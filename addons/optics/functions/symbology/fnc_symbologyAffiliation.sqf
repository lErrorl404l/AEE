#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyAffiliation
 *
 * Engine adapter.  Maps a marker colour class name to friend, hostile,
 * neutral or unknown, relative to the friendly side the palette chooses.
 * getMarkerColor returns one of ColorWEST, ColorEAST, ColorGUER, ColorCIV or
 * ColorUNKNOWN.  The colour override is a test seam: an empty override makes
 * the adapter read getMarkerColor.
 *
 * Arguments:
 *   0: _marker       <STRING> the marker name
 *   1: _colourName   <STRING> optional colour class name, for a headless call
 *   2: _friendlySide <STRING> "WEST" or "EAST", from FUNC(symbologyPaletteFriendly)
 *
 * Return: <STRING> "friend", "hostile", "neutral" or "unknown".
 */
params [
    ["_marker", "", [""]],
    ["_colourName", "", [""]],
    ["_friendlySide", "WEST", [""]]
];

private _colour = _colourName;
if (_colour isEqualTo "") then {
    _colour = getMarkerColor _marker;
};

private _side = "UNKNOWN";
if (_colour isEqualTo "ColorWEST") then { _side = "WEST"; };
if (_colour isEqualTo "ColorEAST") then { _side = "EAST"; };
if (_colour isEqualTo "ColorGUER") then { _side = "GUER"; };
if (_colour isEqualTo "ColorCIV") then { _side = "CIV"; };
if (_colour isEqualTo "ColorUNKNOWN") then { _side = "UNKNOWN"; };

private _affiliation = "unknown";
if (_side isEqualTo _friendlySide) then { _affiliation = "friend"; };
if (((_side isEqualTo "GUER") || (_side isEqualTo "CIV")) && (_side isNotEqualTo _friendlySide)) then {
    _affiliation = "neutral";
};
if (((_side isEqualTo "WEST") || (_side isEqualTo "EAST")) && (_side isNotEqualTo _friendlySide)) then {
    _affiliation = "hostile";
};

_affiliation
