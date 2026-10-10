#include "..\..\script_component.hpp"
/*
 * aee_cartography_fnc_mapLegendDraw
 *
 * Pure kernel.  Returns the AEE topographic legend rows as
 *   [[swatchRGBA, label], ...]
 * from a FIXED row spec.  The engine owns the map Legend class and draws its
 * body, so a mod cannot author one (docs/engine/topo-map-surface.md:186-194);
 * the only route to a real legend body is SQF, so the Draw hook draws these
 * rows.
 *
 * The swatch colours are never literals: each row names a palette KEY, and the
 * kernel RESOLVES the colour from the _palette argument.  The caller passes the
 * same table the map config is pinned to, data/symbology/terrain_symbols.json
 * (map_colours for the map palette, palette for the terrain symbol groups), so
 * the legend and the map share one source.  A key that is absent from _palette
 * is skipped, so a caller never draws an empty swatch.
 *
 * The kernel is pure: it reads no config, no marker, no unit and no world.  The
 * palette arrives as an argument.
 *
 * Arguments:
 *   0: _palette <ARRAY> each [name <STRING>, [r, g, b, a] <ARRAY>]
 *
 * Return: <ARRAY> each [[r, g, b, a], label <STRING>], in legend order:
 *   the map palette (relief brown, water blue, vegetation green, roads red,
 *   the index and the intermediate contour), then the terrain symbol groups.
 */
params [
    ["_palette", [], [[]]]
];

private _rows = [
    // The map palette.
    ["relief_brown", "Relief"],
    ["water_blue", "Water"],
    ["vegetation_green", "Vegetation"],
    ["transport_red", "Roads"],
    ["contour_index", "Index contour"],
    ["contour_intermediate", "Intermediate contour"],
    // The terrain symbol groups (the icon categories).
    ["group_relief", "Hill and rock"],
    ["group_vegetation", "Woodland"],
    ["group_hydrography", "Water feature"],
    ["group_populated", "Built-up area"],
    ["group_works", "Works"],
    ["group_transport", "Transport"],
    ["group_boundary", "Boundary"],
    ["group_control", "Control point"],
    ["group_military", "Military"]
];

private _count = count _palette;
private _out = [];
{
    private _key = _x select 0;
    private _label = _x select 1;
    private _rgba = [];
    for "_i" from 0 to (_count - 1) do {
        private _entry = _palette select _i;
        if (((_entry select 0) isEqualTo _key) && ((count (_entry select 1)) == 4)) then {
            _rgba = _entry select 1;
        };
    };
    if ((count _rgba) == 4) then {
        _out pushBack [_rgba, _label];
    };
} forEach _rows;

_out
