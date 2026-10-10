#include "..\script_component.hpp"
/*
Snell's law at a sound-speed layer boundary (issue #113).

Urick, "Principles of Underwater Sound", 3rd ed., McGraw-Hill 1983,
ISBN 0-07-066087-5, ch. 6.  The ray invariant across a horizontally
stratified medium is

    cos(theta) / c = constant

with theta the grazing angle measured from the horizontal and c the local
sound speed.  Across a boundary from layer 1 to layer 2:

    cos(theta2) = (c2 / c1) * cos(theta1)

A ray bends TOWARD the slower sound speed.  When c2 < c1, cos(theta2) is
smaller than cos(theta1), so theta2 is larger: the ray steepens.  In a
negative gradient (sound speed falling with depth) a downward ray therefore
bends downward.

Total internal reflection.  When (c2 / c1) * cos(theta1) reaches or exceeds
1, no real angle satisfies the relation: the ray turns and reflects back.
This is the turning point that defines a shadow zone.

Input:  [theta1, c1, c2]
          theta1  grazing angle in layer 1, degrees (0 = horizontal)
          c1      sound speed in layer 1, m/s
          c2      sound speed in layer 2, m/s
Output: [theta2, turned]
          theta2  grazing angle in layer 2, degrees
          turned  true when the boundary is a turning point
*/

params [
    ["_theta1", 0, [0]],
    ["_c1", 1500, [0]],
    ["_c2", 1500, [0]]
];

if (_c1 <= 0 || _c2 <= 0) exitWith { [0, false] };

private _cosT2 = (_c2 / _c1) * (cos _theta1);

if ((abs _cosT2) >= 1) exitWith { [90, true] };

[(acos _cosT2), false]
