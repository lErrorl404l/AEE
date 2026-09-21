#include "..\..\script_component.hpp"
/*
Proxy-plane metrics diagnostic (issue #204) - v4.

Road decals are fully material-baked: runway_beton and road_W10_L9 both
report tex=[] AND mats=[] - no texture or material slot is scriptable.
The terrain overlay needs a piece with SWAPPABLE materials (the FPN
object test proved material swaps render in TI).

Candidates: Land_ClutterCutter_large_F (the crater mods' decal) and a
flat Land_ object.  This spawns each, measures it, and reports
getObjectTextures + getObjectMaterials so we see which one can be
painted or material-swapped.

Usage (debug console):
    [] call aee_thermal_fnc_debugProxyMetrics;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];
private _candidates = ["Land_ClutterCutter_large_F", "Land_HelipadSquare_F", "Land_Runway_20_F"];
{
    private _cls = _x;
    private _obj = objNull;
    if (_cls find ".p3d" >= 0) then {
        _obj = createSimpleObject [_cls, _pos];
    } else {
        _obj = createVehicle [_cls, _pos, [], 0, "NONE"];
    };
    if (!isNull _obj) then {
        private _bb = boundingBoxReal _obj;
        private _size = [(_bb select 1 select 0) - (_bb select 0 select 0),
                         (_bb select 1 select 1) - (_bb select 0 select 1),
                         (_bb select 1 select 2) - (_bb select 0 select 2)];
        private _texs = getObjectTextures _obj;
        private _mats = getObjectMaterials _obj;
        systemChat format ["AEE metrics: %1 size=%2x%3 tex=%4 mats=%5", _cls, _size select 0, _size select 1, count _texs, count _mats];
        diag_log format ["[AEE][METRICS] %1 size=%2 tex=%3 mats=%4", _cls, _size, _texs, _mats];
        deleteVehicle _obj;
    } else {
        systemChat format ["AEE metrics: %1 FAILED to spawn", _cls];
        diag_log format ["[AEE][METRICS] %1 spawn FAILED", _cls];
    };
} forEach _candidates;

[]
