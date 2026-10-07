#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbolResolve
 *
 * Pure symbol resolver.  Maps a side, a class category, an affiliation, an
 * echelon and a palette to one symbol specification.  PURE: every input
 * arrives as an argument, so the resolver reads no marker, no unit and no
 * world.  The side is carried for the caller's symmetry; the affiliation is
 * already resolved before this call.
 *
 * The frame shape comes from the affiliation, the NATO APP-6(C) frame
 * grammar.  The dimension and the icon id come from the class category.  The
 * colour comes from FUNC(symbolPalette).  The frame shape token is consumed
 * by FUNC(symbolFrame), which produces the outline in the draw layer.
 *
 * Arguments:
 *   0: _side        <ANY>    the engine side, carried, not read
 *   1: _category    <STRING> a class category, for example "infantry"
 *   2: _affiliation <STRING> "friend", "hostile", "neutral" or "unknown"
 *   3: _echelon     <STRING> an echelon token, for example "squad"
 *   4: _palette     <STRING> "NATO", "OPFOR" or "Auto"
 *
 * Return: <ARRAY> [affiliation, frameShape, dimension, colourRGBA, iconId,
 *          echelon]
 */
params [
    ["_side", "", []],
    ["_category", "unknown", [""]],
    ["_affiliation", "friend", [""]],
    ["_echelon", "unknown", [""]],
    ["_palette", "NATO", [""]]
];

// The frame shape from the affiliation, APP-6(C).
private _frameShape = "rect";
if (_affiliation isEqualTo "hostile") then { _frameShape = "diamond"; };
if (_affiliation isEqualTo "neutral") then { _frameShape = "square"; };
if (_affiliation isEqualTo "unknown") then { _frameShape = "quatrefoil"; };

// The category maps to a dimension and an icon id.
private _dimension = "land";
private _iconId = "unknown";
if (_category isEqualTo "infantry") then { _iconId = "infantry"; };
if (_category isEqualTo "armour") then { _iconId = "armour"; };
if (_category isEqualTo "motorised") then { _iconId = "motorised"; };
if (_category isEqualTo "artillery") then { _iconId = "artillery"; };
if (_category isEqualTo "engineer") then { _iconId = "engineer"; };
if (_category isEqualTo "signal") then { _iconId = "signal"; };
if (_category isEqualTo "medical") then { _iconId = "medical"; };
if (_category isEqualTo "supply") then { _iconId = "supply"; };
if (_category isEqualTo "support") then { _iconId = "support"; };
if (_category isEqualTo "recon") then { _iconId = "recon"; };
if (_category isEqualTo "air_defence") then { _iconId = "air_defence"; };
if (_category isEqualTo "hq") then { _iconId = "hq"; };
if (_category isEqualTo "waypoint") then { _iconId = "waypoint"; };
if (_category isEqualTo "fixed_wing") then {
    _dimension = "air";
    _iconId = "fixed_wing";
};
if (_category isEqualTo "rotary") then {
    _dimension = "air";
    _iconId = "rotary";
};
if (_category isEqualTo "uav") then {
    _dimension = "air";
    _iconId = "uav";
};
if (_category isEqualTo "sea_surface") then {
    _dimension = "sea";
    _iconId = "sea_surface";
};
if (_category isEqualTo "subsurface") then {
    _dimension = "subsurface";
    _iconId = "subsurface";
};
if (_category isEqualTo "installation") then {
    _dimension = "installation";
    _iconId = "installation";
};

private _colour = [_affiliation, _palette] call FUNC(symbolPalette);

[_affiliation, _frameShape, _dimension, _colour, _iconId, _echelon]
