#include "..\script_component.hpp"

// Wind vector is the REAL control mechanism for ACE3 ballistics/wind deflection.
// ACE3 reads Arma's built-in `wind` command, NOT a mission variable.
// So we call setWind to make our values propagate to ACE3.
// We ALSO store in EGVAR(core,currentWind) for internal AEE consumption.
private _wind = wind;
// gust is an engine weather variable that is undefined on a dedicated
// server (no local weather simulation). Guard it; the gust field is
// used for visual/audio FX only, so a zero default is safe.
private _gusts = 0;
if (!isNil {gust}) then { _gusts = gust; };

// Apply module wind multiplier (EDEN/Zeus)
private _moduleMult = missionNamespace getVariable [QEGVAR(core,moduleWindMultiplier), 1];
if (_moduleMult != 1) then { _wind = [_wind#0 * _moduleMult, _wind#1 * _moduleMult]; };

// Compute wind direction in meteorological convention (degrees from north, wind FROM)
// ACE3 uses: windDir = (wind#0 atan2 wind#1) + 180
private _windDir = ((_wind select 0) atan2 (_wind select 1)) + 180;
if (_windDir >= 360) then { _windDir = _windDir - 360; };

// Push to Arma engine so ACE3 ballistics/wind deflection picks it up
setWind [_wind select 0, _wind select 1, false];

// Store for our own functions
missionNamespace setVariable [QEGVAR(core,currentWind), _wind];
missionNamespace setVariable [QEGVAR(core,currentGusts), _gusts];
missionNamespace setVariable [QEGVAR(core,currentWindDir), _windDir];
