#include "..\..\script_component.hpp"

/*
Camera-shake strength and duration for an earthquake.

Duration: the shaking lasts about as long as the fault ruptures.  The rupture
duration is the fault length divided by the rupture velocity:

    log10 L[km] = -2.44 + 0.59*M        (all fault types)
    t_r = L / Vr,   Vr ~ 0.8 * Vs

Source for the length-magnitude relation: Wells, D.L. and Coppersmith, K.J.
(1994) "New empirical relationships among magnitude, rupture length, rupture
width, rupture area, and surface displacement", Bulletin of the Seismological
Society of America 84(4):974-1002.  DOI 10.1785/BSSA0840040974.  The rupture
velocity as a fraction of the shear-wave velocity is the standard Brune (1970)
value; 2.8 km/s is used.

The issue's ladder M5 = 5 s, M6 = 15 s, M7 = 30 s, M8 = 60 s has no published basis and
is not used.  The length-magnitude relation gives about 9 s at M6.5 and about
18 s at M7.

Power: the engine addCamShake power is a 0-20 unitless strength with no
physical meaning.  The physical input is the published shaking severity, so
the power is derived from the Worden et al. (2012) Modified Mercalli
intensity (fnc_seismicIntensity) on the engine's fixed 0-20 scale:

    power = 20 * (MMI - 1) / 9

MMI 1 (imperceptible) maps to 0 and MMI 10 maps to 20; the expression is
clamped to the engine's 0-20 range.  The mapping is an explicit engine
calibration; the intensity it reads is the published quantity.

Input:  [_pgaG, _magnitude] - peak ground acceleration (g) and moment
        magnitude.
Output: [power, durationS] - addCamShake power (0-20) and shake duration (s).
Public: No
*/

params [
    ["_pgaG", 0.2, [0]],
    ["_magnitude", 6.5, [0]]
];

private _lengthKm = 10 ^ (-2.44 + 0.59 * _magnitude);
private _durationS = _lengthKm / 2.8;

private _powerRaw = 20 * ((([_pgaG] call FUNC(seismicIntensity)) - 1) / 9);
private _power = (_powerRaw min 20) max 0;

[_power, _durationS]
