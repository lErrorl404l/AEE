#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyMarkerColor
 *
 * The CfgMarkerColors class for an AEE marker.  Every AEE texture carries its
 * own colour, so the class is NEUTRAL: ColorAEE is white and leaves the texture
 * untouched.  The affiliation colour is not applied by the engine; it lives in
 * the texture, and the affiliation is carried by the marker type
 * FUNC(symbologyMarkerType) selects.
 *
 * The palette still chooses the friendly side, through
 * FUNC(symbologyPaletteFriendly), which drives the affiliation and so the
 * texture; it no longer changes the marker colour class.
 *
 * Arguments:
 *   0: _affiliation <STRING> "friend", "hostile", "neutral" or "unknown"
 *   1: _palette     <STRING> "NATO", "OPFOR" or "Auto"
 *
 * Return: <STRING> the CfgMarkerColors class name, "ColorAEE".
 */
params [
    ["_affiliation", "friend", [""]],
    ["_palette", "NATO", ["Auto"]]
];

"ColorAEE"
