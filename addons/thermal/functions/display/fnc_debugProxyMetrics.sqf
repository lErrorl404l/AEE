#include "..\..\script_component.hpp"
/*
Proxy-plane metrics diagnostic (issue #204) - v3.

road_W10_L9 is 10x9m (ideal tile) but texBefore=[] - road decals have
NO texture selection, setObjectTexture cannot paint them.  Their
material is baked into the model at the decal level.

This tests setObjectMaterial instead: swap the piece's material to the
FPN rvmat (white Stage1 + perlinNoise Stage2 - the material the object
FPN test proved renders in TI).  If the swap applies and shows white +
mottle in TI, the material-swap route is the terrain overlay: spawn
road_W10_L9 pieces, swap to a heat-colour rvmat, done.

The rvmat's ambient/diffuse IS the heat colour - no texture slot needed.

Usage (debug console):
    [] call aee_thermal_fnc_debugProxyMetrics;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];
private _plane = createSimpleObject ["a3\roads_f\Test_RoadsA\road_W10_L9.p3d", _pos];
private _mats = getObjectMaterials _plane;
private _matCount = count _mats;
// swap every material slot to the FPN rvmat
{
    if (_x isEqualType "") then {
        _plane setObjectMaterial [_forEachIndex, "\z\aee\addons\thermal\data\ti_fpn.rvmat"];
    };
} forEach _mats;
private _matsAfter = getObjectMaterials _plane;
systemChat format ["AEE metrics: road_W10_L9 mats=%1 after=%2", _matCount, _matsAfter];
diag_log format ["[AEE][METRICS] road_W10_L9 matCount=%1 matsBefore=%2 matsAfter=%3", _matCount, _mats, _matsAfter];

[]
