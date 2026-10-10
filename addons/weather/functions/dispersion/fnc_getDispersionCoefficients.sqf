#include "..\..\script_component.hpp"

/*
Briggs rural (and urban) dispersion coefficients sigma_y and sigma_z.

Source: Briggs, G. A. (1973), "Diffusion Estimation for Small Emissions",
ATDL Contribution File No. 79, NOAA.  Rural formulae, downwind distance x
in metres.  The urban adjustment doubles sigma_y.

  Class  sigma_y                        sigma_z
  A      0.22 x (1+0.0001 x)^-0.5       0.20 x
  B      0.16 x (1+0.0001 x)^-0.5       0.12 x
  C      0.11 x (1+0.0001 x)^-0.5       0.08 x (1+0.0002 x)^-0.5
  D      0.08 x (1+0.0001 x)^-0.5       0.06 x (1+0.0015 x)^-0.5
  E      0.06 x (1+0.0001 x)^-0.5       0.03 x (1+0.0003 x)^-1
  F      0.04 x (1+0.0001 x)^-0.5       0.016 x (1+0.0003 x)^-1

Arguments:
  0: downwind distance x (NUMBER, m)
  1: stability class (STRING, "A".."F")
  2: urban (BOOL, default false)

Returns [sigma_y, sigma_z] in metres.
*/

params [
    ["_x", 0, [0]],
    ["_stability", "D", [""]],
    ["_urban", false, [true]]
];

private _dist = _x max 1;
private _syBase = sqrt (1 + 0.0001 * _dist);
private _sy = 0;
private _sz = 0;

if (_stability == "A") then {
    _sy = 0.22 * _dist / _syBase;
    _sz = 0.20 * _dist;
} else {
    if (_stability == "B") then {
        _sy = 0.16 * _dist / _syBase;
        _sz = 0.12 * _dist;
    } else {
        if (_stability == "C") then {
            _sy = 0.11 * _dist / _syBase;
            _sz = 0.08 * _dist / (sqrt (1 + 0.0002 * _dist));
        } else {
            if (_stability == "E") then {
                _sy = 0.06 * _dist / _syBase;
                _sz = 0.03 * _dist / (1 + 0.0003 * _dist);
            } else {
                if (_stability == "F") then {
                    _sy = 0.04 * _dist / _syBase;
                    _sz = 0.016 * _dist / (1 + 0.0003 * _dist);
                } else {
                    // D (default): the neutral class.
                    _sy = 0.08 * _dist / _syBase;
                    _sz = 0.06 * _dist / (sqrt (1 + 0.0015 * _dist));
                };
            };
        };
    };
};

// Urban surface roughness doubles the crosswind spread (Briggs 1973).
if (_urban) then { _sy = _sy * 2; };

[_sy, _sz]
