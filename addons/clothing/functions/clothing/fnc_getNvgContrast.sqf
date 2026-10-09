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

The uniform's NIR reflectance comes from fnc_getCamouflageProperties.

THIS IS A DETECTABILITY COEFFICIENT, NOT AN ALBEDO, AND IT HAS NO VALID
BRIGHTNESS CONSUMER IN THIS REPOSITORY.  An earlier attempt to use it as
one was reverted.  The engine limit is recorded here so it is not hunted
again.

  - The engine NVG view (vision mode 1) is a client-side screen-space
    post-process.  It has no per-object NIR stage, so no engine path
    reads a per-soldier NIR value.
  - A brightness render is flat or absent.  setObjectTexture REPLACES
    the object's texture with one solid colour and destroys the uniform
    detail (rejected: the repository standard is "not flat").  There is
    no per-instance multiply.  setObjectMaterial swaps to a static rvmat,
    and the repository ships one rvmat (thermal/data/ti_fpn.rvmat, white,
    no darkening).  A per-soldier dim needs a set of darkened rvmats,
    which is an invented asset class.
  - The coefficient is not a brightness even in principle.  It is the
    MATCH to the vegetation background, so a white or snow uniform (a
    poor match) scores 0 exactly as a black uniform does.  Only the NIR
    albedo (fnc_getNirPerSelection, the signature the tube actually
    sees) would order white bright, black dark, vegetation mid.

The correct home for this coefficient is an AI-detection model (the
P_detect relation above).  This repository ships no such model.  The
function and fnc_getNirPerSelection are kept as the researched
detectability data with no runtime consumer.

Arguments:
  0: unit (OBJECT, default player)

Returns the detectability coefficient 0..1:
  1.0 = perfect blend (uniform NIR matches background)
  0.0 = maximum contrast (the black hole)
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { 0.0 };

private _camo = [_unit] call FUNC(getCamouflageProperties);
private _nirUniform = _camo select 1;

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

