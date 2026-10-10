#include "..\..\script_component.hpp"
/*
 * aee_cartography_fnc_mapIconWorldSize
 *
 * Pure kernel.  Converts a desired on-map size in world metres to the
 * drawIcon width and height in screen pixels, so an icon keeps its real
 * ground size at every map zoom.
 *
 * The engine draws a map icon at a constant pixel size that does not change
 * with the zoom (BIKI drawIcon note, Leopard20 2022-05-09).  To hold an icon
 * at a fixed WORLD size the pixel size must therefore scale with the
 * displayed scale:
 *
 *     pixels = metres / (6.4 * worldSize / 8192 * scale)
 *
 * The scale and the world size arrive as arguments, so the kernel reads no
 * control and no world.  The caller passes worldSize and ctrlMapScale _map.
 * The returned value is used for both the drawIcon width and height, so the
 * box stays square and the texture is not stretched.
 *
 * Source: the community-documented conversion,
 * docs/engine/arma-map-grid-semantics.md:93-97 (Q4).  Technique from APP6
 * Markers (3009271265), reimplemented with AEE's own code; the mod file is
 * not copied.  The constants 6.4 and 8192 are UNSOURCED: no primary engine
 * source publishes them, only the community note's empirical fit.
 *
 * Arguments:
 *   0: _metres    <NUMBER> the desired on-map size in world metres
 *   1: _worldSize <NUMBER> the world size in metres (worldSize)
 *   2: _scale     <NUMBER> the displayed map scale (ctrlMapScale _map)
 *
 * Return: <NUMBER> the drawIcon width and height in screen pixels.  0 for a
 * non-positive world size or scale, so a caller never draws a bad box.
 */
params [
    ["_metres", 0, [0]],
    ["_worldSize", 0, [0]],
    ["_scale", 0, [0]]
];

private _pixels = 0;
if ((_worldSize > 0) && (_scale > 0)) then {
    _pixels = _metres / (6.4 * _worldSize / 8192 * _scale);
};

_pixels
