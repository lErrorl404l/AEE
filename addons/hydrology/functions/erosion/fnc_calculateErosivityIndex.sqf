#include "..\..\script_component.hpp"
/*
Storm erosivity index EI30 (RUSLE R-factor building block, issue #21).

The R factor of the RUSLE is the annual sum of the storm erosivity index.
For one storm the index is the storm kinetic energy times the maximum
30-minute intensity, scaled by the conventional factor:

  EI30 = E * I30 / 100

E is the total storm kinetic energy in MJ/ha (the per-millimetre energy
from fnc_calculateKineticEnergy times the storm depth), and I30 is the
maximum 30-minute rainfall intensity in mm/h. The result is in
MJ*mm/ha/h, the unit of the R factor.

Source: Wischmeier and Smith (1978) USDA Agriculture Handbook 537; Renard
et al. (1997) USDA Agriculture Handbook 703, chapter 2.

Args:
  0: storm kinetic energy E (NUMBER, MJ/ha, default 0)
  1: maximum 30-minute intensity I30 (NUMBER, mm/h, default 0)

Returns EI30 in MJ*mm/ha/h.

Example:
  [1000, 50] call aee_hydrology_fnc_calculateErosivityIndex -> 500
*/

params [["_energy", 0, [0]], ["_i30", 0, [0]]];

if !(_energy isEqualType 0) then { _energy = 0; };
if !(_i30 isEqualType 0) then { _i30 = 0; };

((_energy max 0) * (_i30 max 0)) / 100
