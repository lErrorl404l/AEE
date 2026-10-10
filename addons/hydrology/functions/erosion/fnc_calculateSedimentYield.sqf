#include "..\..\script_component.hpp"
/*
Event sediment yield, MUSLE (issue #21).

The RUSLE is an annual-average model. For a single storm the Modified
Universal Soil Loss Equation replaces the rainfall-erosivity term R with a
runoff term, which makes it event-scale and directly usable from the
mod's own runoff chain:

  Sed = 11.8 * (Q * qp)^0.56 * K * LS * C * P

  Q   event runoff volume        m3
  qp  peak runoff rate           m3/s
  K, LS, C, P as in the RUSLE

Sed is in metric tonnes. The coefficient 11.8 and the exponent 0.56 are
Williams' (1975) fitted values (USDA ARS-S-40), reproduced in Renard et
al. (1997) AH-703 chapter 4.

Args:
  0: Q, event runoff volume (NUMBER, m3, default 0)
  1: qp, peak runoff rate (NUMBER, m3/s, default 0)
  2: K (NUMBER, default 0)
  3: LS (NUMBER, default 0)
  4: C (NUMBER, default 1)
  5: P (NUMBER, default 1)

Returns the sediment yield in metric tonnes.

Example:
  [1000, 2, 0.30, 1.79, 0.36, 1] call aee_hydrology_fnc_calculateSedimentYield
*/

params [
    ["_q", 0, [0]],
    ["_qp", 0, [0]],
    ["_k", 0, [0]],
    ["_ls", 0, [0]],
    ["_c", 1, [0]],
    ["_p", 1, [0]]
];

if !(_q isEqualType 0) then { _q = 0; };
if !(_qp isEqualType 0) then { _qp = 0; };
if !(_k isEqualType 0) then { _k = 0; };
if !(_ls isEqualType 0) then { _ls = 0; };
if !(_c isEqualType 0) then { _c = 1; };
if !(_p isEqualType 0) then { _p = 1; };

private _qQp = (_q max 0) * (_qp max 0);

11.8 * (_qQp ^ 0.56) * (_k max 0) * (_ls max 0) * (_c max 0) * (_p max 0)
