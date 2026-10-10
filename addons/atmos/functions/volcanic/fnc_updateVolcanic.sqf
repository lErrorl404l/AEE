#include "..\..\script_component.hpp"

/*
Per-tick volcanic activity orchestrator.

Reads the eruption parameters (published by the EDEN module or the defaults),
computes the ash, SO2, lahar and volcanic-winter state at the observer
position, and publishes it.  The kernels are:
  calculatePlumeRise        Briggs buoyant plume rise
  calculateGaussianPlume    Pasquill-Gifford dispersion
  calculateAshSettling      Stokes settling
The models are calculateVolcanicAsh, calculateSO2Plume, calculateLaharRisk
and calculateVolcanicWinter.

The plume rise is capped at the stratospheric umbrella (20 km above the
vent): Briggs was calibrated on combustion plumes and the rise is not
physical for a Plinian column, which spreads laterally at the neutral level.

Sets (all GVAR, in aee_atmos):
  volcanicActive, volcanicAshConcentrationMgM3, volcanicAshDepth_mm,
  volcanicAshVisibilityKm, volcanicAshState, volcanicAshIntensity,
  volcanicSO2_ppm, volcanicSO2Band, volcanicLaharRisk,
  volcanicWinterCooling_C, volcanicWinterRegionalCooling_C

Sources: see the kernel and model headers; issue #25.
*/

params [["_posASL", [], [[]]]];

if (!(missionNamespace getVariable [QGVAR(volcanicEnabled), false])) exitWith {};

// Normalise the observer position.
if ((count _posASL) == 1 && {(_posASL select 0) isEqualType []}) then {
    _posASL = _posASL select 0;
};
if (count _posASL < 2) then {
    private _unit = call CBA_fnc_currentUnit;
    if (!isNil "_unit" && {!isNull _unit}) then { _posASL = getPosASL _unit; };
};
if (count _posASL < 2) exitWith {};

// ─── Eruption source ────────────────────────────────────────────────────────
private _volcano = missionNamespace getVariable [QGVAR(volcanoPosition), []];
if !(_volcano isEqualType [] && {(count _volcano) >= 2}) exitWith {
    missionNamespace setVariable [QGVAR(volcanicActive), false];
};

private _vei         = missionNamespace getVariable [QGVAR(volcanoVEI), 5];
private _ventAlt     = missionNamespace getVariable [QGVAR(volcanoVentAltitude), 2000];
private _ashEmission = missionNamespace getVariable [QGVAR(volcanoAshEmission), 5.0e6];
private _so2Emission = missionNamespace getVariable [QGVAR(volcanoSO2Emission), 5.0e5];
private _heatFlux    = missionNamespace getVariable [QGVAR(volcanoHeatFlux), 1.0e11];

// ─── Wind and geometry ──────────────────────────────────────────────────────
private _wind = wind;
private _windSpeed = vectorMagnitude _wind;
private _windUnit = _wind vectorMultiply (1 / (_windSpeed max 1.0e-3));

private _rel = [
    (_posASL select 0) - (_volcano select 0),
    (_posASL select 1) - (_volcano select 1),
    0
];
private _downwind = _rel vectorDotProduct _windUnit;
private _along = _windUnit vectorMultiply _downwind;
private _crosswind = vectorMagnitude (_rel vectorDiff _along);

// ─── Pasquill stability from wind and insolation ────────────────────────────
private _stability = "D";
if ((_windSpeed < 6) && (overcast < 0.7)) then {
    private _solar = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), 0];
    if !(_solar isEqualType 0) then { _solar = 0; };
    private _hour = dayTime;
    private _daytime = (_hour > 6) && (_hour < 18);
    if (_daytime) then {
        if ((_solar > 0.5) && (_windSpeed < 3)) then { _stability = "A"; }
        else { if (_solar > 0.3) then { _stability = "B"; } else { _stability = "C"; }; };
    } else {
        if (_windSpeed < 3) then { _stability = "F"; } else { _stability = "E"; };
    };
};

// ─── Plume rise and effective height ────────────────────────────────────────
private _temp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_temp isEqualType 0) then { _temp = 15; };
private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
if !(_rho isEqualType 0) then { _rho = 1.225; };

private _rise = [_heatFlux, _windSpeed, _stability, _temp, _rho] call FUNC(calculatePlumeRise);
private _plumeHeight = _ventAlt + (_rise min 20000);

// ─── Ash ────────────────────────────────────────────────────────────────────
private _ash = [_downwind, _crosswind, _ashEmission, _windSpeed, _stability, _plumeHeight]
    call FUNC(calculateVolcanicAsh);

private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
private _depth_mm = missionNamespace getVariable [QGVAR(volcanicAshDepth_mm), 0];
if !(_depth_mm isEqualType 0) then { _depth_mm = 0; };
// deposition kg/(m2 s) * dt / bulk density (1000 kg/m3) -> m -> mm
_depth_mm = _depth_mm + ((_ash get "depositionRate") * _interval / 1000 * 1000);

// ─── SO2 ────────────────────────────────────────────────────────────────────
private _pressure = missionNamespace getVariable [QEGVAR(core,currentPressure), 101325];
if !(_pressure isEqualType 0) then { _pressure = 101325; };
private _so2 = [_downwind, _crosswind, _so2Emission, _windSpeed, _stability, _plumeHeight, 1.5, _temp, _pressure]
    call FUNC(calculateSO2Plume);

// ─── Lahar ──────────────────────────────────────────────────────────────────
// Rain on the loose ash deposit; the accumulated depth is the deposit.
private _rainMMH = rain * 25;
private _slopeDeg = missionNamespace getVariable [QGVAR(volcanoSlope), 15];
if !(_slopeDeg isEqualType 0) then { _slopeDeg = 15; };
private _lahar = [1, _rainMMH, _depth_mm / 1000, _slopeDeg] call FUNC(calculateLaharRisk);

// ─── Volcanic winter ────────────────────────────────────────────────────────
private _latitude = missionNamespace getVariable [QGVAR(volcanoLatitude), 45];
if !(_latitude isEqualType 0) then { _latitude = 45; };
private _winter = [_vei, _latitude, true] call FUNC(calculateVolcanicWinter);

// ─── Publish ────────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(volcanicActive), true];
missionNamespace setVariable [QGVAR(volcanicAshConcentrationMgM3), _ash get "concentrationMgM3"];
missionNamespace setVariable [QGVAR(volcanicAshDepth_mm), _depth_mm];
missionNamespace setVariable [QGVAR(volcanicAshVisibilityKm), _ash get "visibilityKm"];
missionNamespace setVariable [QGVAR(volcanicAshState), _ash get "state"];
missionNamespace setVariable [QGVAR(volcanicAshIntensity), _ash get "intensity"];
missionNamespace setVariable [QGVAR(volcanicSO2_ppm), _so2 get "ppm"];
missionNamespace setVariable [QGVAR(volcanicSO2Band), _so2 get "band"];
missionNamespace setVariable [QGVAR(volcanicLaharRisk), _lahar get "risk"];
missionNamespace setVariable [QGVAR(volcanicWinterCooling_C), _winter get "globalCooling"];
missionNamespace setVariable [QGVAR(volcanicWinterRegionalCooling_C), _winter get "regionalCooling"];

if (AEE_TRACE_ON) then {
    private _msg = format [
        "volcanic | VEI=%1 plume=%2m ash=%3mg/m3 depth=%4mm vis=%5km SO2=%6ppm/%7 lahar=%8 winter=%9C",
        _vei, round _plumeHeight,
        [_ash get "concentrationMgM3", 3] call CBA_fnc_formatNumber,
        round _depth_mm, [_ash get "visibilityKm", 2] call CBA_fnc_formatNumber,
        [_so2 get "ppm", 3] call CBA_fnc_formatNumber, _so2 get "band",
        [_lahar get "risk", 2] call CBA_fnc_formatNumber,
        [_winter get "globalCooling", 2] call CBA_fnc_formatNumber
    ];
    AEE_LOG_DEBUG(_msg);
};
