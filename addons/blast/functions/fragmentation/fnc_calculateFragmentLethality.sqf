#include "..\..\script_component.hpp"

/*
Fragment lethality from kinetic energy (Henderson, DTIC ADA532158).

Henderson's curve gives the probability of a lethal wound from a fragment's
kinetic energy E = 0.5 * m * v^2:

  E =  79 J  -> 31% lethal
  E = 103 J  -> 50% lethal
  E = 200 J  -> 90% lethal

Below 79 J the wound is not lethal.  The function is piecewise linear between
the anchors, and the 103-200 J slope is extended above 200 J.  The result is
clamped to [0, 1].

Input:  [_fragmentMassKg, _velocity]
Output: lethal-wound probability (0-1)
*/
params [
    ["_fragmentMassKg", 0.001, [0]],
    ["_velocity", 500, [0]]
];

if (_fragmentMassKg <= 0) exitWith { 0 };

private _energy = 0.5 * _fragmentMassKg * _velocity * _velocity;
private _p = 0;
if (_energy >= 200) then {
    _p = 0.90 + ((_energy - 200) * (0.40 / 97));
} else {
    if (_energy >= 103) then {
        _p = 0.50 + ((_energy - 103) * (0.40 / 97));
    } else {
        if (_energy >= 79) then {
            _p = 0.31 + ((_energy - 79) * (0.19 / 24));
        };
    };
};
_p min 1 max 0
