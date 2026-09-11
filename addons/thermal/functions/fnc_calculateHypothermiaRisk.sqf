#include "..\script_component.hpp"

/*
Cold exposure risk index (0–1).
  0.0 = safe (temp > 15 °C)
  1.0 = severe hypothermia risk

Factors: wind-chill adjusted temperature, rain accumulation, ground state.

Stored in GVAR(currentHypothermiaRisk).
*/

private _T_C = EGVAR(core,currentTemperature);
if (isNil "_T_C") exitWith { 0 };

// No risk above 15 °C
if (_T_C > 15) exitWith { 0 };

private _windSpeed  = vectorMagnitude wind;
private _rainAccum  = missionNamespace getVariable [QEGVAR(core,rainAccum), 0];
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];

// ─── Wind-chill adjusted temperature
private _windChill = _windSpeed * (0.3 + ((15 - _T_C) max 0) / 20);
private _T_adjusted = _T_C - _windChill;

// ─── Temperature risk: 0 at 15 °C → 1 at –25 °C
private _tempRisk = ((15 - _T_adjusted) / 40) min 1 max 0;

// ─── Wetness factor from rain accumulation
private _wetRisk = _rainAccum min 1;

// ─── Ground-state modifier
private _groundRisk = switch (_groundState) do {
    case "Snow":   { 0.30 };
    case "Frozen": { 0.20 };
    case "Mud":    { 0.10 };
    default        { 0    };
};

// ─── Composite (weighted)
private _risk = (_tempRisk * 0.6) + (_wetRisk * 0.25) + (_groundRisk * 0.15);
_risk = _risk min 1;

missionNamespace setVariable [QEGVAR(core,currentHypothermiaRisk), _risk];

_risk
