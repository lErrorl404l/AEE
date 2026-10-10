#include "..\..\script_component.hpp"

/*
Hopkinson-Cranz cube-root blast scaling.

For one explosive, geometry and medium the scaled distance R / W^(1/3) is
constant at the same overpressure, so

    D1 / D2 = (W1 / W2)^(1/3)

where D is a crater dimension (radius, diameter or depth) and W is the
TNT-equivalent charge mass.  Basis: the charge radius scales as W^(1/3) and
blast similarity gives the same overpressure at the same scaled distance.
Holds from microtons to megatons (Swisdak 1975).

Sources: Hopkinson (1915); Cranz (1926); Swisdak (1975).

Honest limit: the cube root breaks when gravity or strength dominates.  A
buried charge scales as W^0.3 (Chabai 1973, 0.296 +/- 0.024).  Use the 1/3.4
exponent for large or heavy charges (Violet 1961).  The cube root is adequate
under about 100 lb of TNT.

Input:  [_refMassKg, _refDimensionM, _massKg] - a known (mass, dimension)
        pair and the new charge mass.
Output: the scaled dimension in metres (0 when an argument is non-positive).
Public: No
*/

params [["_refMassKg", 1, [0]], ["_refDimensionM", 1, [0]], ["_massKg", 1, [0]]];

if (_refMassKg <= 0 || _refDimensionM <= 0 || _massKg <= 0) exitWith { 0 };

_refDimensionM * ((_massKg / _refMassKg) ^ (1 / 3))
