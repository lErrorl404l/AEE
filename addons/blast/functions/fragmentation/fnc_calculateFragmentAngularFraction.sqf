#include "..\..\script_component.hpp"

/*
Fragment angular distribution (Gurney, BRL Report 405, 1943; Mott 1943).

Grenade body (isotropic sphere): fragments spread uniformly over the sphere.
The differential fraction landing in a band d_theta at polar angle theta
(measured from the vertical) is:

  f(theta) * d_theta = sin(theta) * d_theta / 2

so 50% fall within +/-30 degrees of the horizontal (theta 60 to 120 degrees).

Cylinder (artillery shell): fragments concentrate in the equatorial band.  The
shape is a Gaussian about theta = 90 degrees with spread sigma, truncated to
50-120 degrees:

  f(theta) = exp(-(theta - 90)^2 / (2 * sigma^2))

Input:  [_thetaDeg, _dThetaDeg, _geometry, _sigmaDeg]
Output: isotropic: band fraction.  cylinder: relative weight (peak 1 at the
        equator).  theta is in degrees from the vertical.
*/
params [
    ["_thetaDeg", 90, [0]],
    ["_dThetaDeg", 1, [0]],
    ["_geometry", "isotropic", [""]],
    ["_sigmaDeg", 17.5, [0]]
];

if (_geometry == "cylinder") exitWith {
    exp (-((_thetaDeg - 90) * (_thetaDeg - 90)) / (2 * _sigmaDeg * _sigmaDeg))
};

// SQF sin takes degrees, so sin(_thetaDeg) is the sine of the polar angle.
// The band width converts to radians: the isotropic band fraction is
// sin(theta) * dtheta / 2 with dtheta in radians.
private _dThetaRad = _dThetaDeg * (pi / 180);
(sin _thetaDeg) * _dThetaRad / 2
