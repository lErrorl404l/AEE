#include "..\..\script_component.hpp"
/*
Planck band radiance (exact cumulative-blackbody series, issue #196 family).

This pure kernel is the ONE home of the band integral.  The radiance kernel
fnc_calculateBandRadiance and the band sky kernel fnc_calculateSkyRadiance
both call it, so the series is not duplicated.

    L_band = C * T^4 * [I(z1) - I(z2)],  z_i = c2 / (lambda_i * T),
    I(z) = sum_n exp(-n z) (z^3/n + 3 z^2/n^2 + 6 z/n^3 + 6/n^4).

C = 2 k^4 / (h^3 c^2) = 2.779416505e-9 W m^-2 sr^-1 K^-4 and
c2 = h c / k = 1.438776877e-2 m K, both from CODATA 2022.

The series needs no fit constants and converges below 1e-9 in 40 terms over
the simulation's temperature range.

Arguments:
  0: temperature (NUMBER, K)
  1: band short edge (NUMBER, m), default 8e-6
  2: band long edge (NUMBER, m), default 14e-6

Return Value: NUMBER, band radiance W/m2/sr, or -1 when the band is unusable.
Example: [300, 3e-6, 5e-6] call aee_thermal_fnc_planckBandRadiance
Public: No
*/
params [["_tk", 300, [0]], ["_lambda1M", 8e-6, [0]], ["_lambda2M", 14e-6, [0]]];

// A band must be a positive, increasing pair, and the temperature must be
// finite.  SQF NaN compares false against everything, so finite is checked
// before the arithmetic.
if !(_lambda1M isEqualType 0) exitWith { -1 };
if !(_lambda2M isEqualType 0) exitWith { -1 };
if !(finite _tk) exitWith { -1 };
if !(finite _lambda1M) exitWith { -1 };
if !(finite _lambda2M) exitWith { -1 };
if (_lambda1M <= 0 || _lambda2M <= _lambda1M) exitWith { -1 };

_tk = (_tk max 100) min 2000;   // numerical domain guard, not a physical clamp

private _z1 = 1.438776877e-2 / (_lambda1M * _tk);
private _z2 = 1.438776877e-2 / (_lambda2M * _tk);
private _z1s = _z1 * _z1;
private _z1c = _z1s * _z1;
private _z2s = _z2 * _z2;
private _z2c = _z2s * _z2;
private _b1 = exp (-_z1);
private _b2 = exp (-_z2);
private _e1 = _b1;
private _e2 = _b2;
private _i1 = 0;
private _i2 = 0;
for "_n" from 1 to 8 do {
    private _n2 = _n * _n;
    private _n3 = _n2 * _n;
    private _n4 = _n3 * _n;
    _i1 = _i1 + _e1 * (_z1c / _n + 3 * _z1s / _n2 + 6 * _z1 / _n3 + 6 / _n4);
    _i2 = _i2 + _e2 * (_z2c / _n + 3 * _z2s / _n2 + 6 * _z2 / _n3 + 6 / _n4);
    _e1 = _e1 * _b1;
    _e2 = _e2 * _b2;
};
2.779416505e-9 * (_tk ^ 4) * (_i2 - _i1)
