#include "..\script_component.hpp"

/*
Condensation / fogging on optical lenses (scope, binoculars, camera) 0–1.

Returns obscuration level where 0 = clear, 1 = fully fogged.

Condensation occurs when warm, humid air contacts a cold optical surface:
  • High humidity (>80 %) AND lens is cold (ambient between -5 °C and 15 °C)
    AND rapid warming (>3 °C/tick) — player moved from cold to warm environment
  • Early morning (06:00–08:00) with high humidity — natural dew point

Includes a breath-fog component (slight random blur per tick) when the
player is using optics in sub-zero conditions.

Once condensing conditions clear, obscuration decays to zero over time.

Stored in GVAR(dewOnOptics) and consumed by visual post-process overlay.
*/

params [];

// ─── Inputs ────────────────────────────────────────────────────────────────
private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _tAmbient = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _daytime  = dayTime;

// Humidity may be stored as 0–100 or 0–1; normalise
if (_humidity > 1) then { _humidity = _humidity / 100; };
_humidity = _humidity max 0 min 1;

// ─── Persisted state ───────────────────────────────────────────────────────
private _prevTemp = missionNamespace getVariable [QGVAR(dewPreviousTemp), _tAmbient];
private _fogTimer = missionNamespace getVariable [QGVAR(dewTimer), 0];

// ─── Temperature differential (warming rate °C/tick) ───────────────────────
private _tempDelta = _tAmbient - _prevTemp;

// ─── Condensation triggers ─────────────────────────────────────────────────
private _condense = false;

// Primary: humid + cold-ish lens + rapid warming (moved from cold to warm)
if (_humidity > 0.8 && {_tAmbient > -5 && {_tAmbient < 15 && (_tempDelta > 3)}}) then {
    _condense = true;
};

// Morning dew: 06:00–08:00 with high humidity
if (_daytime >= 6 && {_daytime <= 8 && (_humidity > 0.8)}) then {
    _condense = true;
};

// ─── Accumulate / decay fog timer ─────────────────────────────────────────
// Rates are per-tick; scale by the update interval so behaviour is
// interval-independent (5 s baseline).
private _intervalScale = (missionNamespace getVariable [QEGVAR(core,updateInterval), 5]) / 5;
private _accumRate = (missionNamespace getVariable [QGVAR(dewAccumRate), 0.05]) * _intervalScale;
private _decayRate = (missionNamespace getVariable [QGVAR(dewDecayRate), 0.02]) * _intervalScale;

if (_condense) then {
    _fogTimer = (_fogTimer + _accumRate) min 1;
} else {
    _fogTimer = (_fogTimer - _decayRate) max 0;
};

// ─── Breath-fog component (cold + scope usage) ────────────────────────────
private _breathFog = 0;
if (_tAmbient < 0 && (_fogTimer > 0)) then {
    _breathFog = random 0.05;
};

// ─── Final obscuration ─────────────────────────────────────────────────────
private _obscuration = (_fogTimer + _breathFog) min 1;

// ─── Store state ───────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(dewPreviousTemp), _tAmbient];
missionNamespace setVariable [QGVAR(dewTimer), _fogTimer];
missionNamespace setVariable [QGVAR(dewOnOptics), _obscuration];

_obscuration
