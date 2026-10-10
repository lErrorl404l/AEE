#include "..\..\script_component.hpp"
/*
 * aee_cartography_fnc_mapFieldPlan
 *
 * Samples the mod's own PER-POSITION kernels over the visible map rectangle
 * and returns the draw plan for the tactical layers.  This is the only place
 * the overlay touches engine state; the colour, arrow and rose geometry are
 * the pure kernels FUNC(mapBiomeColor), FUNC(mapWindArrow) and
 * FUNC(mapDeclinationRose).
 *
 * Every sample is a real AEE computation, not invented data:
 *   biome   EFUNC(weather,getBiomeAtPosition) - the per-position Koppen code
 *   wind    EFUNC(atmos,getLocalWind)         - the per-position local wind
 *   height  getTerrainHeightASL               - the engine terrain height
 *
 * The two global scalars the issue lists (temperature, WBGT, flood, fire,
 * snow, radio, trafficability) are computed at the PLAYER position only, not
 * as spatial fields, so they are NOT sampled here: drawing them as map zones
 * would invent spatial data.  They appear in the click readout instead.
 *
 * The caller (FUNC(mapOverlayDraw)) throttles this to 1 Hz and caches the
 * result, so a static map does no resampling.
 *
 * Arguments:
 *   0: _rect <ARRAY> [xMin, yMin, xMax, yMax] the visible world rectangle
 *
 * Return: <ARRAY> [biomeCells, windArrows, cellW, cellH]
 *   biomeCells <ARRAY> each [centreX, centreY, code <STRING>, tint <ARRAY>]
 *   windArrows <ARRAY> each [[x0, y0], [x1, y1]] world-metre segments
 *   cellW/cellH <NUMBER> the biome cell size in world metres, for the draw
 */
params [
    ["_rect", [], [[]]]
];
if ((count _rect) < 4) exitWith { [[], [], 0, 0] };

private _x0 = _rect select 0;
private _y0 = _rect select 1;
private _x1 = _rect select 2;
private _y1 = _rect select 3;

// ── Biome field: a coarse grid of per-position Koppen samples ─────────────
// Dozens of cells, not thousands (the issue's marker budget).  The code is
// the mod's own biome kernel at each cell centre.
private _cols = 8;
private _rows = 6;
private _cw = (_x1 - _x0) / _cols;
private _ch = (_y1 - _y0) / _rows;

private _biomeCells = [];
for "_c" from 0 to (_cols - 1) do {
    for "_r" from 0 to (_rows - 1) do {
        private _cx = _x0 + ((_c + 0.5) * _cw);
        private _cy = _y0 + ((_r + 0.5) * _ch);
        private _gz = getTerrainHeightASL [_cx, _cy];
        private _code = [[_cx, _cy, _gz]] call EFUNC(weather,getBiomeAtPosition);
        private _spec = [_code] call FUNC(mapBiomeColor);
        _biomeCells pushBack [_cx, _cy, _code, _spec select 0];
    };
};

// ── Wind field: a coarse grid of per-position local-wind arrows ───────────
private _wcols = 6;
private _wrows = 5;
private _wcw = (_x1 - _x0) / _wcols;
private _wch = (_y1 - _y0) / _wrows;
private _arrowLenM = ((_wcw + _wch) * 0.5) * 0.7;

private _windArrows = [];
for "_c" from 0 to (_wcols - 1) do {
    for "_r" from 0 to (_wrows - 1) do {
        private _cx = _x0 + ((_c + 0.5) * _wcw);
        private _cy = _y0 + ((_r + 0.5) * _wch);
        private _gz = getTerrainHeightASL [_cx, _cy];
        private _wind = [[_cx, _cy, _gz], 2] call EFUNC(atmos,getLocalWind);
        private _seg = [_wind, _arrowLenM] call FUNC(mapWindArrow);
        private _a = _seg select 0;
        private _b = _seg select 1;
        // A calm sample returns a zero segment; skip it.
        if (((_b select 0) != 0) || ((_b select 1) != 0)) then {
            _windArrows pushBack [
                [_cx + (_a select 0), _cy + (_a select 1)],
                [_cx + (_b select 0), _cy + (_b select 1)]
            ];
        };
    };
};

[_biomeCells, _windArrows, _cw, _ch]
