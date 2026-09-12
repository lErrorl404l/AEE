#include "..\script_component.hpp"

/*
Rothermel (1972) fire spread rate — simplified implementation.

Rate of spread (m/s) from fuel, wind, slope and fuel moisture:

  ROS = 0.03 × fuelFactor × (1 + 0.2·wind) × (1 + 0.1·slope%) × exp(–moisture·0.05)

Fuel factor from ground state: grass 1.0, scrub 0.8, forest 0.6,
minimal fuel (snow, frozen, urban) 0.1. Fuel moisture from humidity and
recent rain (simplified formulation). Fire area grows as a circle at the
spread rate.

Stores:
  QEGVAR(core,currentFireRisk)  — danger index 0–1 (normalised spread rate)
  QGVAR(fireSpreadRate_mps)     — rate of spread
  QGVAR(fireArea_m2)            — integrated fire area
*/

private _RH = EGVAR(core,currentHumidity);
private _windSpeed = vectorMagnitude wind;
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _rainAccum = missionNamespace getVariable [QEGVAR(core,rainAccum), 0];
private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];

if (isNil "_RH") then { _RH = 50; };

// ─── Fuel factor from ground state ────────────────────────────────────────
private _fuelFactor = switch (_groundState) do {
    case "Snow":   { 0.1 };  // snow-covered — minimal fuel
    case "Frozen": { 0.1 };  // frozen ground — minimal fuel
    case "Dusty":  { 0.8 };  // scrub / sparse dry fuel
    default        { 1.0 };  // grass (Normal, Mud)
};

// ─── Fuel moisture from humidity and recent rain ──────────────────────────
private _fuelMoisture = ((100 - _RH) / 100) + _rainAccum * 0.2;

// ─── Slope from 4 cardinal terrain samples at 50 m radius (percent) ───────
private _slopePct = 0;
private _player = call CBA_fnc_currentUnit;
if (!isNil "_player") then {
    private _pos2D = getPos _player;
    private _c = getTerrainHeightASL _pos2D;
    private _n = getTerrainHeightASL [_pos2D#0, (_pos2D#1) + 50];
    private _s = getTerrainHeightASL [_pos2D#0, (_pos2D#1) - 50];
    private _e = getTerrainHeightASL [(_pos2D#0) + 50, _pos2D#1];
    private _w = getTerrainHeightASL [(_pos2D#0) - 50, _pos2D#1];

    private _maxDiff = (abs (_c - _n)) max (abs (_c - _s)) max (abs (_c - _e)) max (abs (_c - _w));
    _slopePct = (_maxDiff / 50) * 100;
};

// ─── Rate of spread (Rothermel, simplified) ───────────────────────────────
private _ROS_mps = 0.03 * _fuelFactor * (1 + 0.2 * _windSpeed) * (1 + 0.1 * _slopePct) * exp (-_fuelMoisture * 0.05);

// ─── Fire area growth — growing circle ────────────────────────────────────
private _area = missionNamespace getVariable [QGVAR(fireArea_m2), 0];
private _perimeter = 2 * pi * sqrt (_area / pi);
_area = _area + _perimeter * _ROS_mps * _interval;
_area = _area max 0 min 1e6;

// ─── Danger index — normalised spread rate ────────────────────────────────
private _risk = (_ROS_mps / 1.0) min 1;

missionNamespace setVariable [QEGVAR(core,currentFireRisk), _risk];
missionNamespace setVariable [QGVAR(fireSpreadRate_mps), _ROS_mps];
missionNamespace setVariable [QGVAR(fireArea_m2), _area];

_risk
