#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbolPalette
 *
 * The draw tint for an AEE symbol texture.  Every AEE texture carries its own
 * colour (the affiliation frame, the black glyph and the standard fills), so
 * the tint is NEUTRAL: [1, 1, 1, 1] leaves the texture's colours untouched.
 * The affiliation colour is not applied as a tint; it lives in the texture, and
 * the affiliation is carried by the marker type FUNC(symbologyMarkerType)
 * selects.
 *
 * The palette still chooses the friendly side, through
 * FUNC(symbologyPaletteFriendly), which drives the affiliation and so the
 * texture; it no longer changes the tint.
 *
 * Arguments:
 *   0: _affiliation <STRING> "friend", "hostile", "neutral" or "unknown"
 *   1: _palette     <STRING> "NATO", "OPFOR" or "Auto"
 *
 * Return: <ARRAY> the neutral tint [1, 1, 1, 1].
 */
params [
    ["_affiliation", "friend", [""]],
    ["_palette", "NATO", [""]]
];

[1, 1, 1, 1]
