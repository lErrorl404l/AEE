#include "..\script_component.hpp"
/*
Vertical sound-speed profile of the sea (issue #113).

The profile is built from a piecewise-linear temperature profile through the
Mackenzie (1981) equation (fnc_calculateSoundSpeedWater, JASA 70(3):807-812,
DOI 10.1121/1.386920):

    T(0)                 = surface temperature   (mixed layer)
    T(thermoclineDepth)  = deep temperature      (base of the thermocline)
    T(maxDepth)          = deep temperature      (isothermal deep layer)

Temperature falls linearly from the surface to the thermocline base, then
holds at the deep temperature.  Salinity is uniform.  Sound speed at each
sample depth follows from Mackenzie with that temperature, the salinity and
the depth.

In the thermocline the temperature falls with depth, so sound speed falls
with depth (a negative gradient).  Rays bend toward the slower speed, so
they bend downward through the thermocline.  The profile is the input to
fnc_calculateSoundChannel and fnc_calculateShadowZone.

Input:  [surfaceTemp, thermoclineDepth, deepTemp, salinity, maxDepth, samples]
          surfaceTemp      degC
          thermoclineDepth m (base of the mixed layer)
          deepTemp         degC (isothermal layer below the thermocline)
          salinity         psu
          maxDepth         m (bottom of the profile)
          samples          number of layers (>= 2)
Output: array of [depth, c] pairs, sorted by depth
*/

params [
    ["_surfaceTemp", 20, [0]],
    ["_thermoclineDepth", 100, [0]],
    ["_deepTemp", 4, [0]],
    ["_salinity", 35, [0]],
    ["_maxDepth", 4000, [0]],
    ["_samples", 21, [0]]
];

private _n = 2 max (round _samples);
private _thermo = 1 max _thermoclineDepth;
private _profile = [];

for "_i" from 0 to (_n - 1) do {
    private _z = (_maxDepth * _i) / (_n - 1);
    private _T = if (_z <= _thermo) then {
        _surfaceTemp + ((_deepTemp - _surfaceTemp) * (_z / _thermo))
    } else {
        _deepTemp
    };
    private _c =
          1448.96
        + 4.591 * _T
        - 5.304e-2 * _T ^ 2
        + 2.374e-4 * _T ^ 3
        + 1.340 * (_salinity - 35)
        + 1.630e-2 * _z
        + 1.675e-7 * _z ^ 2
        - 1.025e-2 * _T * (_salinity - 35)
        - 7.139e-13 * _T * _z ^ 3;
    _profile pushBack [_z, _c];
};

_profile
