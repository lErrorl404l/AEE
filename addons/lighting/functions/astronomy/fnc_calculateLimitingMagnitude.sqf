#include "..\..\script_component.hpp"

/*
Naked-eye limiting magnitude (NELM) at the zenith from the sky luminance.

Sky luminance at the zenith, cd/m2, the sum of:
  - the natural night sky, 22.0 mag/arcsec2 = 1.74e-4 cd/m2 (Falchi et al.
    2016, Sci. Adv. 2:e1600377, the natural background of the World Atlas);
  - moonlight scattered by the air (Krisciunas & Schaefer 1991, PASP
    103:1033, eqs. 15-21) for the zenith (X = 1), the Moon at zenith
    distance Z and phase angle a:
      B = f(rho) I* 10^(-0.4 k X_moon) (1 - 10^(-0.4 k))   nanolamberts
      f(rho) = 10^5.36 (1.06 + cos^2 rho) + 10^(6.15 - rho/40), rho = Z
      I* = 10^(-0.4 (3.84 + 0.026 |a| + 4e-9 a^4))
      X_moon = (1 - 0.96 sin^2 Z)^-1/2;  1 nL = 3.183e-6 cd/m2;
  - twilight: the sky of a sun below the horizon is the only light on a
    horizontal plane, so for an isotropic sky L = E / pi
    (fnc_twilightIlluminance, already cloud-cut).
The threshold illuminance of a point source against that luminance is the
Knoll et al. (1946) law, which Crumey (2014, MNRAS 442:2600, eq. 19) shows
fits astronomical conditions better than Hecht's:
  dI = 1.076e-9 (1 + 1e5 B)^1/2  lux,  B in cd/m2.
A V = 0 star gives 2.54e-6 lux above the atmosphere (Schlyter, held in
data/astronomy/sources), so m = -2.5 log10(dI / 2.54e-6), less the zenith
extinction k (mag per air mass):
  k = 1.086 (tau_Rayleigh 0.0973 + tau_ozone 0.027 + tau_aerosol)  at 550 nm,
tau_aerosol from the published haze extinction (less Rayleigh, Bucholtz
1995, times the 1.2 km aerosol scale height, Elterman 1968).

Light pollution: the artificial zenith luminance of the settlement around
the observer (fnc_lightPollutionPenalty, Albers & Duriscoe 2001 with the UN
household size) adds to the sky luminance.

Arguments:
  0: Number - Moon altitude, deg
  1: Number - Moon illuminated fraction, 0..1
  2: Number - twilight horizontal illuminance, lux
  3: Number - haze extinction at 550 nm, per km
  4: Number - nearby house count
  5: Number - persons per household

Pure.  The caller publishes aee_lighting_limitingMagnitude and
aee_lighting_skyLuminance.
Returns: [limiting magnitude at the zenith, sky luminance cd/m2].
*/

params [
    ["_moonAlt", -90, [0]],
    ["_moonFrac", 0, [0]],
    ["_twilightLux", 0, [0]],
    ["_haze", 0.08, [0]],
    ["_houseCount", 0, [0]],
    ["_perHouse", 3.8, [0]]
];

private _tauAer = ((_haze - 0.0116) max 0) * 1.2;
private _k = 1.086 * (0.0973 + 0.027 + _tauAer);

private _b = 1.74e-4;

if (_moonAlt > 0 && _moonFrac > 0) then {
    private _z = 90 - _moonAlt;
    private _alpha = acos ((((2 * (_moonFrac min 1)) - 1) max -1) min 1);
    private _iStar = 10 ^ (-0.4 * (3.84 + (0.026 * _alpha) + (4e-9 * (_alpha ^ 4))));
    private _f = ((10 ^ 5.36) * (1.06 + ((cos _z) ^ 2))) + (10 ^ (6.15 - (_z / 40)));
    private _xMoon = 1 / (sqrt (1 - (0.96 * ((sin _z) ^ 2))));
    private _bMoonNl = _f * _iStar * (10 ^ (-0.4 * _k * _xMoon)) * (1 - (10 ^ (-0.4 * _k)));
    _b = _b + (_bMoonNl * 3.183e-6);
};

_b = _b + ((_twilightLux max 0) / pi);
_b = _b + ([_houseCount, _perHouse] call FUNC(lightPollutionPenalty));

private _dI = 1.076e-9 * (sqrt (1 + (1e5 * _b)));
private _mLim = (-2.5 * (log (_dI / 2.54e-6))) - _k;


_mLim = (_mLim max -2) min 8;

[_mLim, _b]
