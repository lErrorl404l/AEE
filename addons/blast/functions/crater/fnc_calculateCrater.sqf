#include "..\..\script_component.hpp"

/*
Apparent and true crater size and shape (Hopkinson-Cranz scaling; WES and
TM 5-855-1 crater equations).

The crater radius and depth follow the WES general form r or d = K * W^n
(WES Report 2, about 1800 shots): the radius exponent is 1/3, the depth
exponent is 0.3.  Strength enters the coefficient K, not the exponent.  The
recommended model:

    R_a    = C_R * W^(1/3)               apparent radius (m)
    D_a    = C_D * W^n                   apparent depth (m)
    V      = 0.5 * pi * R_a^2 * D_a      paraboloid volume (m^3)
    R_lip  = 1.25 * R_a                  lip radius
    H_lip  = 0.25 * D_a                  lip height
    R_ej   = 2.15 * R_a                  ejecta radius (Glasstone 6.71)
    R_true = 1.15 * R_a                  true radius (up to optimum DOB)
    D_true = max(D_a, DOB + 0.4 * W^(1/3))

W is the TNT-equivalent charge mass in kilograms.  The apparent crater is the
visible crater after fallback.  The true crater is the excavated crater before
fallback.  The 0.4 in D_true is ft/lb^(1/3) and converts to 0.15864 m/kg^(1/3).
Depth/diameter ratios: about 0.25 soil, 0.20 apparent simple craters, 0.28 dry
sandy clay, 0.27 concrete.

Medium coefficients C_R, C_D (m/kg^(1/3)) are the published ft/lb^(1/3) values
converted by 0.39659 (1 ft/lb^(1/3) = 0.39659 m/kg^(1/3)):

    soil              C_R 0.4000   C_D 0.2000   Kinney-Graham surface burst
    drySandyClay      C_R 0.38866  C_D 0.21812  0.98 / 0.55 ft/lb^(1/3)
    concrete          C_R 0.15070  C_D 0.07932  0.38 / 0.20 ft/lb^(1/3)
    optimumBurialSoil C_R 0.22209  C_D 0.09915  0.56 / 0.25 ft/lb^(1/3)
    drySand           C_R 0.29744  C_D 0.14872  0.75 ft/lb^(1/3)
    wetClay           C_R 0.45608  C_D 0.22804  1.15 ft/lb^(1/3)
    sandstone         C_R 1.19000  C_D 0.40000  1.19 / 0.40 m/kg^(1/3.4), n 1/3.4

The Kinney-Graham surface burst is D = 0.8 * W^(1/3) in metres (Kinney and
Graham define D as the apparent crater diameter), so the soil radius
coefficient is 0.4.  This matches the dry sandy clay diameter (0.778
m/kg^(1/3)).

Sources: TM 5-855-1 (US Army cratering nomograms); UFC 3-340-02; WES Report 2
(1961); Hopkinson (1915); Cranz (1926); Kinney and Graham (1985); Ambrosini;
Muller and Carleton; Glasstone and Dolan; Chabai (1973); Violet (1961);
Vaile (1954).

Honest limits: the cube root breaks when gravity or strength dominates.  The
WES depth exponent is 0.3 (Chabai 1973); Violet uses 1/3.4 for large or heavy
charges; the strength regime tends toward 1/4.  The 1/3 and 1/3.4 results
differ by 31 per cent at 1000 kg but lie within the 10-30 per cent scatter.
The coefficient matters more than the exponent.  Bare charges only: a cased
munition craters smaller.  The medium effect factor reaches 2x (Vaile 1954).

Input:  [_massKg, _medium, _dofM] - charge mass (kg), medium key, and the
        depth of burial of the charge centre (m, 0 for a surface burst).
Output: [R_a, D_a, V, R_lip, H_lip, R_ej, R_true, D_true]
Public: No
*/

params [["_massKg", 1, [0]], ["_medium", "drySandyClay", [""]], ["_dofM", 0, [0]]];

if (_massKg <= 0) exitWith { [0, 0, 0, 0, 0, 0, 0, 0] };

// Medium coefficients in m/kg^(1/3).  The depth exponent n defaults to the
// WES radius exponent 1/3, which reproduces the published OKC and CONWEP
// craters.
private _cR = 0.38866;
private _cD = 0.21812;
private _n = 1 / 3;

if (_medium == "soil") then { _cR = 0.40; _cD = 0.20; };
if (_medium == "concrete") then { _cR = 0.15070; _cD = 0.07932; };
if (_medium == "optimumBurialSoil") then { _cR = 0.22209; _cD = 0.09915; };
if (_medium == "drySand") then { _cR = 0.29744; _cD = 0.14872; };
if (_medium == "wetClay") then { _cR = 0.45608; _cD = 0.22804; };
if (_medium == "sandstone") then { _cR = 1.19; _cD = 0.40; _n = 1 / 3.4; };

private _w13 = _massKg ^ (1 / 3);
private _wn = _massKg ^ _n;

private _rA = _cR * _wn;
private _dA = _cD * _wn;
private _v = 0.5 * pi * _rA * _rA * _dA;
private _rLip = 1.25 * _rA;
private _hLip = 0.25 * _dA;
private _rEj = 2.15 * _rA;
private _rTrue = 1.15 * _rA;
private _dTrue = _dA max (_dofM + 0.15864 * _w13);

[_rA, _dA, _v, _rLip, _hLip, _rEj, _rTrue, _dTrue]
