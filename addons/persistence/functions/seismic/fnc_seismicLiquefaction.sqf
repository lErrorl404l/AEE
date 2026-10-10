#include "..\..\script_component.hpp"

/*
Liquefaction potential from the Seed-Idriss simplified procedure.

Saturated loose sand loses strength when the cyclic stress ratio (CSR)
imposed by the shaking exceeds its cyclic resistance ratio (CRR).  The
procedure computes the factor of safety FS = CRR / CSR; liquefaction is
expected where FS < 1.

Sources:
  Seed, H.B. and Idriss, I.M. (1971) "Simplified procedure for evaluating
  soil liquefaction potential", Journal of the Soil Mechanics and Foundations
  Division, ASCE 97(SM9):1249-1273.
  Youd, T.L., Idriss, I.M. et al. (2001) "Liquefaction resistance of soils:
  summary report from the 1996 NCEER and 1998 NCEER/NSF workshops on
  evaluation of liquefaction resistance of soils", Journal of Geotechnical
  and Geoenvironmental Engineering 127(4):297-313.
  DOI 10.1061/(ASCE)1090-0241(2001)127:4(297).

    CSR      = 0.65 * (sigma_v / sigma_v') * (a_max / g) * rd
    rd       = 1.000 - 0.00765*z            z <= 9.15 m
    rd       = 1.174 - 0.0267*z             9.15 < z <= 23 m
    CRR7.5   = 1/(34 - (N1)60) + (N1)60/135
               + 50 / (10*(N1)60 + 45)^2 - 1/200     (clean sand, (N1)60 < 30)
    MSF      = 10^2.24 / M^2.56             (Youd and Noble 1997)
    CRR      = CRR7.5 * MSF * K_sigma
    FS       = CRR / CSR

The overburden stress sigma_v uses a moist total unit weight of 20 kN/m^3 and
the pore pressure uses the supplied water-table depth.  K_sigma is set to 1,
which is exact for sigma_v' <= 100 kPa (about 10 m of soil); deeper layers are
not modelled.  The (N1)60 input is the blow count already normalised to
100 kPa overburden, so no further CN correction is applied.

The CRR7.5 curve is valid for (N1)60 < 30.  A cleaner sand above that value
is treated as non-liquefiable and the kernel returns a high FS.

Honest limits: this is a single-layer, free-field check at one depth.  It does
not model the full soil profile, fines content, or the CPT-based procedures.
The subsidence amount a caller may apply is NOT derived here (the issue's
0.1-0.5 m figure is UNSOURCED); this kernel returns only FS and the
liquefiable flag.

Input:  [_pgaG, _depthM, _n160, _mag, _waterTableM] - peak ground acceleration
        (g), layer depth (m), (N1)60 blow count, moment magnitude, water-table
        depth (m).
Output: [FS, liquefiable] - factor of safety and FS < 1.
Public: No
*/

params [
    ["_pgaG", 0.2, [0]],
    ["_depthM", 5, [0]],
    ["_n160", 15, [0]],
    ["_mag", 6.5, [0]],
    ["_waterTableM", 1.5, [0]]
];

if (_depthM <= 0 || _depthM > 23) exitWith { [99, false] };
if (_n160 >= 30) exitWith { [99, false] };

private _sigmaV = 20 * _depthM;
private _u = 9.81 * ((_depthM - _waterTableM) max 0);
private _sigmaVeff = (_sigmaV - _u) max 1;

private _rdRaw = 1.174 - 0.0267 * _depthM;
if (_depthM <= 9.15) then { _rdRaw = 1.000 - 0.00765 * _depthM; };
private _rd = _rdRaw max 0;

private _csr = 0.65 * (_sigmaV / _sigmaVeff) * _pgaG * _rd;

private _crr75 = 1 / (34 - _n160) + _n160 / 135 + 50 / ((10 * _n160 + 45) ^ 2) - 1 / 200;
private _msf = (10 ^ 2.24) / (_mag ^ 2.56);
private _crr = _crr75 * _msf;

private _fs = 99;
if (_csr > 0.0001) then { _fs = _crr / _csr; };

[_fs, _fs < 1]
