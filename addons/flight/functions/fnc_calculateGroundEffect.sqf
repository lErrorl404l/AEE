#include "..\script_component.hpp"

/*
Ground-effect reduction of induced drag (issue #22).

Within about one wingspan of the ground the wing's trailing vortices are
suppressed, so the induced drag falls.  The FAA Airplane Flying Handbook gives
the empirical reduction against the height-to-wingspan ratio h/b:

  h/b     induced-drag reduction
  0.1     50 percent
  0.25    40 percent
  0.5     25 percent
  1.0     10 percent

The curve is linear between those points and is clamped to 50 percent at or
below h/b = 0.1.  Above one wingspan the airframe is in free air and the
reduction is zero.

Source: FAA Airplane Flying Handbook (FAA-H-8083-3), ground effect.  The
McCormick vortex model, CDi_GE = CDi * (1 - 1/(1 + 16 (h/b)^2)), is the
analytic alternative.  It overpredicts (86 percent at h/b = 0.1) and is not
used here.

This is a pure kernel.

Arguments:
  0: NUMBER - height above ground, metres
  1: NUMBER - wingspan, metres

Return Value: NUMBER - induced-drag reduction fraction, 0 .. 0.5
Example: [5, 10] call aee_flight_fnc_calculateGroundEffect
Public: No
*/

params [
    ["_heightAglM", 0, [0]],
    ["_wingspanM", 0, [0]]
];

if (_wingspanM <= 0) exitWith { 0 };

private _ratio = (_heightAglM max 0) / _wingspanM;
if (_ratio > 1.0) exitWith { 0 };

// Piecewise-linear through the FAA points.
private _reduction = 0.10;
if (_ratio <= 0.1) then {
    _reduction = 0.50;
} else {
    if (_ratio <= 0.25) then {
        _reduction = 0.50 + (0.40 - 0.50) * ((_ratio - 0.1) / 0.15);
    } else {
        if (_ratio <= 0.5) then {
            _reduction = 0.40 + (0.25 - 0.40) * ((_ratio - 0.25) / 0.25);
        } else {
            _reduction = 0.25 + (0.10 - 0.25) * ((_ratio - 0.5) / 0.5);
        };
    };
};

_reduction min 0.5 max 0
