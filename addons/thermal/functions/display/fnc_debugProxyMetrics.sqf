#include "..\..\script_component.hpp"
/*
Proxy-plane metrics diagnostic (issue #204) - v6.

Land_DirtPatch_03_F has ONE selection: "usertexture" - the decal's
engine-projected texture hook.  getObjectTextures returns [] because
the texture is generated/projected, but setObjectTexture by SELECTION
NAME is the designed way to address decal textures.

Test: paint the usertexture selection with the mid heat tile and read
back what the object reports.

Usage (debug console):
    [] call aee_thermal_fnc_debugProxyMetrics;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];
private _obj = createVehicle ["Land_DirtPatch_03_F", _pos, [], 0, "NONE"];
_obj setObjectTexture ["usertexture", "\z\aee\addons\thermal\data\ground\ground_heat_04.paa"];
private _texs = getObjectTextures _obj;
private _mats = getObjectMaterials _obj;
systemChat format ["AEE metrics: DirtPatch painted usertexture, tex=%1 mats=%2", _texs, _mats];
diag_log format ["[AEE][METRICS] DirtPatch usertexture painted, tex=%1 mats=%2", _texs, _mats];

[]
