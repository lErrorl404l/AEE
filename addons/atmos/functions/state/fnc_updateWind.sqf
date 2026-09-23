#include "..\..\script_component.hpp"

// Wind vector is the REAL control mechanism for ACE3 ballistics/wind deflection.
// ACE3 reads Arma's built-in `wind` command, NOT a mission variable.
// So we call setWind to make our values propagate to ACE3.
// We ALSO store in EGVAR(core,currentWind) for internal AEE consumption.
private _wind = wind;
// gust is an engine weather variable that is undefined on a dedicated
// server (no local weather simulation). Guard it; the gust field is
// used for visual/audio FX only, so a zero default is safe.
//
// The gust setting is the relative frequency of gust events (0 calm, 1
// very gusty). It scales the engine's own gust signal, which supplies the
// timing, so the setting controls how much gust the atmosphere carries
// without replacing the engine's natural cycle.
private _gusts = 0;
if (!isNil {gust}) then { _gusts = gust; };
private _gustFreq = missionNamespace getVariable [QEGVAR(core,windGustFrequency), 0.3];
if !(_gustFreq isEqualType 0) then { _gustFreq = 0.3; };
_gustFreq = _gustFreq max 0 min 1;
_gusts = _gusts * (_gustFreq * 2);

// Apply module wind multiplier (EDEN/Zeus)
private _moduleMult = missionNamespace getVariable [QEGVAR(core,moduleWindMultiplier), 1];

// Only call setWind when the multiplier actually changes the vector.
// Calling setWind every tick (even with the same values) resets the
// engine's natural gust cycle and can cause visual artefacts during
// skip-time or rapid weather transitions.
if (_moduleMult != 1) then {
    _wind = [_wind#0 * _moduleMult, _wind#1 * _moduleMult];
    setWind [_wind select 0, _wind select 1, false];
};

// Compute wind direction in meteorological convention (degrees from north, wind FROM)
// ACE3 uses: windDir = (wind#0 atan2 wind#1) + 180
private _windDir = ((_wind select 0) atan2 (_wind select 1)) + 180;
if (_windDir >= 360) then { _windDir = _windDir - 360; };

// Wind strength (m/s magnitude) — scalar form of the vector for modules
// that only need intensity (scent dispersal, glare, sound).
private _windStr = vectorMagnitude _wind;

// ─── Terrain speed-up ────────────────────────────────────────────────────
// Wind accelerates over a ridge crest and slows in the lee. The published
// guideline (Taylor and Lee 1984) gives the fractional speed-up as
// dS = 2 (h/L) sigma; fnc_calculateTerrainWind holds it. The setting gates
// and scales the effect.
private _terrainSetting = missionNamespace getVariable [QEGVAR(core,windTerrainInfluence), 0.6];
if !(_terrainSetting isEqualType 0) then { _terrainSetting = 0.6; };
if (_terrainSetting > 0) then {
    private _unit = call CBA_fnc_currentUnit;
    if (!isNil "_unit" && {!isNull _unit}) then {
        private _multiplier = [getPosASL _unit, _terrainSetting] call FUNC(calculateTerrainWind);
        _wind = _wind vectorMultiply _multiplier;
        _windStr = _windStr * _multiplier;
    };
};

// Store for our own functions
missionNamespace setVariable [QEGVAR(core,currentWind), _wind];
missionNamespace setVariable [QEGVAR(core,currentGusts), _gusts];
missionNamespace setVariable [QEGVAR(core,currentWindDir), _windDir];
missionNamespace setVariable [QEGVAR(core,currentWindStr), _windStr];
