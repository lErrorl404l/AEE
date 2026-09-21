#include "..\..\script_component.hpp"
/*
Proxy-plane metrics diagnostic (issue #204) - v9 - Noticeboard test.

Land_Noticeboard_F is the first flat object WITH real texture slots
(tex=1, noticeboard_ca.paa) - the scanner found it.  It is a thin flat
board (0.83x1.58x0.18m); scaled x3-6 it is a 2.5-5m proxy plane, and
unlike every decal measured, it has a REAL material slot.

Test: spawn it scaled, paint the texture slot with the heat tile, and
swap the material to the FPN rvmat (the proven TI-visible render path
on objects).  If it reads hot in TI, the noticeboard is the tile proxy.

Usage (debug console):
    [] call aee_thermal_fnc_debugProxyMetrics;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];
private _obj = createVehicle ["Land_Noticeboard_F", _pos, [], 0, "NONE"];
_obj setObjectScale 3;
_obj setVectorUp [0, 0, 1];
private _texs = getObjectTextures _obj;
private _mats = getObjectMaterials _obj;
// paint + material swap
_obj setObjectTexture [0, "\z\aee\addons\thermal\data\ground\ground_heat_07.paa"];
if (count _mats > 0) then {
    _obj setObjectMaterial [0, "\z\aee\addons\thermal\data\ti_fpn.rvmat"];
};
systemChat format ["AEE metrics: Noticeboard tex=%1 mats=%2 painted+swapped", _texs, _mats];
diag_log format ["[AEE][METRICS] Noticeboard tex=%1 mats=%2 painted+swapped", _texs, _mats];

[]
