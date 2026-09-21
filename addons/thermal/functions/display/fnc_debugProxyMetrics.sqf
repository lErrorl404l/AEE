#include "..\..\script_component.hpp"
/*
Proxy-plane metrics diagnostic (issue #204) - v11 - colour-in-material.

v10 showed grey with the tile painted: the TI pass reads the material's
COLOUR (ambient/diffuse), not the Stage1 texture.  ti_fpn.rvmat has
white ambient -> white-grey in TI regardless of the painted tile.  A3TI
carries the heat entirely in ambient/diffuse (TIRed has NO texture).

Test: swap the noticeboard to ti_heat_07.rvmat - full WHOT-red in
ambient/diffuse.  If it reads HOT in TI, the terrain overlay is solved:
swap tiles to ti_heat_XX.rvmat per heat level.

Usage (debug console):
    [] call aee_thermal_fnc_debugProxyMetrics;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];
private _obj = createVehicle ["Land_Noticeboard_F", _pos, [], 0, "NONE"];
_obj setObjectScale 3;
_obj setVectorUp [0, 0, 1];
_obj setObjectMaterial [0, "\z\aee\addons\thermal\data\ti_heat_07.rvmat"];
systemChat "AEE metrics: Noticeboard swapped to ti_heat_07 (red ambient/diffuse)";
diag_log "[AEE][METRICS] Noticeboard -> ti_heat_07 (red in material colour)";

[]
