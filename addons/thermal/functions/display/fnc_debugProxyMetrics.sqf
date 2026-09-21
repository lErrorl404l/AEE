#include "..\..\script_component.hpp"
/*
Proxy-plane metrics diagnostic (issue #204) - v5.

The one decal never measured: Land_DirtPatch_03_F (the crater mods'
own decal, used in our very first ground test).  All other vanilla
flat pieces measured baked (tex=[] mats=[]).  If DirtPatch has
material slots, it is the tile proxy.

Usage (debug console):
    [] call aee_thermal_fnc_debugProxyMetrics;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];
private _obj = createVehicle ["Land_DirtPatch_03_F", _pos, [], 0, "NONE"];
private _bb = boundingBoxReal _obj;
private _size = [(_bb select 1 select 0) - (_bb select 0 select 0),
                 (_bb select 1 select 1) - (_bb select 0 select 1),
                 (_bb select 1 select 2) - (_bb select 0 select 2)];
private _texs = getObjectTextures _obj;
private _mats = getObjectMaterials _obj;
private _sels = selectionNames _obj;
systemChat format ["AEE metrics: DirtPatch size=%1x%2 tex=%3 mats=%4 sels=%5", _size select 0, _size select 1, count _texs, count _mats, count _sels];
diag_log format ["[AEE][METRICS] DirtPatch size=%1 tex=%2 mats=%3 sels=%4", _size, _texs, _mats, _sels];
deleteVehicle _obj;

[]
