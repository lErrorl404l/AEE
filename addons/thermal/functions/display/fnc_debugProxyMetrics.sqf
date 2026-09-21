#include "..\..\script_component.hpp"
/*
Proxy-plane metrics diagnostic (issue #204) - v10 - swap-then-paint.

v9 showed the noticeboard grey: the paint landed then the material
swap replaced the material, so the FPN rvmat's white Stage1 showed
instead of the heat tile.  Correct order is SWAP FIRST, PAINT SECOND -
the paint then lands on the FPN rvmat's Stage1 (the same order
production uses), and perlinNoise Stage2 multiplies over it.

Usage (debug console):
    [] call aee_thermal_fnc_debugProxyMetrics;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];
private _obj = createVehicle ["Land_Noticeboard_F", _pos, [], 0, "NONE"];
_obj setObjectScale 3;
_obj setVectorUp [0, 0, 1];
private _mats = getObjectMaterials _obj;
// SWAP first (FPN rvmat, proven TI-visible), THEN paint the heat tile
if (count _mats > 0) then {
    _obj setObjectMaterial [0, "\z\aee\addons\thermal\data\ti_fpn.rvmat"];
};
_obj setObjectTexture [0, "\z\aee\addons\thermal\data\ground\ground_heat_07.paa"];
systemChat "AEE metrics: Noticeboard swap-then-paint (heat_07 + FPN rvmat)";
diag_log "[AEE][METRICS] Noticeboard swap-then-paint heat_07 + ti_fpn";

[]
