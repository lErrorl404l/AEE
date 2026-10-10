#include "..\..\script_component.hpp"

/*
Liquid-pool evaporation mass flux (issue #120).

A volatile or liquefied agent spilled on the ground forms a pool and
evaporates from its surface.  Kawamura & Mackay (1987, Journal of
Hazardous Materials 15(3):343-364; also Environment Canada EE-59, 1985)
give the mass flux

  E = k * M * P(Ts) / (R * Ts)                  g/m2/h

where M is the molar mass (g/mol), P(Ts) the saturation vapour pressure
at the surface temperature Ts (Pa), R the gas constant 8.314 J/mol/K,
and k the mass-transfer coefficient (m/h) from Mackay & Matsugu (1973):

  k = 0.029 * u^0.78 * X^-0.11 * Sc^-0.67       m/h

with u the wind speed in m/h at 10 m, X the pool diameter in m, and Sc
the Schmidt number (air-vapour).  M*P/(R*Ts) is the saturation
concentration (kg/m3, or g/m3 with M in g/mol); k converts it to a flux.

The returned value is in kg/m2/s, the per-tick unit the engine consumes.
The default Schmidt number 0.7 is a MODELLING CHOICE for gases in air
(most vapours fall in 0.6 to 1.0); it is exposed so a caller can set it.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: NUMBER - wind speed u at 10 m, m/s
  1: NUMBER - pool diameter X, m
  2: NUMBER - molar mass M, g/mol
  3: NUMBER - saturation vapour pressure P(Ts), Pa
  4: NUMBER - surface temperature Ts, K
  5: NUMBER - Schmidt number Sc (default 0.7)

Returns:
  NUMBER - evaporation mass flux, kg/m2/s
*/

params [
    ["_windSpeed", 0, [0]],
    ["_poolDiameter", 1, [0]],
    ["_molarMass", 0, [0]],
    ["_vapourPressurePa", 0, [0]],
    ["_surfaceTempK", 293.15, [0]],
    ["_schmidt", 0.7, [0]]
];

private _r = 8.314;      // J/mol/K
private _uMetresPerHour = (_windSpeed max 0) * 3600;
private _x = _poolDiameter max 0.1;
private _sc = _schmidt max 0.1;

// Mackay & Matsugu 1973 mass-transfer coefficient, m/h.
private _k = 0.029 * (_uMetresPerHour ^ 0.78) * (_x ^ -0.11) * (_sc ^ -0.67);

// Kawamura & Mackay flux, g/m2/h (M in g/mol, P in Pa).
private _fluxGrams = _k * _molarMass * _vapourPressurePa / (_r * (_surfaceTempK max 1));

// kg/m2/s
_fluxGrams / 1000 / 3600
