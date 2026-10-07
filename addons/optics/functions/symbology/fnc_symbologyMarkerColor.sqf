#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyMarkerColor
 *
 * Pure marker-colour kernel.  Maps an affiliation and the chosen palette to
 * the CfgMarkerColors class name the engine marker uses.  PURE: both inputs
 * arrive as arguments, so the kernel reads no setting, no world and no side.
 *
 * friend  ColorWEST, hostile ColorEAST, neutral ColorGUER, unknown
 * ColorUNKNOWN.  The OPFOR palette swaps friend and hostile, so an OPFOR
 * group's own side is red.  The Auto palette resolves from the local side
 * through FUNC(symbologyPaletteFriendly) before this call, which is why this
 * kernel treats Auto as NATO and stays argument-driven.
 *
 * Arguments:
 *   0: _affiliation <STRING> "friend", "hostile", "neutral" or "unknown"
 *   1: _palette     <STRING> "NATO", "OPFOR" or "Auto"
 *
 * Return: <STRING> the CfgMarkerColors class name.
 */
params [
    ["_affiliation", "friend", [""]],
    ["_palette", "NATO", [""]]
];

private _friend = "ColorWEST";
private _hostile = "ColorEAST";

// The OPFOR palette swaps friend and hostile.
if (_palette isEqualTo "OPFOR") then {
    _friend = "ColorEAST";
    _hostile = "ColorWEST";
};

private _colour = _friend;
if (_affiliation isEqualTo "hostile") then { _colour = _hostile; };
if (_affiliation isEqualTo "neutral") then { _colour = "ColorGUER"; };
if (_affiliation isEqualTo "unknown") then { _colour = "ColorUNKNOWN"; };

_colour
