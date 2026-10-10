#include "..\..\script_component.hpp"
/*
 * aee_cartography_fnc_mapOverlayDraw
 *
 * Draws the AEE physics-state tactical layers on the open map control.  It is
 * called from the ONE map Draw handler (FUNC(mgrsMapDraw)), so the map keeps a
 * single rendering path; this function does not register its own Draw handler.
 *
 * Layers (each grounded in the mod's own computed state):
 *   biome       a coloured Koppen cell per sample   EFUNC(weather,getBiomeAtPosition)
 *   wind        a local-wind arrow per sample        EFUNC(atmos,getLocalWind)
 *   declination the true-north and magnetic-north rays  EGVAR(core,magneticDeclinationDeg)
 *
 * The field is sampled by FUNC(mapFieldPlan) at most once a second, keyed on
 * the rounded visible rectangle, so a static map resamples nothing.  The
 * drawLine framerate caveat (#146) is respected by that throttle.
 *
 * Arguments:
 *   0: _map  <CONTROL> the map control (a CT_MAP)
 *   1: _rect <ARRAY>   the visible world rectangle, as FUNC(mapFieldPlan) takes
 *   2: _font <STRING>  the overlay font the Draw handler selected
 *
 * Returns: nothing.
 */
params [
    ["_map", controlNull, [controlNull]],
    ["_rect", [], [[]]],
    ["_font", "PuristaMedium", [""]]
];

if (isNull _map) exitWith {};
if ((count _rect) < 4) exitWith {};
if !(missionNamespace getVariable [QGVAR(mapOverlayEnabled), false]) exitWith {};

// ── Throttle: rebuild the field plan at most once a second ────────────────
private _now = diag_tickTime;
private _cache = missionNamespace getVariable [QGVAR(mapOverlayCache), []];
private _key = _rect apply { round (_x / 25) };
private _fresh = false;
if (
    (_cache isEqualType [])
    && {((count _cache) == 3)}
    && {(_cache select 0) isEqualTo _key}
    && {(_now - (_cache select 2)) < 1}
) then { _fresh = true; };

private _plan = [];
if (_fresh) then {
    _plan = _cache select 1;
} else {
    _plan = [_rect] call FUNC(mapFieldPlan);
    missionNamespace setVariable [QGVAR(mapOverlayCache), [_key, _plan, _now]];
};
if !(_plan isEqualType []) then { _plan = [[], [], 0, 0]; };
if ((count _plan) < 4) exitWith {};

_plan params ["_biomeCells", "_windArrows", "_cellW", "_cellH"];

private _worldSize = worldSize;
private _scale = ctrlMapScale _map;
private _span = ((_rect select 2) - (_rect select 0)) max ((_rect select 3) - (_rect select 1));

// ── Biome field ───────────────────────────────────────────────────────────
if (missionNamespace getVariable [QGVAR(mapBiomeLayer), true]) then {
    private _pxW = [_cellW, _worldSize, _scale] call FUNC(mapIconWorldSize);
    private _pxH = [_cellH, _worldSize, _scale] call FUNC(mapIconWorldSize);
    if ((_pxW > 0) && (_pxH > 0)) then {
        {
            _x params ["_cx", "_cy", "_code", "_tint"];
            private _fill = format [
                "#(argb,8,8,3)color(%1,%2,%3,%4)",
                _tint select 0, _tint select 1, _tint select 2, _tint select 3
            ];
            _map drawIcon [
                _fill, [1, 1, 1, 1], [_cx, _cy], _pxW, _pxH, 0,
                _code, 1, 0.016, _font, "center"
            ];
        } forEach _biomeCells;
    };
};

// ── Wind field ────────────────────────────────────────────────────────────
if (missionNamespace getVariable [QGVAR(mapWindLayer), true]) then {
    {
        _x params ["_a", "_b"];
        _map drawLine [_a, _b, [0.10, 0.20, 0.45, 0.9], 2];
    } forEach _windArrows;
};

// ── Magnetic-declination rose ─────────────────────────────────────────────
if (missionNamespace getVariable [QGVAR(mapDeclinationRose), true]) then {
    private _decl = missionNamespace getVariable [QEGVAR(core,magneticDeclinationDeg), 0];
    if !(_decl isEqualType 0) then { _decl = 0; };
    private _radius = _span * 0.06;
    private _rose = [_decl, _radius] call FUNC(mapDeclinationRose);
    private _trueN = _rose select 0;
    private _magN = _rose select 1;
    private _rx = (_rect select 2) - (_span * 0.10);
    private _ry = (_rect select 3) - (_span * 0.10);
    // True north (the map up axis) is dark; magnetic north is red.
    _map drawLine [[_rx, _ry], [_rx + (_trueN select 0), _ry + (_trueN select 1)], [0.05, 0.05, 0.05, 0.9], 3];
    _map drawLine [[_rx, _ry], [_rx + (_magN select 0), _ry + (_magN select 1)], [0.60, 0.10, 0.10, 0.9], 3];
    _map drawIcon [
        "", [0.05, 0.05, 0.05, 1],
        [_rx + (_trueN select 0), _ry + (_trueN select 1)],
        0, 0, 0, "N", 1, 0.018, _font, "center"
    ];
};
