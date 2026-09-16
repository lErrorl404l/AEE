#include "..\script_component.hpp"

/*
Author: AEE
Description: Computes atmospheric refraction from temperature, humidity, and pressure. Radio refractivity follows ITU-R P.453. The surface refractivity gradient, k-factor, ducting condition, mirage type, and refraction angle are derived from the state. Results are stored in aee_atmos_* mission variables.
Arguments: None
Return Value: NUMBER: refraction k-factor
Example: [] call aee_atmos_fnc_calculateRefraction
Public: No
*/

params [];

if (!(missionNamespace getVariable [QGVAR(refractionEnabled), true])) exitWith {
    missionNamespace setVariable [QGVAR(refractivityN), 0];
    missionNamespace setVariable [QGVAR(refractivityGradient), 0];
    missionNamespace setVariable [QGVAR(refractionK), 1];
    missionNamespace setVariable [QGVAR(refractionCondition), "None"];
    missionNamespace setVariable [QGVAR(mirageType), "None"];
    missionNamespace setVariable [QGVAR(refractionAngle), 0];
    1
};

private _temp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _pressure = missionNamespace getVariable [QEGVAR(core,currentPressure), 1013];

// ─── Vapour pressure (Buck equation) ──────────────────────────────────────
// e = RH/100 * 6.105 * exp(17.27*T / (237.7 + T)) hPa.
private _vapour = (_humidity / 100) * 6.105 * exp (17.27 * _temp / (237.7 + _temp));

// ─── Radio refractivity (ITU-R P.453) ─────────────────────────────────────
// N = 77.6 * P/T + 3.73e5 * e/T^2, T in Kelvin.
private _tempK = _temp + 273.15;
private _refractivity = 77.6 * _pressure / _tempK + 3.73e5 * _vapour / (_tempK ^ 2);

// ─── Refractivity gradient (N/km) ─────────────────────────────────────────
// The standard atmosphere has a surface gradient of -39 N/km. The
// simulation scales this by the temperature deviation from 15 C.
private _gradient = -39 * (1 + 0.00366 * (_temp - 15));

// ─── k-factor ─────────────────────────────────────────────────────────────
// k = 1 / (1 + a * dn/dh) with a = 6371 km. The gradient is in N/km, so
// the product carries a 1e-6 scale. Ducting (dN/dh < -157) drives the
// denominator to zero; the clamp keeps k finite.
private _denom = 1 + 6371 * _gradient * 1e-6;
private _k = 1 / (_denom max 0.001);

// ─── Condition ────────────────────────────────────────────────────────────
private _condition = "Standard";
if (_gradient <= -157) then {
    _condition = "Ducting";
} else {
    if (_gradient < -39) then {
        _condition = "Super-refraction";
    } else {
        if (_gradient > -39) then {
            _condition = "Sub-refraction";
        };
    };
};

// ─── Mirage type ──────────────────────────────────────────────────────────
// A strong lapse (super-refraction) gives an inferior mirage; an
// inversion (sub-refraction) gives a superior mirage.
private _mirage = "None";
if (_gradient <= -157) then {
    _mirage = "Towering";
} else {
    if (_gradient < -39) then {
        _mirage = "Inferior";
    } else {
        if (_gradient > 0) then {
            _mirage = "Looming";
        } else {
            if (_gradient > -39) then {
                _mirage = "Superior";
            };
        };
    };
};

// ─── Refraction angle (degrees, 100 km reference path) ────────────────────
// Small-angle bending: dTheta = -(dn/dh) * d / n. dn/dh = dN/dh * 1e-6.
private _angle = (-1 * _gradient * 1e-6 * 100 / 1.0003) * 180 / pi;

// ─── Store ────────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(refractivityN), _refractivity];
missionNamespace setVariable [QGVAR(refractivityGradient), _gradient];
missionNamespace setVariable [QGVAR(refractionK), _k];
missionNamespace setVariable [QGVAR(refractionCondition), _condition];
missionNamespace setVariable [QGVAR(mirageType), _mirage];
missionNamespace setVariable [QGVAR(refractionAngle), _angle];

_k
