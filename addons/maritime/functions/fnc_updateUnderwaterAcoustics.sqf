#include "..\script_component.hpp"
/*
Underwater acoustics state (issue #113).

Computes and publishes the environmental acoustics of the sea at the local
unit's position, once per second:

  - surface sound speed, from the Mackenzie (1981) equation with the
    sea-surface temperature the maritime module publishes
    (fnc_calculateSoundSpeedWater);
  - the vertical sound-speed profile and its SOFAR channel axis
    (fnc_calculateSoundSpeedProfile, fnc_calculateSoundChannel);
  - the direct-path shadow zone below the thermocline
    (fnc_calculateShadowZone);
  - the seawater absorption at the reference frequency
    (fnc_calculateAbsorptionWater, Francois-Garrison 1982);
  - the ambient noise spectrum level at the reference frequency, keyed to
    the physical wind speed at 10 m (fnc_calculateAmbientNoise, Wenz 1962
    "rule of fives" plus the Mellen thermal limit).

The published variables are read by the sonar query
(fnc_getSonarDetectionRange) and by scenarios.  This driver does not decide
detection; it publishes the environment.  The sonar equation lives in
fnc_calculateSonarEquation and fnc_calculateDetectionRange.

The noise model is wind-driven, so the driver reads the wind speed the
atmosphere publishes (aee_core_currentWindStr, m/s at 10 m) and passes the
physical value.  The game's Beaufort sea state no longer feeds the noise
model, so no unsourced Beaufort-to-sea-state mapping remains.

Input:  [_depth] - source depth in metres (default: the local unit's depth)
Output: none.  Publishes the state variables below.
*/

params [["_depth", -1, [0]]];

private _windSpeed = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];
if !(_windSpeed isEqualType 0) then { _windSpeed = 0; };
if (_windSpeed <= 0) then {
    // Fallback: magnitude of the velocity vector, when the scalar is not
    // published yet (first tick) or is zero.
    private _windVec = missionNamespace getVariable [QEGVAR(core,currentWind), [0, 0]];
    if (_windVec isEqualType []) then {
        _windSpeed = vectorMagnitude _windVec;
    };
};

private _sst = missionNamespace getVariable [QGVAR(seaSurfaceTemperature), 15];
if !(_sst isEqualType 0) then { _sst = 15; };

private _salinity = missionNamespace getVariable [QGVAR(seaSalinity), 35];
if !(_salinity isEqualType 0) then { _salinity = 35; };

private _freqHz = missionNamespace getVariable [QGVAR(acousticReferenceFreqHz), 1000];
if !(_freqHz isEqualType 0) then { _freqHz = 1000; };

private _deepTemp = missionNamespace getVariable [QGVAR(deepWaterTemperature), 4];
if !(_deepTemp isEqualType 0) then { _deepTemp = 4; };

private _thermoclineDepth = missionNamespace getVariable [QGVAR(thermoclineDepth), 100];
if !(_thermoclineDepth isEqualType 0) then { _thermoclineDepth = 100; };

// Source depth: the explicit argument, else the local unit's depth.
if (_depth < 0) then {
    private _unit = call CBA_fnc_currentUnit;
    _depth = if (isNull _unit) then {
        0
    } else {
        private _z = (getPosASL _unit) select 2;
        0 max (-_z)
    };
};

// ─── Surface sound speed ──────────────────────────────────────────────────
private _cSurface = [_sst, _salinity, 0] call FUNC(calculateSoundSpeedWater);

// ─── Vertical profile and the SOFAR channel ───────────────────────────────
// 4000 m to the abyssal floor, 21 samples: fine enough to resolve the
// thermocline and the channel axis without a per-tick cost.
private _profile = [
    _sst, _thermoclineDepth, _deepTemp, _salinity, 4000, 21
] call FUNC(calculateSoundSpeedProfile);

private _channel = [_profile, 0] call FUNC(calculateSoundChannel);
private _axisDepth = _channel select 0;
private _axisSpeed = _channel select 1;

// ─── Direct-path shadow zone below the thermocline ────────────────────────
private _shadow = [_profile, _depth] call FUNC(calculateShadowZone);

// ─── Absorption and ambient noise at the reference frequency ──────────────
private _absorption = [_freqHz, _sst, _salinity, 0, 8.0] call FUNC(calculateAbsorptionWater);
private _noise = [_freqHz, _windSpeed, false] call FUNC(calculateAmbientNoise);

// ─── Publish ──────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(soundSpeedSurface), _cSurface];
missionNamespace setVariable [QGVAR(soundChannelAxisDepth_m), _axisDepth];
missionNamespace setVariable [QGVAR(soundChannelAxisSpeed), _axisSpeed];
missionNamespace setVariable [QGVAR(shadowZoneTop_m), _shadow select 0];
missionNamespace setVariable [QGVAR(shadowZoneBottom_m), _shadow select 1];
missionNamespace setVariable [QGVAR(absorptionDbPerKm), _absorption];
missionNamespace setVariable [QGVAR(ambientNoiseDb), _noise];

if (AEE_TRACE_ON) then {
    private _logMsg = format [
        "underwater acoustics | c=%1 m/s | axis=%2 m @ %3 m/s | shadow=%4..%5 m | alpha=%6 dB/km | NL=%7 dB",
        round (_cSurface * 10) / 10,
        round _axisDepth, round (_axisSpeed * 10) / 10,
        round (_shadow select 0), round (_shadow select 1),
        round (_absorption * 1000) / 1000,
        round _noise
    ];
    AEE_LOG_DEBUG(_logMsg);
};
