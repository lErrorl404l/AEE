#include "..\..\script_component.hpp"
/*
Proxy-plane metrics diagnostic (issue #204) - v2.

runway_beton_F is 40x80m with NO texture selection (textures=[]) - it
renders its own baked concrete and ignores setObjectTexture, and at
any sane tile scale it is still a giant slab.

The road_W10_L9 pieces (10x9m) DO have texture selections (road_ca.paa
+ road.rvmat).  This spawns one, measures it, paints the mid heat tile,
and reads back getObjectTextures to verify the paint applies.  If it
paints, these are the terrain-overlay tile proxy.

Usage (debug console):
    [] call aee_thermal_fnc_debugProxyMetrics;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];
private _plane = createSimpleObject ["a3\roads_f\Test_RoadsA\road_W10_L9.p3d", _pos];
private _bb = boundingBoxReal _plane;
private _size = [(_bb select 1 select 0) - (_bb select 0 select 0),
                 (_bb select 1 select 1) - (_bb select 0 select 1),
                 (_bb select 1 select 2) - (_bb select 0 select 2)];
private _texsBefore = getObjectTextures _plane;
_plane setObjectTexture [0, "\z\aee\addons\thermal\data\ground\ground_heat_04.paa"];
private _texsAfter = getObjectTextures _plane;
systemChat format ["AEE metrics: road_W10_L9 size %1x%2, tex before=%3 after=%4", _size select 0, _size select 1, _texsBefore, _texsAfter];
diag_log format ["[AEE][METRICS] road_W10_L9 size=%1 texBefore=%2 texAfter=%3", _size, _texsBefore, _texsAfter];

[]
