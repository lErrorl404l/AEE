#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyMarkerType
 *
 * Pure marker-type kernel.  Maps an affiliation and a class category to the
 * real CfgMarkers type the engine draws, using the generated family and glyph
 * tables aee_optics_symbologyTables.  PURE: the inputs arrive as arguments and
 * the tables are loaded data, so the kernel reads no marker, no unit and no
 * world.
 *
 * The type is "AEE_<family>_<glyph>".  The family is the affiliation: b for
 * friend, o for hostile, n for neutral and u for unknown.  The glyph is the
 * class category's marker token, for example "inf" for infantry.  The
 * dimension, the echelon and the palette are carried: they do not change the
 * type.  The frame a symbol draws is selected by the CfgMarkers class's
 * texture, not by the type name, so a caller that needs an air, sea or
 * installation frame must point the class at a dimension-correct texture.
 *
 * Arguments:
 *   0: _affiliation <STRING> "friend", "hostile", "neutral" or "unknown"
 *   1: _category    <STRING> a class category, for example "infantry"
 *   2: _dimension   <STRING> a dimension token, carried
 *   3: _echelon     <STRING> an echelon token, carried
 *   4: _palette     <STRING> "NATO", "OPFOR" or "Auto", carried
 *
 * Return: <STRING> the CfgMarkers type, for example "AEE_b_inf".
 */
params [
    ["_affiliation", "friend", [""]],
    ["_category", "unknown", [""]],
    ["_dimension", "land", [""]],
    ["_echelon", "unknown", [""]],
    ["_palette", "NATO", [""]]
];

private _tables = aee_symbology_symbologyTables;
private _families = _tables select 4;
private _glyphs = _tables select 5;

// The affiliation to family token, from the generated table.
private _family = "b";
private _found = false;
for "_i" from 0 to ((count _families) - 1) do {
    if (!_found && (_affiliation isEqualTo ((_families select _i) select 0))) then {
        _family = (_families select _i) select 1;
        _found = true;
    };
};

// The class category to glyph token, from the generated table.
private _glyph = "unknown";
_found = false;
for "_i" from 0 to ((count _glyphs) - 1) do {
    if (!_found && (_category isEqualTo ((_glyphs select _i) select 0))) then {
        _glyph = (_glyphs select _i) select 1;
        _found = true;
    };
};

"AEE_" + _family + "_" + _glyph
