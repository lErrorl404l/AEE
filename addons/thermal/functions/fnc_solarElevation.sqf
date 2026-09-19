#include "..\script_component.hpp"
/*
Equilibrium solar elevation above air for a surface (issue #124 audit).

The old object solver added `_solar * alpha * 15` to the target
temperature: it treated the 0..1 solar FACTOR as if multiplying by 15
produced degrees Celsius.  At clear noon that yields a maximum +9 C
elevation for fabric - six times below the real equilibrium (a cloth
surface in full sun sits ~45 C above 30 C air; metal ~53 C).  It also
ignored wind and radiation.

This returns the TRUE steady-state elevation from the same single-node
energy balance every AEE surface uses:

  alpha * G = h * (Ts - Ta) + eps * sigma * (Ts^4 - Ta^4)

solved to convergence (Newton, radiation included - the term that caps
high-temperature elevation).  This is the same solve as
fnc_solveSelectionTemperature; the object solver calls it per surface
class instead of carrying a unit-mixing constant.

Input:
  0: solar absorptance (NUMBER 0..1)
  1: solar flux (NUMBER, W/m2) - from currentSolarFlux
  2: emissivity (NUMBER 0..1)
  3: ambient temperature (NUMBER, Celsius)
  4: wind (NUMBER, m/s)

Output: elevation above air in Celsius (number) - add to the target
*/

params [
    ["_alpha", 0.6, [0]],
    ["_flux", 0, [0]],
    ["_eps", 0.9, [0]],
    ["_tAir", 15, [0]],
    ["_wind", 0, [0]]
];

if (_flux <= 0) exitWith { 0 };

private _h = 5.7 + 3.8 * (_wind max 0);
private _sigma = 5.670374419e-8;
private _tAirK = _tAir + 273.15;
private _tsK = _tAirK + 1;

for "_i" from 1 to 10 do {
    private _qConv = _h * (_tsK - _tAirK);
    private _qRad = _eps * _sigma * ((_tsK ^ 4) - (_tAirK ^ 4));
    private _residual = (_alpha * _flux) - _qConv - _qRad;
    private _deriv = -(_h + (4 * _eps * _sigma * (_tsK ^ 3)));
    if (_deriv == 0) exitWith {};
    _tsK = _tsK - (_residual / _deriv);
};

(_tsK - _tAirK) max 0
