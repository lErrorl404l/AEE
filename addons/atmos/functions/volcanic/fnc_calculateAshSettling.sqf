#include "..\..\script_component.hpp"

/*
Stokes terminal settling velocity for a volcanic ash particle (kernel).

  vs = (2/9) * (rho_p - rho_a) * g * r^2 / mu

Valid while the particle Reynolds number Re = rho_a * vs * d / mu < 1, which
holds for fine ash (below ~100 um).  Coarse ash settles faster and leaves the
Stokes regime; the caller applies the result to the fine-ash fraction.

Sources: Stokes, G.G. (1851) Trans. Camb. Phil. Soc. 9:8-106; Casadevall,
T.J. (ed.) (1994) USGS Bulletin 2047 "Volcanic Ash and Aviation Safety".

Arguments:
  0: Particle diameter (NUMBER, m)
  1: Particle density (NUMBER, kg/m3, default 2500)
  2: Air density (NUMBER, kg/m3, default 1.225)
  3: Dynamic viscosity of air (NUMBER, Pa.s, default 1.81e-5)

Return Value: NUMBER: settling velocity, m/s (>= 0)
Example: [1e-5, 2500, 1.225, 1.81e-5] call aee_atmos_fnc_calculateAshSettling
Public: No
*/

params [
    ["_diameter", 0, [0]],
    ["_particleDensity", 2500, [0]],
    ["_airDensity", 1.225, [0]],
    ["_viscosity", 1.81e-5, [0]]
];

if (_diameter <= 0 || _viscosity <= 0) exitWith { 0 };

private _r = _diameter / 2;
private _g = 9.80665;
private _vs = (2 / 9) * (_particleDensity - _airDensity) * _g * _r * _r / _viscosity;

_vs max 0
