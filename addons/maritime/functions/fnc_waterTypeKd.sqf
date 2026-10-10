#include "..\script_component.hpp"
/*
Diffuse attenuation coefficients per colour band for a Jerlov water type
(issue #14).

Underwater light decays with depth by the Beer-Lambert law:

    I(z) = I0 * exp(-Kd * z)

Kd is the diffuse attenuation coefficient (m^-1) and z is the depth (m).
Kd is strongly wavelength-dependent, so this kernel carries three bands:
red 660 nm, green 530 nm, blue 475 nm.  The blue shift of underwater light
emerges from the three exponentials, with no separate rule.

Derivation.  No coefficient is invented.

  1. The Jerlov water type sets the minimum Kd, at the transparency peak,
     and the peak wavelength (Jerlov 1976, Marine Optics).  The table
     midpoint is used:

       type   Kd_min (m^-1)   lambda_peak (nm)
       I      0.035           475
       IA     0.045           475
       IB     0.055           475
       II     0.085           475
       III    0.15            500
       1      0.17            500
       3      0.275           525
       5      0.425           550
       7      0.625           560
       9      0.90            575

  2. Kd splits into pure-water absorption a_w and the dissolved plus
     particulate attenuation a_oth:

       Kd(lambda) = a_w(lambda) + a_oth(lambda)

     a_w comes from Pope and Fry (1997), Applied Optics 36:8710, through
     fnc_pureWaterAbsorption.

  3. a_oth is dominated by gelbstoff (dissolved organic matter).  Its
     absorption falls exponentially with wavelength at the slope S:

       a_oth(lambda) = a_oth(lambda_peak) * exp(-S * (lambda - lambda_peak))

     S = 0.014 nm^-1 (Bricaud, Morel and Prieur 1981, Limnology and
     Oceanography 26:43).  The value at the peak follows from steps 1 and 2:

       a_oth(lambda_peak) = Kd_min - a_w(lambda_peak)

The stated approximation is that the non-water attenuation follows one
dissolved-matter exponential across 475-660 nm.  That reproduces the
measured behaviour: clear water keeps blue longest, turbid water loses
blue first, and the transparency peak shifts 475 to 575 nm as dissolved
matter rises.

Input:  [_type] - water-type index 0..9 (I, IA, IB, II, III, 1, 3, 5, 7, 9)
Output: [Kd_R, Kd_G, Kd_B] - attenuation per band (m^-1), 660/530/475 nm
*/

params [["_type", 3, [0]]];

private _kdMin = [0.035, 0.045, 0.055, 0.085, 0.15, 0.17, 0.275, 0.425, 0.625, 0.90];
private _peakNm = [475, 475, 475, 475, 500, 500, 525, 550, 560, 575];

private _idx = ((round _type) max 0) min 9;
private _kdPeak = _kdMin select _idx;
private _lambdaPeak = _peakNm select _idx;

private _awPeak = [_lambdaPeak] call FUNC(pureWaterAbsorption);
private _aOthPeak = _kdPeak - _awPeak;

private _slope = 0.014;   // dissolved organic matter slope, nm^-1

private _bands = [660, 530, 475];
private _out = [];
{
    private _aw = [_x] call FUNC(pureWaterAbsorption);
    private _aOth = _aOthPeak * (exp (-_slope * (_x - _lambdaPeak)));
    _out pushBack (_aw + _aOth);
} forEach _bands;

_out
