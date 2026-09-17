#include "..\script_component.hpp"

/*
Blast wave overpressure from Kingery-Bulmash (Swisdak 1994, ADA526744).

The previous model used a cubic law (P = 0.84·(W^(1/3)/Z)^3) that is wrong
by 2-17x: it OVERESTIMATES close in (Z=1: 840 kPa vs true 1357) and
UNDERESTIMATES far out (Z=10: 0.84 kPa vs true 14.8).  This implements the
simplified Kingery-Bulmash fits, verified against the published values.

Physics: scaled distance Z = R / W^(1/3) (m/kg^(1/3)); incident peak
overpressure P_so in kPa from the 3-piece Swisdak fit; positive-phase
duration t_d in ms from the 3-piece fit scaled by W^(1/3).

The coefficients are the metric Swisdak simplified KB fits (hemispherical
surface burst, TNT equivalent).  Reference anchors reproduced:
  Z=1.0 -> 1353.7 kPa    Z=2.0 -> 283.7 kPa
  Z=5.0 ->  43.2 kPa    Z=10.0 ->  14.9 kPa

Input:  [_massKg, _distanceM] - TNT-equivalent charge mass and standoff
Output: [P_so_kPa, t_d_ms]
*/

params [["_massKg", 1, [0]], ["_distanceM", 1, [0]]];

if (_massKg <= 0 || _distanceM <= 0) exitWith { [0, 0] };

private _w = _massKg ^ (1 / 3);
private _z = _distanceM / _w;

// ─── Incident overpressure (kPa) ─────────────────────────────────────────
// log-form fit: ln(P) = A + B·lnZ + C·(lnZ)^2 + ... evaluated as
// P = exp(A)·Z^B·exp(C·(lnZ)^2 ...) — done numerically for clarity.
private _lnZ = ln _z;
private _pSo = 0;
if (_z >= 0.2 && _z <= 2.9) then {
    _pSo = exp (7.2106 + (-2.1069 * _lnZ) + (-0.3229 * _lnZ * _lnZ)
        + (0.1117 * _lnZ * _lnZ * _lnZ) + (0.0685 * _lnZ * _lnZ * _lnZ * _lnZ));
} else {
    if (_z <= 23.8) then {
        _pSo = exp (7.5938 + (-3.0523 * _lnZ) + (0.40977 * _lnZ * _lnZ)
            + (0.0261 * _lnZ * _lnZ * _lnZ) + (-0.01267 * _lnZ * _lnZ * _lnZ * _lnZ));
    } else {
        if (_z <= 198.5) then {
            _pSo = exp (6.0536 + (-1.4066 * _lnZ));
        };
    };
};

// ─── Positive-phase duration (ms) ────────────────────────────────────────
private _td = 0;
if (_z >= 0.2 && _z <= 1.02) then {
    _td = _w * exp (0.5426 + (3.2299 * _lnZ) + (-1.5931 * _lnZ * _lnZ)
        + (-5.9667 * _lnZ * _lnZ * _lnZ) + (-4.0815 * _lnZ * _lnZ * _lnZ * _lnZ)
        + (-0.9149 * _lnZ * _lnZ * _lnZ * _lnZ * _lnZ));
} else {
    if (_z <= 2.8) then {
        _td = _w * exp (0.5440 + (2.7082 * _lnZ) + (-9.7354 * _lnZ * _lnZ)
            + (14.3425 * _lnZ * _lnZ * _lnZ) + (-9.7791 * _lnZ * _lnZ * _lnZ * _lnZ)
            + (2.8535 * _lnZ * _lnZ * _lnZ * _lnZ * _lnZ));
    } else {
        if (_z <= 40) then {
            _td = _w * exp (-2.4608 + (7.1639 * _lnZ) + (-5.6215 * _lnZ * _lnZ)
                + (2.2711 * _lnZ * _lnZ * _lnZ) + (-0.44994 * _lnZ * _lnZ * _lnZ * _lnZ)
                + (0.03486 * _lnZ * _lnZ * _lnZ * _lnZ * _lnZ));
        };
    };
};

[_pSo, _td]
