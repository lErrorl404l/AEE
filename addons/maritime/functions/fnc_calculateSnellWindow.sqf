#include "..\script_component.hpp"
/*
Snell window for a view from under the surface (issue #14).

From under the water the whole sky is compressed into a cone.  At the cone
edge the refracted ray from the horizon becomes horizontal.  The edge is
the critical angle of total internal reflection:

    sin(theta_c) = n_air / n_water = 1 / n_water

The refractive index of seawater at visible wavelengths is 1.34 to 1.35
(Austin and Halikas 1976, SIO Reference 76-1).  Pure water is 1.333.  The
default here is 1.333, which matches the issue value and gives the classic
48.6 degree window.  At n = 1.333:

    sin(theta_c) = 0.750,  theta_c = 48.6 degrees

The full cone is twice the critical angle, 97.2 degrees.  The angle does
not depend on depth.  Outside the cone the water surface acts as a mirror
and shows the underwater scene.

Input:  [_nWater] - refractive index of the water (default 1.333)
Output: [criticalAngleDeg, coneDeg]
*/

params [["_nWater", 1.333, [0]]];

if (_nWater <= 1) exitWith { [90, 180] };

private _critDeg = asin (1 / _nWater);
[_critDeg, _critDeg * 2]
