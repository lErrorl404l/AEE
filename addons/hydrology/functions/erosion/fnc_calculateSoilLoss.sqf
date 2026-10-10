#include "..\..\script_component.hpp"
/*
RUSLE soil loss A (issue #21).

The Revised Universal Soil Loss Equation predicts the long-term average
annual soil loss:

  A = R * K * LS * C * P

  R   rainfall erosivity        MJ*mm/(ha*h)      (annual sum of EI30)
  K   soil erodibility          t*ha*h/(ha*MJ*mm)
  LS  slope length-gradient     dimensionless
  C   cover-management          dimensionless
  P   support practice          dimensionless

At the unit plot (bare fallow, 22.13 m, 9 percent slope) LS = C = P = 1,
so A reduces to R * K. The result is in tonnes per hectare per year
(t/ha/yr).

Source: Wischmeier and Smith (1978) USDA Agriculture Handbook 537;
Renard et al. (1997) USDA Agriculture Handbook 703.

The event form uses the storm EI30 for R. P is 1.0 for wild terrain: no
support practice is applied to natural ground. Where a practice exists,
the standard contouring factors are 0.6 (1-2 percent), 0.5 (3-8 percent),
0.6 (9-12 percent), 0.7 (13-16 percent), 0.8 (17-20 percent); strip
cropping is 0.25-0.40 and terraces 0.5-1.0 (AH-703 chapter 6).

Args:
  0: R (NUMBER, default 0)
  1: K (NUMBER, default 0)
  2: LS (NUMBER, default 0)
  3: C (NUMBER, default 1)
  4: P (NUMBER, default 1)

Returns A in t/ha/yr.

Example:
  [180, 0.32, 1, 1, 1] call aee_hydrology_fnc_calculateSoilLoss -> 57.6
*/

params [
    ["_r", 0, [0]],
    ["_k", 0, [0]],
    ["_ls", 0, [0]],
    ["_c", 1, [0]],
    ["_p", 1, [0]]
];

if !(_r isEqualType 0) then { _r = 0; };
if !(_k isEqualType 0) then { _k = 0; };
if !(_ls isEqualType 0) then { _ls = 0; };
if !(_c isEqualType 0) then { _c = 1; };
if !(_p isEqualType 0) then { _p = 1; };

(_r max 0) * (_k max 0) * (_ls max 0) * (_c max 0) * (_p max 0)
