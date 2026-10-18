#include "..\..\script_component.hpp"
/*
Condensation (fogging) on an exposed optic, 0-1 (0 clear, 1 fully fogged).

A lens fogs when its surface is colder than the dew point of the air around
it.  The optic (an aluminium tube with glass, lumped: 0.6 kg, 900 J/kg/K,
0.06 m2, a typical 30 mm riflescope) exchanges heat by
  - forced convection over a 40 mm cylinder, the Hilpert correlation
    Nu = C Re^m Pr^1/3 (Incropera & DeWitt, Fundamentals of Heat and Mass
    Transfer, Table 7.2), with a 3 W/m2/K natural-convection floor;
  - longwave radiation to the sky over half its view (glass emittance 0.92,
    Incropera Table A.11), the clear-sky emissivity
    0.70 + 5.95e-5 e exp(1500/T) of Idso 1981 (WRR 17:295), lifted by cloud,
    eps + (1 - eps) N, the other half seeing ground at the air temperature;
and relaxes toward that balance with tau = m c / ((h + h_r) A).  Solar
heating of the optic is not modelled (the dawn dew case it matters for is
sunless).  The dew point is the Magnus inversion (Bolton 1980).
While the lens is below the dew point the fog builds at the dewAccumRate
setting; above it, the film evaporates at dewDecayRate.  Those two rates and
the breath-fog flicker are DISPLAY rates, not physical constants.

Stored in GVAR(dewOnOptics) and GVAR(lensTemperature) (C).
*/
params [];
private _tAir = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_tAir isEqualType 0) then { _tAir = 15; };
private _rh = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
if !(_rh isEqualType 0) then { _rh = 50; };
_rh = (_rh max 1) min 100;
private _wind = vectorMagnitude (missionNamespace getVariable [QEGVAR(core,currentWind), [0, 0]]);
private _dt = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
if !(_dt isEqualType 0) then { _dt = 5; };

// Dew point, Magnus (Bolton 1980).
private _e = (_rh / 100) * 6.112 * exp (17.67 * _tAir / (_tAir + 243.5));
private _lnE = ln (_e / 6.112);
private _tDew = 243.5 * _lnE / (17.67 - _lnE);

// Convection: Hilpert, cylinder D = 0.04 m in crossflow, air at 15 C.
private _d = 0.04;
private _re = ((_wind max 0.01) * _d) / 1.5e-5;
private _cm = [0.027, 0.805];
if (_re < 40000) then { _cm = [0.193, 0.618]; };
if (_re < 4000) then { _cm = [0.683, 0.466]; };
if (_re < 40) then { _cm = [0.911, 0.385]; };
private _h = (((_cm select 0) * (_re ^ (_cm select 1)) * (0.71 ^ (1 / 3))) * 0.026 / _d) max 3;

// Radiation: half the view is sky (Idso), half ground at air temperature.
private _tK = _tAir + 273.15;
private _epsSky = (0.70 + 5.95e-5 * _e * exp (1500 / _tK)) min 1;
private _n = ((overcast max 0) min 1);
_epsSky = _epsSky + (1 - _epsSky) * _n;
private _tSkyK = (_epsSky ^ 0.25) * _tK;
private _sigma = 5.670374419e-8;
private _hr = 4 * 0.92 * _sigma * (_tK ^ 3);
private _tEnv = 0.5 * _tAir + 0.5 * (_tSkyK - 273.15);
// Steady lens temperature from the linearised balance.
private _tEq = ((_h * _tAir) + (_hr * _tEnv)) / (_h + _hr);

private _tau = (0.6 * 900) / ((_h + _hr) * 0.06);
private _tLens = missionNamespace getVariable [QGVAR(lensTemperature), _tEq];
if !(_tLens isEqualType 0) then { _tLens = _tEq; };
_tLens = _tEq + (_tLens - _tEq) * exp (-(_dt max 0) / _tau);

private _fog = missionNamespace getVariable [QGVAR(dewTimer), 0];
if !(_fog isEqualType 0) then { _fog = 0; };
private _scale = (_dt max 0) / 5;
if (_tLens < _tDew) then {
    _fog = (_fog + (missionNamespace getVariable [QGVAR(dewAccumRate), 0.05]) * _scale) min 1;
} else {
    _fog = (_fog - (missionNamespace getVariable [QGVAR(dewDecayRate), 0.02]) * _scale) max 0;
};
private _breathFog = [0, random 0.05] select (_tAir < 0 && _fog > 0);
private _obscuration = (_fog + _breathFog) min 1;

missionNamespace setVariable [QGVAR(lensTemperature), _tLens];
missionNamespace setVariable [QGVAR(dewTimer), _fog];
missionNamespace setVariable [QGVAR(dewOnOptics), _obscuration];
_obscuration
