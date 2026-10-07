#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbolIcon
 *
 * Pure inner-glyph kernel.  Maps an icon identifier to a list of vector
 * primitives in the inner box [-0.55, 0.55].  PURE: the identifier arrives as
 * an argument, so the kernel reads no texture, no file and no engine entity.
 *
 * Each primitive is [kind, points].  kind is "line", "poly" or "ellipse".
 * For "line" and "poly", points is a list of [x, y].  For "ellipse", points
 * is [centre, [a, b], angleDegrees].
 *
 * The glyphs describe the APP-6(C) function icons.  The standard names the
 * functions and gives no coordinates, so every glyph here is a derived or
 * UNSOURCED vector approximation.  The set is curated to about twenty
 * classes; anything outside it falls back to the engine icon texture in the
 * draw layer.
 *
 * Arguments:
 *   0: _iconId <STRING> a class category, for example "infantry"
 *
 * Return: <ARRAY> the primitive list, empty for "unknown".
 */
params [
    ["_iconId", "unknown", [""]]
];

private _prims = [];

if (_iconId isEqualTo "infantry") then {
    // Saltire: two crossed lines.
    _prims = [
        ["line", [[-0.55, -0.55], [0.55, 0.55]]],
        ["line", [[-0.55, 0.55], [0.55, -0.55]]]
    ];
};
if (_iconId isEqualTo "armour") then {
    // Tracked oval.
    _prims = [["ellipse", [[0, 0], [0.55, 0.33], 0]]];
};
if (_iconId isEqualTo "motorised") then {
    // Oval plus two wheel marks.
    _prims = [
        ["ellipse", [[0, 0], [0.55, 0.3], 0]],
        ["line", [[-0.3, -0.3], [-0.3, -0.48]]],
        ["line", [[0.3, -0.3], [0.3, -0.48]]]
    ];
};
if (_iconId isEqualTo "artillery") then {
    // Filled dot.
    _prims = [["ellipse", [[0, 0], [0.22, 0.22], 0]]];
};
if (_iconId isEqualTo "engineer") then {
    // Bracket: three sides of a square.
    _prims = [["poly", [[-0.45, -0.45], [-0.45, 0.45], [0.45, 0.45], [0.45, -0.45]]]];
};
if (_iconId isEqualTo "signal") then {
    // Spark.
    _prims = [["poly", [[-0.45, 0], [-0.15, 0.45], [0.05, -0.45], [0.35, 0.45], [0.45, 0]]]];
};
if (_iconId isEqualTo "medical") then {
    // Cross.
    _prims = [
        ["line", [[-0.45, 0], [0.45, 0]]],
        ["line", [[0, -0.45], [0, 0.45]]]
    ];
};
if (_iconId isEqualTo "supply") then {
    // Box.
    _prims = [["poly", [[-0.45, -0.35], [0.45, -0.35], [0.45, 0.35], [-0.45, 0.35]]]];
};
if (_iconId isEqualTo "support") then {
    // Bracket plus a centre dot.
    _prims = [
        ["poly", [[-0.45, -0.45], [-0.45, 0.45], [0.45, 0.45], [0.45, -0.45]]],
        ["ellipse", [[0, 0], [0.16, 0.16], 0]]
    ];
};
if (_iconId isEqualTo "recon") then {
    // Diagonal.
    _prims = [["line", [[-0.45, -0.45], [0.45, 0.45]]]];
};
if (_iconId isEqualTo "air_defence") then {
    // Arc plus dot.
    _prims = [
        ["poly", [[-0.45, -0.2], [-0.3, 0.25], [0, 0.4], [0.3, 0.25], [0.45, -0.2]]],
        ["ellipse", [[0, -0.1], [0.14, 0.14], 0]]
    ];
};
if (_iconId isEqualTo "fixed_wing") then {
    // Aircraft outline.
    _prims = [["poly", [
        [0, 0.5], [0.12, 0.1], [0.5, 0], [0.12, -0.1],
        [0, -0.5], [-0.12, -0.1], [-0.5, 0], [-0.12, 0.1]
    ]]];
};
if (_iconId isEqualTo "rotary") then {
    // Rotor cross plus a small circle.
    _prims = [
        ["line", [[-0.5, 0], [0.5, 0]]],
        ["line", [[0, -0.5], [0, 0.5]]],
        ["ellipse", [[0, 0], [0.16, 0.16], 0]]
    ];
};
if (_iconId isEqualTo "uav") then {
    // Small aircraft.
    _prims = [["poly", [
        [0, 0.4], [0.08, 0.05], [0.4, 0], [0.08, -0.05],
        [0, -0.4], [-0.08, -0.05], [-0.4, 0], [-0.08, 0.05]
    ]]];
};
if (_iconId isEqualTo "sea_surface") then {
    // Hull.
    _prims = [["poly", [[-0.5, 0.1], [0.5, 0.1], [0.35, -0.35], [-0.35, -0.35]]]];
};
if (_iconId isEqualTo "subsurface") then {
    // Hull plus a lower bar.
    _prims = [
        ["poly", [[-0.5, 0.1], [0.5, 0.1], [0.35, -0.35], [-0.35, -0.35]]],
        ["line", [[-0.5, -0.45], [0.5, -0.45]]]
    ];
};
if (_iconId isEqualTo "installation") then {
    // Bar.
    _prims = [["poly", [[-0.5, -0.15], [0.5, -0.15], [0.5, 0.15], [-0.5, 0.15]]]];
};
if (_iconId isEqualTo "hq") then {
    // Flag.
    _prims = [
        ["line", [[-0.4, -0.5], [-0.4, 0.5]]],
        ["poly", [[-0.4, 0.5], [0.45, 0.3], [-0.4, 0.1]]]
    ];
};
if (_iconId isEqualTo "waypoint") then {
    // Small square.
    _prims = [["poly", [[-0.3, -0.3], [0.3, -0.3], [0.3, 0.3], [-0.3, 0.3]]]];
};

_prims
