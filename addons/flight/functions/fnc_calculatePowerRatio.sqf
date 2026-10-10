#include "..\script_component.hpp"

/*
Engine power or thrust ratio against the density ratio (issue #22).

The available power or thrust falls as the air thins.  The exponent depends on
the engine cycle:

  naturally-aspirated piston   P / P0 = sigma^1.2   (SAE J1349)
  turbojet                     T / T0 = sigma
  turbofan                     T / T0 = sigma^0.7
  turboprop                    T / T0 = sigma       (see below)

sigma is the density ratio rho / rho0 with rho0 = 1.225 kg/m3 (ISO 2533).  The
piston exponent 1.2 is the SAE J1349 density correction and reproduces the
3 percent per 1000 ft rule within one to two points: sigma 0.789 at 8000 ft
gives 0.752.  The turbojet and turbofan exponents are the standard thrust
lapse.  The issue names only the piston and the two jets.  A turboprop is
taken as gas-turbine-like and its exponent is UNSOURCED.

This is a pure kernel.

Arguments:
  0: NUMBER - density ratio sigma = rho / 1.225, 0 < sigma <= ~1.2
  1: STRING - propulsion token: piston_prop, turbojet, turbofan or turboprop

Return Value: NUMBER - power or thrust ratio, P/P0 or T/T0
Example: [0.789, "piston_prop"] call aee_flight_fnc_calculatePowerRatio
Public: No
*/

params [
    ["_sigma", 1, [0]],
    ["_propulsion", "", [""]]
];

private _safeSigma = _sigma max 0.01;
private _key = toLower _propulsion;

// Turbojet, turboprop and an unknown token lapse as sigma.  The piston and
// the turbofan override.
private _exponent = 1.0;
if (_key == "piston_prop") then { _exponent = 1.2; };
if (_key == "turbofan") then { _exponent = 0.7; };

_safeSigma ^ _exponent
