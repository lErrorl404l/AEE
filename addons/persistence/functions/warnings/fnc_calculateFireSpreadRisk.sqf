#include "..\..\script_component.hpp"

/*
Vegetation fire spread — Rothermel (1972) rate of spread with Simard (1968)
dead-fuel moisture and Byram (1959) fireline intensity.

This replaces the earlier heuristic spread rate.  The physics lives in four
pure kernels:

  FUNC(equilibriumMoisture)     Simard EMC from air temperature and humidity
  FUNC(fuelMoistureResponse)    timelag relaxation of a dead fuel class
  FUNC(rothermelSpread)         Rothermel steady rate of spread
  FUNC(byramIntensity)          Byram fireline intensity and flame length
  FUNC(fuelModelParams)         Albini standard fuel-model parameters

The vegetation response selects a standard fuel model from the ground state
and the biome: dense-canopy and continental biomes burn as closed timber
litter (fuel model 8), arid and Mediterranean biomes as brush (fuel model 5),
and the rest as short grass (fuel model 1).  Snow and frozen ground carry no
surface fuel.  Live fuel moisture follows herbaceous curing: dormant cover is
near 30 percent, full green cover near 120 percent (crown-fire gate input).

Precipitation enters through the humidity state (the relative-humidity kernel
saturates toward the dew point under overcast or rain), so no separate rain
term is needed.

Stores:
  QEGVAR(core,currentFireRisk)   — danger index 0–1 (spread rate / 1 m/s)
  QGVAR(fireSpreadRate_mps)      — rate of spread (m/s)
  QGVAR(fireArea_m2)             — integrated fire area (m^2)
  QGVAR(fireIntensity_kWm)       — Byram fireline intensity (kW/m)
  QGVAR(flameLength_m)           — Byram flame length (m)
  QGVAR(fuelMoisture_1h)         — fine (1-hour) dead fuel moisture (fraction)
  QGVAR(fuelMoisture_10h)        — 10-hour dead fuel moisture (fraction)
  QGVAR(fuelMoisture_100h)       — 100-hour dead fuel moisture (fraction)
  QGVAR(fuelMoisture_live)       — live fuel moisture (fraction)
  QGVAR(fuelModel)               — active fuel model id
*/

private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _tempC = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _biome = missionNamespace getVariable [QEGVAR(core,biome), "Cfb"];
private _cropDensity = missionNamespace getVariable [QEGVAR(core,currentCropDensity), 0.3];
private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
private _windSpeed = vectorMagnitude wind;

// ─── Vegetation response: fuel model from ground state and biome ──────────
// The biome-to-fuel-type mapping is an engine modelling choice (the biome
// codes are Köppen).  The fuel MODEL parameters are the Albini standard ones.
private _fuelModel = "grass";
private _fuelAvailable = true;
if ((_groundState isEqualTo "Snow") || (_groundState isEqualTo "Frozen")) then {
    _fuelAvailable = false;
} else {
    if (_biome in ["BWh", "BWk", "BSh", "BSk", "Csa", "Csb"]) then {
        _fuelModel = "scrub";
    };
    if (_biome in ["Af", "Am", "Cfa", "Cfb", "Cwa", "Dfa", "Dfb", "Dfc"]) then {
        _fuelModel = "forest";
    };
};

// ─── Dead fuel moisture: Simard EMC + timelag (1 / 10 / 100 h classes) ─────
private _emc = [_tempC, _humidity] call FUNC(equilibriumMoisture);
private _m1h = missionNamespace getVariable [QGVAR(fuelMoisture_1h), _emc];
private _m10h = missionNamespace getVariable [QGVAR(fuelMoisture_10h), _emc];
private _m100h = missionNamespace getVariable [QGVAR(fuelMoisture_100h), _emc];
_m1h = [_m1h, _emc, _interval, 1] call FUNC(fuelMoistureResponse);
_m10h = [_m10h, _emc, _interval, 10] call FUNC(fuelMoistureResponse);
_m100h = [_m100h, _emc, _interval, 100] call FUNC(fuelMoistureResponse);

// ─── Live fuel moisture: herbaceous curing from vegetation greenness ───────
private _liveMoisture = 0.30 + (_cropDensity * 0.90);

// ─── Slope: tangent of the terrain angle from 4 samples at 50 m ────────────
private _slopeTan = 0;
private _player = call CBA_fnc_currentUnit;
if (!isNil "_player" && {!isNull _player}) then {
    private _pos2D = getPos _player;
    private _c = getTerrainHeightASL _pos2D;
    private _n = getTerrainHeightASL [_pos2D#0, (_pos2D#1) + 50];
    private _s = getTerrainHeightASL [_pos2D#0, (_pos2D#1) - 50];
    private _e = getTerrainHeightASL [(_pos2D#0) + 50, _pos2D#1];
    private _w = getTerrainHeightASL [(_pos2D#0) - 50, _pos2D#1];
    private _maxDiff = (abs (_c - _n)) max (abs (_c - _s)) max (abs (_c - _e)) max (abs (_c - _w));
    _slopeTan = _maxDiff / 50;
};

// ─── Rothermel rate of spread and Byram intensity ─────────────────────────
private _ros = 0;
private _intensity = 0;
private _flame = 0;
if (_fuelAvailable) then {
    private _params = [_fuelModel] call FUNC(fuelModelParams);
    private _sigma = _params select 0;
    private _w0 = _params select 1;
    private _delta = _params select 2;
    private _mx = _params select 3;
    _ros = [_sigma, _w0, _delta, _m1h, _mx, _windSpeed, _slopeTan] call FUNC(rothermelSpread);
    private _byram = [18700, _w0, _ros] call FUNC(byramIntensity);
    _intensity = _byram select 0;
    _flame = _byram select 1;
};

// ─── Fire area growth — growing circle ────────────────────────────────────
private _area = missionNamespace getVariable [QGVAR(fireArea_m2), 0];
private _perimeter = 2 * pi * sqrt (_area / pi);
_area = _area + _perimeter * _ros * _interval;
_area = _area max 0 min 1e6;

// ─── Danger index — spread rate against the 1 m/s extreme reference ───────
private _risk = (_ros / 1.0) min 1;

missionNamespace setVariable [QEGVAR(core,currentFireRisk), _risk];
missionNamespace setVariable [QGVAR(fireSpreadRate_mps), _ros];
missionNamespace setVariable [QGVAR(fireArea_m2), _area];
missionNamespace setVariable [QGVAR(fireIntensity_kWm), _intensity];
missionNamespace setVariable [QGVAR(flameLength_m), _flame];
missionNamespace setVariable [QGVAR(fuelMoisture_1h), _m1h];
missionNamespace setVariable [QGVAR(fuelMoisture_10h), _m10h];
missionNamespace setVariable [QGVAR(fuelMoisture_100h), _m100h];
missionNamespace setVariable [QGVAR(fuelMoisture_live), _liveMoisture];
missionNamespace setVariable [QGVAR(fuelModel), _fuelModel];

_risk
