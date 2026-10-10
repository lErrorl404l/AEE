#include "..\..\script_component.hpp"

/*
Briggs buoyant plume rise (kernel).

The height a hot volcanic plume reaches above its vent.  The buoyancy flux F
carries the thermal power of the eruption; the wind bends the plume and caps
the rise.  Briggs (1975) gives the final rise.

  Buoyancy flux   F = g * Qh / (pi * Cp * rho * T)
  Neutral / unstable (Pasquill A-D):
      F < 55  -> dh = 21.425 * F^(3/4) / u
      F >= 55 -> dh = 38.71  * F^(3/5) / u
  Stable (Pasquill E-F):
      dh = 2.6 * (F / (u * S))^(1/3),  S = (g / T) * dTheta/dz

Sources: Briggs, G.A. (1975) "Plume rise predictions", in Lectures on Air
Pollution and Environmental Impact Analyses, AMS, pp. 59-111; Pasquill, F.
(1961) Meteor. Mag. 90:33-49.

Arguments:
  0: Heat emission rate Qh (NUMBER, W)
  1: Wind speed at vent height u (NUMBER, m/s)
  2: Pasquill stability class (STRING, "A".."F", default "D")
  3: Ambient temperature (NUMBER, degrees C)
  4: Ambient air density (NUMBER, kg/m3)

Return Value: NUMBER: final plume rise above the vent, m (0 when no heat)
Example: [1.0e9, 8, "D", 15, 1.225] call aee_atmos_fnc_calculatePlumeRise
Public: No
*/

params [
    ["_heatFlux", 0, [0]],
    ["_windSpeed", 5, [0]],
    ["_stability", "D", [""]],
    ["_ambientTempC", 15, [0]],
    ["_airDensity", 1.225, [0]]
];

// ─── Buoyancy flux ──────────────────────────────────────────────────────────
// Cp = 1005 J/(kg K) dry air; g = 9.80665 m/s2; T in kelvin.
private _Cp = 1005;
private _g = 9.80665;
private _T = _ambientTempC + 273.15;
private _F = _g * _heatFlux / (pi * _Cp * _airDensity * _T);   // m4/s3

private _u = _windSpeed max 0.5;   // calm guard: no divide by zero

private _rise = 0;
if (_F > 0) then {
    if (_stability in ["E", "F"]) then {
        // Stable stratification: S = (g/T) dTheta/dz.  dTheta/dz ~ 0.02 K/m
        // (E), 0.035 K/m (F).
        private _dThetaDz = [0.02, 0.035] select (_stability == "F");
        private _S = (_g / _T) * _dThetaDz;   // 1/s2
        _rise = 2.6 * ((_F / (_u * _S)) ^ (1 / 3));
    } else {
        if (_F < 55) then {
            _rise = 21.425 * (_F ^ 0.75) / _u;
        } else {
            _rise = 38.71 * (_F ^ 0.6) / _u;
        };
    };
};

_rise
