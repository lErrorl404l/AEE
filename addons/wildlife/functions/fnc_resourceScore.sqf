#include "..\script_component.hpp"

/*
Resource suitability kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Scores one
candidate point for one animal.  A point is best when it is close and the
wanted resource is strong.  The animal picks the highest score among the ring
points the resource search walks.

The search range is the distance a grazing animal will walk to a resource.
Mule deer in northern California stayed 1.19 to 1.55 km from water with a
mean maximum of 2.46 km (Boroski and Mossman, as cited in the mule deer
water literature), so the range is taken as the 1.2 km lower figure: a point
at that distance scores zero and the animal prefers a nearer one.

Arguments:
  0: Number - the distance to the point, metres
  1: Number - the water proximity at the point, 0 to 1
  2: Number - the vegetation score at the point, 0 to 1
  3: Bool   - true when the animal wants water, false for food

Returns:
  Number - the suitability, 0 to 1
*/

params [
    ["_distance", 0, [0]],
    ["_waterProximity", 0, [0]],
    ["_vegScore", 0, [0]],
    ["_wantWater", false, [false]]
];

private _range = 1200;   // m, the measured deer-to-water distance
private _strength = _vegScore;
if (_wantWater) then {
    _strength = _waterProximity;
};

private _near = 1 - ((_distance / _range) min 1);
private _score = (_strength * _near);

((_score max 0) min 1)
