#include "..\..\script_component.hpp"

/*
Newmark sliding-block displacement for a coseismic landslide.

Newmark's rigid-block model treats a slope as a block on an inclined plane.
The block moves only while the earthquake acceleration exceeds the critical
acceleration a_c, and the accumulated downslope displacement is the double
integral of the excess acceleration.

Source: Newmark, N.M. (1965) "Effects of earthquakes on dams and
embankments", Geotechnique 15(2):139-160.  DOI 10.1680/geot.1965.15.2.139.

    a_c = (FS - 1) * g * sin(slope)

The displacement is estimated with the Ambraseys and Menu (1988) regression,
which needs only the ratio of critical to peak acceleration:

    log10 Dn = 0.90 + log10[ (1 - k)^2.53 * k^-1.09 ],   k = a_c / a_max

with Dn in centimetres.  Source: Ambraseys, N.N. and Menu, J.M. (1988)
"Earthquake-induced ground displacements", Earthquake Engineering and
Structural Dynamics 16(7):985-1006.  DOI 10.1002/eqe.4290160704.

The regression is fitted for roughly 0.1 <= k <= 0.9 (their data range).  The
kernel returns zero displacement for k >= 1 (the shaking never reaches the
critical acceleration, so the block never moves) and caps the result for
k <= 0 (the static factor of safety is at or below unity, so the slope has
already failed and the displacement is unbounded).

The critical slope angle the issue mentions is NOT used: the model is
displacement-based and the regression needs no threshold angle.  The trigger
flag reports a displacement above 1 mm.

Input:  [_slopeDeg, _pgaG, _staticFs] - slope angle (deg), peak ground
        acceleration (g), and the static factor of safety (dimensionless).
Output: [a_c (g), Dn (m), triggered]
Public: No
*/

params [
    ["_slopeDeg", 20, [0]],
    ["_pgaG", 0.2, [0]],
    ["_staticFs", 1.5, [0]]
];

// Critical acceleration in g: sin is in degrees in SQF.
private _acG = (_staticFs - 1) * (sin _slopeDeg);

private _dn = 0;
if (_pgaG > 0.001) then {
    private _k = _acG / _pgaG;
    if (_k <= 0) then {
        // Static factor of safety at or below 1: already unstable.
        _dn = 1;
    } else {
        if (_k < 1) then {
            private _dnCm = (10 ^ 0.90) * ((1 - _k) ^ 2.53) * (_k ^ -1.09);
            _dn = _dnCm / 100;
        };
    };
};

[_acG, _dn, _dn > 0.001]
