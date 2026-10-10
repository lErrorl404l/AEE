#include "..\..\script_component.hpp"

/*
Rothermel (1972) steady rate of spread of a surface fire.

The full Rothermel spread equation, with the wind and slope factors:

  R = IR * xi * (1 + phi_w + phi_s) / (rho_b * epsilon * Q_ig)

  IR      = Gamma' * w_n * h * eta_M * eta_s      reaction intensity
  Gamma'  = Gamma'_max * (beta/beta_op)^A * exp(A*(1 - beta/beta_op))
  Gamma'_max = sigma^1.5 / (495 + 0.0594*sigma^1.5)
  beta_op = 3.348 * sigma^-0.8189 ; beta = rho_b / rho_p, rho_p = 513 kg/m3
  A       = 1 / (4.774 * sigma^0.1 - 7.27)
  eta_M   = 1 - 2.59*r + 5.11*r^2 - 3.52*r^3, r = Mf/Mx ; 0 when Mf >= Mx
  eta_s   = 0.174 * Se^-0.19 (mineral damping, capped at 1)
  xi      = exp((0.792 + 0.681*sigma^0.5)*(beta + 0.1)) / (192 + 0.2595*sigma)
  epsilon = exp(-138 / sigma)
  Q_ig    = 250 + 1116*Mf
  phi_w   = C * U^B * (beta/beta_op)^-E
            C = 7.47*exp(-0.133*sigma^0.55), B = 0.02526*sigma^0.54,
            E = 0.715*exp(-3.59e-4*sigma)
  phi_s   = 5.275 * beta^-0.3 * tan(slope)^2

Source: Rothermel, R. C. (1972) "A Mathematical Model for Predicting Fire
Spread in Wildland Fuels", USDA Forest Service Research Paper INT-115
(equations 12, 14, 30, 36, 37, 38, 39, 42, 52).  Fuel parameters are the
Albini (1976) INT-GTR-30 / Anderson (1982) INT-122 standard models.

The equations are unit-specific: sigma in ft^-1, loads in lb/ft^2, depth in
ft, heat in BTU/lb, wind in ft/min.  This kernel takes SI inputs (load in
kg/m^2, depth in m, wind in m/s, heat in kJ/kg) and converts to the native
units, then returns R in m/s.  phi_s takes the tangent of the slope angle
(rise over run) directly.

Params:
  _sigma    surface-area-to-volume ratio, ft^-1
  _w0       oven-dry fuel load, kg/m^2
  _delta    fuel bed depth, m
  _mf       fine dead fuel moisture, fraction
  _mx       moisture of extinction, fraction
  _uMs      midflame wind speed, m/s
  _slopeTan tangent of the terrain slope angle (rise/run)

Returns the rate of spread in m/s.  Zero when the fuel is unavailable
(_w0 <= 0) or the fuel moisture has reached the moisture of extinction.
*/

params [
    ["_sigma", 3500, [0]],
    ["_w0", 0.166, [0]],
    ["_delta", 0.3048, [0]],
    ["_mf", 0.05, [0]],
    ["_mx", 0.12, [0]],
    ["_uMs", 0, [0]],
    ["_slopeTan", 0, [0]]
];

private _r = 0;
if ((_w0 > 0) && (_mf < _mx) && (_sigma > 0)) then {
    private _rhoP = 32;          // lb/ft^3, particle density (513 kg/m^3)
    private _h = 8000;           // BTU/lb, heat content (Albini 1976)
    private _st = 0.0555;        // total mineral content (Albini 1976)
    private _se = 0.01;          // effective mineral content (Albini 1976)

    private _w0Lb = _w0 * 0.204816;      // kg/m^2 -> lb/ft^2
    private _deltaFt = _delta * 3.28084; // m -> ft
    private _uFtMin = _uMs * 196.850;    // m/s -> ft/min

    private _rhoB = _w0Lb / (_deltaFt max 0.001);
    private _beta = _rhoB / _rhoP;
    private _betaOp = 3.348 * _sigma ^ (-0.8189);
    private _ratio = _beta / _betaOp;

    private _a = 1 / (4.774 * _sigma ^ 0.1 - 7.27);
    private _gMax = _sigma ^ 1.5 / (495 + 0.0594 * _sigma ^ 1.5);
    private _g = _gMax * _ratio ^ _a * exp (_a * (1 - _ratio));

    private _etaS = (0.174 * _se ^ (-0.19)) min 1;
    private _mfRatio = _mf / _mx;
    private _etaM = 1 - 2.59 * _mfRatio + 5.11 * _mfRatio ^ 2 - 3.52 * _mfRatio ^ 3;
    _etaM = _etaM max 0;

    private _ir = _g * _w0Lb * (1 - _st) * _h * _etaM * _etaS;
    private _xi = exp ((0.792 + 0.681 * _sigma ^ 0.5) * (_beta + 0.1)) / (192 + 0.2595 * _sigma);
    private _eps = exp (-138 / _sigma);
    private _qig = 250 + 1116 * _mf;

    private _c = 7.47 * exp (-0.133 * _sigma ^ 0.55);
    private _b = 0.02526 * _sigma ^ 0.54;
    private _e = 0.715 * exp (-3.59e-4 * _sigma);
    private _phiW = _c * _uFtMin ^ _b * _ratio ^ (-_e);
    private _phiS = 5.275 * _beta ^ (-0.3) * _slopeTan ^ 2;

    private _denom = _rhoB * _eps * _qig;
    private _rFtMin = _ir * _xi * (1 + _phiW + _phiS) / (_denom max 1e-9);
    _r = _rFtMin * 0.3048 / 60;          // ft/min -> m/s
};

_r
