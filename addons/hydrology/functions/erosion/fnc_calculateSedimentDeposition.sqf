#include "..\..\script_component.hpp"
/*
Slope-break sediment deposition (issue #21).

Eroded soil does not travel the whole hillslope. Where the gradient falls
off, the flow slows and the coarse load drops out. The RUSLE treats the
break as the end of the slope length, and the deposition fraction at the
break is the share of the arriving load retained there.

Rule: a break deposits when the downslope gradient is less than half the
upslope gradient.

The 0.5 gradient ratio is the published NRCS rule of thumb for where
deposition begins: "if no signs of deposition are present on a concave slope,
assume that deposition begins at the location where the steepness is 1/2 of
the average steepness of the concave area" (NRCS-USDA Technical Guide to
RUSLE use in Michigan, LS factor).  The retained fraction depends on the
particle sizes and the flow, so it is the caller's parameter; the default
0.5 is the caller-overridable scenario value.

Args:
  0: upslope gradient (NUMBER, rise/run m/m, default 0)
  1: downslope gradient (NUMBER, rise/run m/m, default 0)
  2: retained fraction at a break (NUMBER, 0..1, default 0.5)

Returns the fraction of the arriving sediment load deposited at the break,
0 when the flow carries on down a continuous slope.

Example:
  [0.10, 0.02] call aee_hydrology_fnc_calculateSedimentDeposition -> 0.5
*/

params [
    ["_upslopeGradient", 0, [0]],
    ["_downslopeGradient", 0, [0]],
    ["_retention", 0.5, [0]]
];

if !(_upslopeGradient isEqualType 0) then { _upslopeGradient = 0; };
if !(_downslopeGradient isEqualType 0) then { _downslopeGradient = 0; };
if !(_retention isEqualType 0) then { _retention = 0.5; };
_retention = _retention max 0 min 1;

private _isBreak = _downslopeGradient < (0.5 * _upslopeGradient);

if (_isBreak) exitWith { _retention };
0
