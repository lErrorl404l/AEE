#include "..\..\script_component.hpp"
/*
Proxy-plane metrics diagnostic (issue #204) - v12 - real-material scanner.

v11 showed grey: the noticeboard has mats=[""] - an EMPTY material
slot, so setObjectMaterial never takes (vehicles have real paths like
a3\...\body.rvmat and the FPN swap worked there).  Also verify by
reading back the material AFTER the swap.

Scan a wider batch and report only objects with REAL material paths
(non-empty) + flat shape - those are the tile proxy candidates.

Usage (debug console):
    [] call aee_thermal_fnc_debugProxyMetrics;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];

// first: verify the noticeboard swap readback
private _nb = createVehicle ["Land_Noticeboard_F", _pos, [], 0, "NONE"];
_nb setObjectScale 3;
_nb setVectorUp [0, 0, 1];
_nb setObjectMaterial [0, "\z\aee\addons\thermal\data\ti_heat_07.rvmat"];
private _nbMats = getObjectMaterials _nb;
systemChat format ["AEE: Noticeboard mats after swap = %1", _nbMats];
diag_log format ["[AEE][METRICS] Noticeboard mats-after-swap=%1", _nbMats];
deleteVehicle _nb;

// second: scan a wider batch for REAL material paths
private _candidates = [
    "Land_TableSmall_F", "Land_ChairPlastic_F", "Land_Pallet_F",
    "Land_Metal_plate_F", "Land_Platform_2_F", "Land_CncBlock_Strip_F",
    "Land_BarrelTrash_F", "Land_WoodenCrate_01_F", "Land_CratesShabby_F",
    "Land_Tyre_F", "Land_WoodenBox_F", "Land_PlasticCase_01_F",
    "Land_Bucket_F", "Land_CinderBlock_F", "Land_Pipes_large_F"
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
        private _mats = getObjectMaterials _obj;
        private _realMats = _mats select { _x isEqualType "" && {_x != ""} };
        if (count _realMats > 0) then {
            systemChat format ["AEE: %1 %2x%3x%4 REALMATS=%5", _cls, _size select 0, _size select 1, _size select 2, _realMats];
            diag_log format ["[AEE][METRICS] %1 size=%2 realMats=%3", _cls, _size, _realMats];
        };
        deleteVehicle _obj;
    };
} forEach _candidates;

[]
