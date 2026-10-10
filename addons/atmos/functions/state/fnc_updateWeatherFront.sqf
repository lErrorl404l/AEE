#include "..\..\script_component.hpp"

/*
Weather front state and forcing (issue #15).

Computes the Bergen life-cycle front (FUNC(calculateWeatherFront)), the
signed distance from the observer (FUNC(calculateFrontDistance)) and the
phase factor (FUNC(calculateFrontPhase)), publishes the front state, and
applies the phase factor to the existing atmospheric state:

  temperature  = T + warmSide * f * contrast/2   (the contrast step)
  pressure     = P - trough * (1 - |f|)          (the trough at the front line)

The wind veer and the cloud trend are published as forcing terms
(aee_atmos_frontWindVeerDeg, aee_atmos_frontCloudTerm) that FUNC(updateWind)
and FUNC(calculateCloudDevelopment) fold into their own kernels, and the
frontal precipitation signature is published as aee_atmos_frontPrecipRate and
aee_atmos_frontPrecipPhase.

The pressure perturbation is applied before FUNC(calculatePressureTrend), so
the existing 3-hour pressure-trend ring buffer reports the fall, the trough
and the rise of a passage without a second trend model.

The whole front is gated on the computed weather: in Real Weather mode the
mission supplies the real temperature and pressure, so the front must not
overwrite them.

Reads:  aee_core_currentTemperature, aee_core_currentPressure,
        aee_core_realWeatherActive, aee_core_weatherProgressionSeed
Sets:   aee_atmos_front* (state), aee_core_currentTemperature,
        aee_core_currentPressure

Arguments:
  0: reference position ASL (Array)
Public: No
*/

params [["_posASL", [], [[]]]];

if (!GVAR(weatherFrontsEnabled)) exitWith {};

// A wrapped single-element form [[x, y, z]] arrives from the docker edge-case
// phase; unwrap it (the same normalisation the core tick does).
if ((count _posASL) == 1 && {(_posASL select 0) isEqualType []}) then {
    _posASL = _posASL select 0;
};

if (missionNamespace getVariable [QEGVAR(core,realWeatherActive), false]) exitWith {};

private _seed = missionNamespace getVariable [QEGVAR(core,weatherProgressionSeed), 0.5];
if !(_seed isEqualType 0) then { _seed = 0.5; };

private _front = [time, _seed] call FUNC(calculateWeatherFront);
private _type      = _front select 0;
private _speedKmh  = _front select 1;
private _contrast  = _front select 2;
private _halfWidth = _front select 3;
private _veerDeg   = _front select 4;
private _trough    = _front select 5;
private _cloudMag  = _front select 6;
private _precipMmH = _front select 7;
private _warmSide  = _front select 8;
private _bearing   = _front select 9;
private _frontDist = _front select 10;

// The anchor is the map centre; the front sweeps across the map along its
// bearing.  Fall back to the world-size centre if the config has no entry.
private _anchor = getArray (configFile >> "CfgWorlds" >> worldName >> "centerPosition");
if ((count _anchor) < 2) then { _anchor = [worldSize / 2, worldSize / 2]; };

private _observer2D = [];
if ((count _posASL) >= 2) then {
    _observer2D = [_posASL select 0, _posASL select 1];
} else {
    private _unit = call CBA_fnc_currentUnit;
    if (!isNil "_unit" && {!isNull _unit}) then { _observer2D = getPos _unit; };
};
if ((count _observer2D) < 2) then { _observer2D = _anchor; };

private _distanceKm = [_observer2D, _anchor, _bearing, _frontDist] call FUNC(calculateFrontDistance);
private _phase = [_distanceKm, _halfWidth] call FUNC(calculateFrontPhase);
private _absPhase = abs _phase;

// ─── Publish the front state (the visualisation surface) ────────────────────
missionNamespace setVariable [QGVAR(frontActive), true];
missionNamespace setVariable [QGVAR(frontType), _type];
missionNamespace setVariable [QGVAR(frontPhase), _phase];
missionNamespace setVariable [QGVAR(frontDistanceKm), _distanceKm];
missionNamespace setVariable [QGVAR(frontSpeedKmh), _speedKmh];
missionNamespace setVariable [QGVAR(frontBearingDeg), _bearing];
missionNamespace setVariable [QGVAR(frontContrastC), _contrast];

// ─── Temperature: the contrast step ─────────────────────────────────────────
// The warm side sits at f = +1 for a cold front (warm air ahead) and at
// f = -1 for a warm front (warm air behind), so warmSide carries the sign.
// Across the front the step is the full contrast.
private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if (_T isEqualType 0) then {
    private _Tf = _T + _warmSide * _phase * (_contrast / 2);
    missionNamespace setVariable [QEGVAR(core,currentTemperature), round (_Tf * 10) / 10];
};

// ─── Pressure: the trough ────────────────────────────────────────────────────
// The pressure is lowest on the front line and rises into both air masses:
// 1-3 hPa below the surroundings ahead, then a rise behind (FAA AC 00-6B).
private _P = missionNamespace getVariable [QEGVAR(core,currentPressure), 1013.25];
if (_P isEqualType 0) then {
    private _Pf = _P - _trough * (1 - _absPhase);
    missionNamespace setVariable [QEGVAR(core,currentPressure), round (_Pf * 10) / 10];
};

// ─── Wind veer (forcing for fnc_updateWind) ──────────────────────────────────
// Clockwise veer of veerDeg/2 to either side of the base direction, so the
// swing across the passage is the full veerDeg (40-90 deg, FAA AC 00-6B).
missionNamespace setVariable [QGVAR(frontWindVeerDeg), -_phase * (_veerDeg / 2)];

// ─── Cloud trend (forcing for fnc_calculateCloudDevelopment) ─────────────────
// Building ahead of the front, clearing behind it.
missionNamespace setVariable [QGVAR(frontCloudTerm), _phase * _cloudMag];

// ─── Frontal precipitation signature ─────────────────────────────────────────
// The intrinsic frontal rate at the line, tapering to zero at the zone edge.
// Cold fronts are showery (10-50 mm/h), warm fronts steady (1-10 mm/h) (WMO).
private _precipRate = _precipMmH * (1 - _absPhase);
missionNamespace setVariable [QGVAR(frontPrecipRate), _precipRate];

private _precipPhase = ["rain", "snow"] select (_T <= 0);
missionNamespace setVariable [QGVAR(frontPrecipPhase), _precipPhase];
