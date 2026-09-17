#include "..\script_component.hpp"
/*
Get the world's latitude from CfgWorlds, hemisphere-preserved.

The mod had three separate latitude reads with inconsistent handling:
solar and biome used `abs`, space weather used the raw signed value.
That split is a bug class (issue #154 pattern 3): a map that publishes a
Southern-hemisphere sign (e.g. Scottish Highlands sets latitude = -56.702)
inverted seasons in solar until the abs() fix, and any consumer using the
raw sign gets a DIFFERENT magnitude than one using abs.

This is the single source of truth.  It returns the signed value as
published, AND a magnitude so consumers choose the meaning they need:

  [signedDeg, magnitudeDeg]

  - Solar elevation and biome classification want MAGNITUDE (the sun's
    max elevation and Köppen temperature bands depend on |lat|, and the
    season comes from the declination term, not the sign).
  - Coriolis deflection wants the SIGNED value (the deflection direction
    flips across the equator).

The published value is usually the hemisphere-correct sign already
(positive north, negative south).  The magnitude is always abs().

Input:  none
Output: [signedLatDeg, magnitudeDeg] — both scalars
*/

private _signed = getNumber (configFile >> "CfgWorlds" >> worldName >> "latitude");
if !(_signed isEqualType 0) then { _signed = 40; };  // untyped -> temperate default
if (_signed == 0) then { _signed = 40; };

[_signed, abs _signed]
