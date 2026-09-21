#include "..\..\script_component.hpp"
/*
NVG camouflage contrast (issue #119).

The black-hole effect: modern camo (OCP/MTP/MARPAT) reflects 35-45% in
the NIR band (700-900 nm), matching vegetation (40-50%) - the soldier
blends under NVG.  Black (non-matched) reflects only 5-10% - a black
hole against the NIR-bright background.

  camo_coeff = 1 - |R_uniform - R_bg| / dR_max
  C_eff      = C * (1 - camo_coeff)
  P_detect   = 1 / (1 + (N50/N)^k)

The uniform's NIR reflectance comes from fnc_getClothingInsulation.
The result feeds the NVG visibility (the optics module reads it to
scale the soldier's brightness in the NVG tube).

Arguments:
  0: unit (OBJECT, default player)

Returns the NVG contrast coefficient 0..1:
  1.0 = perfect blend (uniform NIR matches background)
  0.0 = maximum contrast (the black hole)
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { 0.0 };

private _clothing = [_unit] call FUNC(getClothingInsulation);
private _nirUniform = _clothing select 2;

// The per-selection NIR (uniform + vest + helmet materials, area-
// weighted) is the signature the NVG tube ACTUALLY sees - a plate
// carrier with metal mag pouches reads brighter than bare cloth.  Fall
// back to the uniform-only value when the selections cannot be read.
private _nirEffective = ([_unit] call FUNC(getNirPerSelection)) max _nirUniform;

// The background NIR reflectance: vegetation 40-50% (the NVG-matched
// baseline).  A built-up/urban background would differ, but the field
// default is the vegetation match the camo is designed for.
private _nirBg = 0.45;
private _dRMax = 0.40;   // the NIR band range (0.05 black .. 0.45 veg)

private _camoCoeff = 1 - ((abs (_nirEffective - _nirBg)) / _dRMax);
_camoCoeff max 0 min 1

