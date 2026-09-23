#include "..\..\script_component.hpp"
/*
Rainfall runoff by the SCS Curve Number method (issue #24).

The mod had a Nash cascade for river level and nothing to feed it a
runoff depth. A catchment converts rainfall to runoff through the soil's
infiltration capacity, and the Curve Number is the standard operational
way to express that capacity from the soil group and land cover.

  S  = 25400 / CN - 254        potential maximum retention, mm
  Ia = 0.2 * S                 initial abstraction (interception, fill)
  Q  = (P - Ia)^2 / (P + 0.8S) when P > Ia, else 0

Source: USDA NRCS TR-55 (1986), "Urban Hydrology for Small Watersheds",
chapter 1 and 2. The relationship is the SCS (now NRCS) rainfall-runoff
equation, the form with the 0.2 initial-abstraction ratio.

The curve number comes from the soil group and the land cover, not from a
map name. The material classifier already resolves the surface, and the
antecedent moisture comes from the mod's own soil state, so a wet soil
raises the number the way a real catchment does (this is the standard
CN adjustment toward group III conditions):

  CN_III = CN_II / (0.427 + 0.00573 * CN_II)

Args:
  0: rain (NUMBER, mm over the interval)
  1: curve number CN_II (NUMBER, 30..98, default 75)
  2: antecedent moisture (NUMBER, 0..1, default 0.2)

Returns the runoff depth in mm.
*/

params [["_rain", 0, [0]], ["_cn", 75, [0]], ["_moisture", 0.2, [0]]];

if (_rain <= 0) exitWith { 0 };
if !(_cn isEqualType 0) then { _cn = 75; };
if !(_moisture isEqualType 0) then { _moisture = 0.2; };

// Antecedent moisture: a wet catchment runs off more. Dry soil (below
// 0.3 of the range) uses group I, wet (above 0.5) uses group III, and the
// published conversion for group III is applied. Group I is the mirror,
// CN_I = CN_II / (2.281 - 0.01281 * CN_II), from the same table.
if (_moisture >= 0.5) then {
    _cn = _cn / (0.427 + (0.00573 * _cn));
} else {
    if (_moisture < 0.3) then {
        _cn = _cn / (2.281 - (0.01281 * _cn));
    };
};
_cn = _cn max 30 min 99;

private _s = (25400 / _cn) - 254;
private _ia = 0.2 * _s;

// Below the initial abstraction nothing runs off: the soil and the
// surface store take it all.
if (_rain <= _ia) exitWith { 0 };

((_rain - _ia) ^ 2) / (_rain + (0.8 * _s))
