#include "..\..\script_component.hpp"
/*
Two-node core/skin temperature driver (issue #191).

Reads the engine state and the material registry, resolves the material
properties the kernel needs, calls the PURE kernel FUNC(solveTwoNodeKernel)
through the kernel dispatcher (native when the extension is ready, else the SQF
reference), publishes the human core temperature, and returns the pair.

This driver is the only place that reads the registry or writes the namespace,
so the kernel stays pure and portable.  The physics and its sources live in the
kernel file.

Arguments (unchanged for every caller):
  0: object (OBJECT) - retained for the caller arity; the physics is per
     selection and the kernel takes no engine handle
  1: selection name (STRING)
  2: core material class (STRING, from getMaterialThermal registry)
  3: skin material class (STRING)
  4: ambient temp (NUMBER, C)
  5: wind (NUMBER, m/s)
  6: solar flux (NUMBER, W/m2)
  7: shading exposure (NUMBER, 0..1)
  8: core mass (NUMBER, kg)
  9: skin mass (NUMBER, kg)
  10: surface area (NUMBER, m2)
  11: characteristic length (NUMBER, m)
  12: current core temp (NUMBER, C)
  13: current skin temp (NUMBER, C)
  14: internal generation (NUMBER, W)
  15: orientation (STRING)
  16: relative humidity (NUMBER, 0..1)
  17: mean radiant temperature (NUMBER, C)
  18: is human (BOOL)
  19: conduction length (NUMBER, m)
  20: evaporative path on (BOOL)
  21: time step (NUMBER, s)
  22: water speed (NUMBER, m/s)
  23: water temperature (NUMBER, C)
  24: rain rate (NUMBER, 0..1)
  25: skin perfusion index (NUMBER, 0..1)
  26: clothing insulation (NUMBER, clo)
  27: solar absorptance (NUMBER, 0..1) - -1 derives it from the skin material

Return:
  [coreTempC, skinTempC]
*/

params [
    ["_obj", objNull, [objNull]],
    ["_selection", "", [""]],
    ["_coreClass", "metal", [""]],
    ["_skinClass", "metal", [""]],
    ["_tAir", 15, [0]],
    ["_wind", 0, [0]],
    ["_solar", 0, [0]],
    ["_exposure", 1, [0]],
    ["_mCore", 50, [0]],
    ["_mSkin", 20, [0]],
    ["_area", 1.8, [0]],
    ["_lChar", 0.15, [0]],
    ["_tCore0", 36.8, [0]],
    ["_tSkin0", 33.7, [0]],
    ["_qGen", 0, [0]],
    ["_orientation", "vertical", [""]],
    ["_rh", 0.5, [0]],
    ["_mrtC", 15, [0]],
    ["_isHuman", false, [true]],
    ["_lCond", 0.05, [0]],
    ["_evapOn", true, [true]],
    ["_dt", 5, [0]],
    ["_waterSpeed", 0, [0]],
    ["_tWater", -273, [0]],
    ["_rain", 0, [0]],
    ["_skinPerfusion", 1, [0]],
    ["_clo", 0, [0]],
    ["_solarAlpha", 0, [0]]
];

// Material properties the kernel needs.  The registry read lives here, not in
// the kernel, so the kernel is a pure function of its arguments and a native
// port needs no registry.
private _coreMat = _coreClass call FUNC(getMaterialThermal);
private _skinMat = _skinClass call FUNC(getMaterialThermal);
private _skinEps = _skinMat select 0;
private _skinAlpha = if (_solarAlpha > 0) then { _solarAlpha } else { _skinMat select 1 };
// Fourier conductance of the inert (engine/building) path: k * A / L_cond with
// the lower of the two series conductivities.
private _cond = ((_coreMat select 4) min (_skinMat select 4)) * _area / (_lCond max 0.01);

private _args = [
    _tAir, _wind, _solar, _exposure,
    _mCore, _mSkin, _area, _lChar,
    _tCore0, _tSkin0, _qGen,
    _orientation, _rh, _mrtC,
    _isHuman, _evapOn, _dt,
    _waterSpeed, _tWater, _rain,
    _skinPerfusion, _clo,
    _cond, _skinEps, _skinAlpha
];

// The dispatcher selects the native kernel when the extension is ready, else
// the SQF reference kernel.  The native path returns a string the SQF kernel
// returns as an array, so normalise before reading the elements.
private _result = ["solveTwoNodeKernel", _args] call EFUNC(core,dispatchKernel);
if (_result isEqualType "") then { _result = parseSimpleArray _result; };
if !((_result isEqualType []) && {(count _result) >= 2}) exitWith {
    // A registered kernel always resolves; a malformed result is a bug, so
    // keep the persistent state rather than propagate a NaN.
    [_tCore0, _tSkin0]
};

private _tCoreNew = _result select 0;
private _tSkinNew = _result select 1;

// The human core temperature is published for the physiology handoff.  The
// kernel computes it from the last solve iteration; the write is the driver's.
if (_isHuman && _evapOn) then {
    missionNamespace setVariable ["aee_thermal_humanCoreTempC", (_result param [2, 0])];
};

[_tCoreNew, _tSkinNew]
