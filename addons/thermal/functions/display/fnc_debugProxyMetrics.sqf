#include "..\..\script_component.hpp"
/*
Proxy-plane metrics diagnostic (issue #204).

The runway_beton_F grid merged into one giant road because the piece is
large by default and the grid scale (step*1.3) was far too big.  This
spawns ONE proxy, measures its real size (boundingBoxReal), paints the
mid heat tile, then reads back getObjectTextures to verify the paint
actually applied.

Usage (debug console):
    [] call aee_thermal_fnc_debugProxyMetrics;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];
private _plane = createSimpleObject ["a3\roads_f\runway\runway_beton_F.p3d", _pos];
private _bb = boundingBoxReal _plane;
private _size = [(_bb select 1 select 0) - (_bb select 0 select 0),
                 (_bb select 1 select 1) - (_bb select 0 select 1),
                 (_bb select 1 select 2) - (_bb select 0 select 2)];
systemChat format ["AEE metrics: runway_beton natural size %1x%2x%3", _size select 0, _size select 1, _size select 2];

_plane setObjectTexture [0, "\z\aee\addons\thermal\data\ground\ground_heat_04.paa"];
private _texs = getObjectTextures _plane;
systemChat format ["AEE metrics: after paint textures = %1", _texs];
diag_log format ["[AEE][METRICS] runway_beton size=%1 textures=%2", _size, _texs];

[]
