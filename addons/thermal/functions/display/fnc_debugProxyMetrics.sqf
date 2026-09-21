#include "..\..\script_component.hpp"
/*
Proxy-plane metrics diagnostic (issue #204) - v8 - MATERIAL SCANNER.

All flat decals measured so far (DirtPatch, ClutterCutter, runway,
road_W10_L9, HelipadSquare) report tex=[] mats=[] - no paintable slot,
and the usertexture paint does NOT reach the TI render (seen cold).

The FPN test PROVED objects with real material slots render our
material swap in TI.  This scans a batch of flat-ish vanilla objects
for tex/mats counts - the one with mats > 0 and a flat shape is the
tile proxy (material-swapped to a heat rvmat).

Usage (debug console):
    [] call aee_thermal_fnc_debugProxyMetrics;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];
private _candidates = [
    "Land_CncWall1_F", "Land_CncWall4_F", "Land_MetalBarrel_F",
    "Land_Noticeboard_F", "Land_CampingTable_F", "Land_TableBig_F",
    "Land_BagFence_Long_F", "Land_Target_F", "Land_Scaffolding_F",
    "Land_CratesWooden_F", "Land_GarbagePallet_F", "Land_Sacks_goods_F"
];
{
    private _cls = _x;
    private _obj = objNull;
    try {
        _obj = createVehicle [_cls, _pos, [], 0, "NONE"];
    } catch { };
    if (!isNull _obj) then {
        private _bb = boundingBoxReal _obj;
        private _size = [(_bb select 1 select 0) - (_bb select 0 select 0),
                         (_bb select 1 select 1) - (_bb select 0 select 1),
                         (_bb select 1 select 2) - (_bb select 0 select 2)];
        private _texs = getObjectTextures _obj;
        private _mats = getObjectMaterials _obj;
        systemChat format ["AEE: %1 %2x%3x%4 tex=%5 mats=%6", _cls, _size select 0, _size select 1, _size select 2, count _texs, count _mats];
        diag_log format ["[AEE][METRICS] %1 size=%2 tex=%3 mats=%4", _cls, _size, _texs, _mats];
        deleteVehicle _obj;
    } else {
        systemChat format ["AEE: %1 FAILED", _cls];
    };
} forEach _candidates;

[]
