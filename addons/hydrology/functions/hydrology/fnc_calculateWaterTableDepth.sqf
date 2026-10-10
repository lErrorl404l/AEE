#include "..\..\script_component.hpp"
/*
Water-table depth from aquifer storage (issue #26).

The groundwater store GVAR(groundwaterStore_mm) is a depth of water, not a
height.  To turn it into a water-table depth the mod uses the water-table
fluctuation method, the standard way a storage change is read as a head
change:

  dS = S_y * dh            a storage change fills the drainable pores
  dh = dS / S_y            the head rise for that storage change

S is the stored water depth (mm) and S_y the specific yield.  The water table
sits at the reference depth when the store is empty and rises by dh as the
store fills, so:

  head_m  = store_mm / (1000 * S_y)
  depth_m = referenceDepth_m - head_m

The depth is clamped at zero: the water table cannot rise above the ground
surface.  This is a pure conversion, so the store's own recession is the
linear reservoir in fnc_calculateBaseflow (issue #24), reused rather than
reimplemented.

Source: Meinzer, O.E. (1923), "The occurrence of groundwater in the United
States", USGS Water-Supply Paper 489.  Healy, R.W. and Cook, P.G. (2002),
"Using groundwater levels to estimate recharge", Hydrogeology Journal
10:91-109 (the water-table fluctuation method).

Args:
  0: aquifer store (NUMBER, mm, default 0)
  1: specific yield S_y (NUMBER, 0..0.3, default 0.1)
  2: reference depth, the depth at zero store (NUMBER, m, default 3)

Returns [waterTableDepth_m, head_m].
*/

params [
    ["_store", 0, [0]],
    ["_specificYield", 0.1, [0]],
    ["_referenceDepth", 3, [0]]
];

if !(_store isEqualType 0) then { _store = 0; };
if !(_specificYield isEqualType 0) then { _specificYield = 0.1; };
if !(_referenceDepth isEqualType 0) then { _referenceDepth = 3; };
_store = _store max 0;
// A zero or negative specific yield would divide by zero.  The floor is a
// near-impervious lithology: the water table tracks the store almost 1:1.
_specificYield = _specificYield max 0.01;
_referenceDepth = _referenceDepth max 0;

private _headM = _store / (1000 * _specificYield);
private _depthM = (_referenceDepth - _headM) max 0;

[_depthM, _headM]
