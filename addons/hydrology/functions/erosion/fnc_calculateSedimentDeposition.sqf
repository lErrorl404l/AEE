#include "..\..\script_component.hpp"
/*
Slope-break sediment deposition (issue #21).

Eroded soil does not travel the whole hillslope. Where the gradient falls
off, the flow slows and the coarse load drops out. The RUSLE treats the
break as the end of the slope length, and the deposition fraction at the
break is the share of the arriving load retained there.

Rule (issue #21, "Sediment Delivery and Deposition"): a break deposits when
the downslope gradient is less than half the upslope gradient, or the
downslope gradient is below 2 percent. The retained fraction is 50 to 90
percent at a break.

The 2 percent threshold and the 0.5 gradient ratio are the issue's stated
rule. The exact retention curve between 50 and 90 percent is UNSOURCED:
no primary was found, so the retained fraction is a parameter with a
conservative default of 0.5 (the low end of the stated range).

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

private _isBreak = (_downslopeGradient < (0.5 * _upslopeGradient)) || (_downslopeGradient < 0.02);

if (_isBreak) exitWith { _retention };
0
