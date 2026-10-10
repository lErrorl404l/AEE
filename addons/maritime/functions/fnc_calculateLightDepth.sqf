#include "..\script_component.hpp"
/*
Depth at which a given fraction of the surface light remains (issue #14).

The inverse of the Beer-Lambert law:

    T(z) = exp(-Kd * z)
    z(T) = -ln(T) / Kd = ln(1 / T) / Kd

The common anchor is the 1 percent light depth, T = 0.01:

    z_1pct = ln(100) / Kd = 4.605 / Kd

A clear Jerlov I water (Kd 0.04 m^-1) puts the 1 percent depth at 115 m.

Input:  [_kd, _fraction]
          _kd       - diffuse attenuation coefficient (m^-1)
          _fraction - remaining light fraction, 0 < _fraction < 1 (default 0.01)
Output: depth in metres.  Zero when the input is out of range.
*/

params [
    ["_kd", 0, [0]],
    ["_fraction", 0.01, [0]]
];

if (_kd <= 0 || _fraction <= 0 || _fraction >= 1) exitWith { 0 };

(ln (1 / _fraction)) / _kd
