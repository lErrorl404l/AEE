#include "..\..\script_component.hpp"
/*
Proxy-plane metrics diagnostic (issue #204) - v7.

The usertexture paint WORKS (seen in-game) but the .paa tile at heat
level 04 reads dark/cold - the mid tile is half-brightness red and TI
reads its luminance.  The proven object paint uses a FULL-brightness
procedural colour #(rgb,8,8,3)color(1,0.10,0.20,1).

This paints the usertexture selection with the full WHOT-red procedural
colour (no .paa) - if it reads bright/hot in TI, the overlay uses the
procedural string directly.

Usage (debug console):
    [] call aee_thermal_fnc_debugProxyMetrics;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];
private _obj = createVehicle ["Land_DirtPatch_03_F", _pos, [], 0, "NONE"];
_obj setObjectScale 0.8;
_obj setObjectTexture ["usertexture", "#(rgb,8,8,3)color(1,0.10,0.20,1)"];
systemChat "AEE metrics: DirtPatch painted FULL WHOT-red procedural";
diag_log "[AEE][METRICS] DirtPatch usertexture = full WHOT-red procedural";

[]
