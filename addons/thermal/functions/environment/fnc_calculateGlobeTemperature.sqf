#include "..\..\script_component.hpp"
/*
Black-globe thermometer temperature (ISO 7726) - the radiant term in
WBGT, solved from the energy balance instead of guessed.

The WBGT formula needs the globe temperature Tg: the equilibrium
temperature of a black globe (D = 0.15 m, eps = 0.95) exposed to solar
radiation, longwave radiation from the surroundings (MRT), and
convection.  The old fnc_calculateWBGT GUESSED Tg = Tair + 15 in sun
and Tair in shade.  That guess has no physical basis - the real globe
temperature is set by the balance

  absorbed solar + absorbed longwave = emitted longwave + convection

  alpha_globe * G/4  +  eps_globe * sigma * MRT^4
        = eps_globe * sigma * Tg^4 + h * (Tg - Tair)

with the projected area of a sphere being one quarter of its surface
area (G is hemispherical irradiance W/m2 on a flat surface; a sphere
presents a circular cross-section = A/4), alpha_globe = eps_globe =
0.95 for matte black paint, and h the McAdams convection coefficient
(5.7 + 3.8 * w, the same model every other AEE surface uses - Energies
2022, IES VE).

On a sunny day MRT sits far above Tair (hot ground, hot objects), so
the globe reads above air temperature even though it is a passive
absorber.  On a clear night MRT falls below Tair (cold sky radiates at
Swinbank sky temperature), so the globe reads cold.  Both effects are
real and both were missing from the +15 guess.

The equation is solved for Tg by fixed-point iteration (the same
8-iteration pattern the per-selection solver uses); the result is
bounded to [Tair - 60, Tair + 90] C, which covers the physical range
of a passive sphere (it cannot run away hotter than the sun's
equivalent blackbody).

Input:  none (reads EGVAR(core,...) state: temperature, wind, solar,
        humidity)
Output: globe temperature Tg in degrees C (number)
*/

if !(missionNamespace getVariable [QEGVAR(core,enabled), true]) exitWith { missionNamespace getVariable [QEGVAR(core,currentTemperature), 15] };

private _tAir = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_tAir isEqualType 0) then { _tAir = 15; };

private _mrt = [] call FUNC(calculateMRT);
private _wind = missionNamespace getVariable [QEGVAR(core,currentWind), [0, 0, 0]];
if !(_wind isEqualType []) then { _wind = [0, 0, 0]; };
private _windSpd = vectorMagnitude _wind;
private _solar = missionNamespace getVariable [QEGVAR(core,currentSolarFlux), 0];
if !(_solar isEqualType 0) then { _solar = 0; };

private _h = 5.7 + (3.8 * _windSpd);            // McAdams W/m2K
private _sigma = 5.670374419e-8;             // CODATA 2022
private _epsG = 0.95;                        // matte black globe
private _alphaG = 0.95;                      // black paint absorptance
private _mrtK = _mrt + 273.15;
private _tAirK = _tAir + 273.15;

// Fixed-point: q_absorbed - q_emitted - q_conv = 0
private _tg = _tAir + 10;                    // first guess
private _tgK = _tg + 273.15;
for "_i" from 1 to 8 do {
    private _absorbed = (_alphaG * _solar / 4) + (_epsG * _sigma * (_mrtK ^ 4));
    private _lost = (_epsG * _sigma * (_tgK ^ 4)) + (_h * (_tgK - _tAirK));
    private _residual = _absorbed - _lost;
    // d/dTg of lost term: 4*eps*sigma*Tg^3 + h
    private _deriv = -((4 * _epsG * _sigma * (_tgK ^ 3)) + _h);
    _tgK = _tgK - (_residual / _deriv);
    if (_tgK < (_tAirK - 60)) then { _tgK = _tAirK - 60; };
    if (_tgK > (_tAirK + 90)) then { _tgK = _tAirK + 90; };
};

(_tgK - 273.15)
