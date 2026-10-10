#include "..\..\script_component.hpp"
/*
Radar detection query (issue #104) - one radar, one target.

Computes the maximum detection range for a radar-target pair as the
minimum of the noise, clutter and horizon limits, with the evaporation
duct applied when it traps.  This is the issue's recommended per-target
query (steps 1-6).

Reads:
  EGVAR(atmos,refractivityGradient)   N/km (published by fnc_calculateRefraction)
  EGVAR(core,currentTemperature)      C
  EGVAR(maritime,seaSurfaceTemperature)  C (nil when maritime is off)
  EGVAR(core,seaStateBeaufort)        Douglas sea state
  QGVAR(radarDetection)               the module switch
Writes nothing.

Radar config array (fixed order):
  0  peak transmit power P_t, W
  1  antenna gain G, linear
  2  wavelength lambda, m
  3  frequency, Hz
  4  bandwidth, Hz
  5  noise figure F_n, linear
  6  required SNR, linear
  7  azimuth beamwidth theta_az, rad
  8  pulse width tau, s
  9  target-to-clutter ratio TCR_min
  10 antenna height, m
  11 polarisation, "VV" or "HH"

Duct height delta (Paulus-Jeske, mirroring issue #37):
  delta = clamp(1.5 + (T_air - T_sea) * 2.5, 3, 25) m.  Without a sea
  temperature there is no evaporation duct, so delta = 0.

Arguments:
  0: Array - radar position, ASL
  1: Array - radar config (the array above)
  2: Array - target position, ASL
  3: String - target class token
  4: Number - target height, m

Returns:
  Array - [range m, limiting factor, detected]
*/
params [
    ["_radarPos", [0, 0, 0], [[]]],
    ["_radar", [], [[]]],
    ["_targetPos", [0, 0, 0], [[]]],
    ["_targetClass", "", [""]],
    ["_targetHeight", 0, [0]]
];

if (!(missionNamespace getVariable [QGVAR(radarDetection), false])) exitWith {
    [0, "disabled", false]
};
if (count _radar < 12) exitWith { [0, "invalid", false] };

private _pt = _radar select 0;
private _gain = _radar select 1;
private _lambda = _radar select 2;
private _freqHz = _radar select 3;
private _bandwidth = _radar select 4;
private _noiseFigure = _radar select 5;
private _snrMin = _radar select 6;
private _thetaAz = _radar select 7;
private _tau = _radar select 8;
private _tcrMin = _radar select 9;
private _radarHeight = _radar select 10;
private _polarisation = _radar select 11;

private _slant = _radarPos distance _targetPos;
private _heightDiff = _targetHeight - _radarHeight;
private _ground = sqrt ((_slant ^ 2) - (_heightDiff ^ 2)) max 1;
private _grazing = (abs _heightDiff) atan2 _ground;

private _gradient = missionNamespace getVariable [QEGVAR(atmos,refractivityGradient), -39];
if !(_gradient isEqualType 0) then { _gradient = -39; };

private _temp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _sst = missionNamespace getVariable [QEGVAR(maritime,seaSurfaceTemperature), nil];
private _delta = 0;
if (!isNil "_sst" && _sst isEqualType 0) then {
    _delta = ((1.5 + ((_temp - _sst) * 2.5)) max 3) min 25;
};

private _seaState = missionNamespace getVariable [QEGVAR(core,seaStateBeaufort), 3];
if !(_seaState isEqualType 0) then { _seaState = 3; };

private _exponent = [_delta, _freqHz, _gradient, _radarHeight, _targetHeight] call FUNC(radarDuctRange);
private _ducted = _exponent < 4;

private _pmin = [_bandwidth, _noiseFigure, _snrMin] call FUNC(radarNoiseFloor);
private _sigma = [_targetClass] call FUNC(radarRcs);
private _noiseRmax = [_pt, _gain, _lambda, _sigma, _pmin, _exponent] call FUNC(radarRangeEquation);

private _sigma0 = [_grazing, (_freqHz / 1e9), _seaState, _polarisation] call FUNC(radarSeaClutter);
private _clutterRmax = [_sigma, _sigma0, _thetaAz, _tau, _grazing, _tcrMin] call FUNC(radarClutterRange);

private _horizonM = ([_radarHeight, _targetHeight] call FUNC(radarHorizon)) * 1000;

private _limits = [_noiseRmax, _clutterRmax, _horizonM, _ducted] call FUNC(radarDetectionRange);
private _rdet = _limits select 0;
private _limiting = _limits select 1;

private _detected = (_slant > 0) && (_slant <= _rdet);

[_rdet, _limiting, _detected]
