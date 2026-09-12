#include "..\script_component.hpp"

/*
Solar activity cycle (11-year), solar flares, Kp geomagnetic index,
and aurora visibility.

Computes:
  • Solar cycle activity from astronomical date (0–1)
  • Solar flare state machine: IDLE → ACTIVE (2–6 hr game time) → DECAYING
  • Kp geomagnetic index (0–9) from cycle + flare contribution + noise
  • Aurora visibility from Kp, overcast, nighttime, and latitude

Solar cycle uses a sine approximation referenced to the ~11 yr cycle
(4018 days ≈ 11 yr × 365.25 d/yr).

The radio propagation integrator in fn_calculateRadioPropagation reads
QGVAR(solarActivity) for HF band conditions.

Stored in GVAR(solarActivity), GVAR(kpIndex), GVAR(solarFlareActive),
GVAR(geomagneticDescription), GVAR(auroraVisibility),
GVAR(spaceWeatherFlareState), GVAR(spaceWeatherFlareTimer),
GVAR(spaceWeatherFlareValue).
*/

params [];

// ─── Date-based solar cycle (11-year approximation) ────────────────────────
// dateToNumber returns 0.0 at Jan 1 00:00, ~1.0 at Dec 31 24:00
private _dateArr   = date;
_dateArr params [["_year", 2024]];

private _yearFrac   = dateToNumber _dateArr;
private _dayOfYear  = _yearFrac * 365.25;              // day number within the year
private _totalDays  = _dayOfYear + _year * 365.25;     // absolute days since year 0
private _solarCycle = (sin (360 * _totalDays / 4018) + 1) / 2; // 0–1

// ─── Solar flare state machine ────────────────────────────────────────────
// States:  IDLE  →  ACTIVE  →  DECAYING  →  IDLE
//          (background)  (peak held)  (-0.05/tick)

private _flareState = missionNamespace getVariable [QGVAR(spaceWeatherFlareState), "IDLE"];
private _flareValue = missionNamespace getVariable [QGVAR(spaceWeatherFlareValue), 0];

switch (_flareState) do {
    case "IDLE": {
        // 5 % chance per tick to trigger when cycle > 0.6
        if ((_solarCycle > 0.6) && (([round (time * 10), 401] call EFUNC(core,deterministicRandom)) < 0.05)) then {
            _flareValue = _solarCycle * (0.3 + (0.4 * ([round (time * 10), 402] call EFUNC(core,deterministicRandom))));
            missionNamespace setVariable [QGVAR(spaceWeatherFlareEndTime), time + 7200 + (14400 * ([round (time * 10), 403] call EFUNC(core,deterministicRandom)))];
            _flareState = "ACTIVE";
        };
    };

    case "ACTIVE": {
        // Hold peak value until end time; timer tracks remaining game-seconds
        private _endTime = missionNamespace getVariable [QGVAR(spaceWeatherFlareEndTime), time];
        if (time >= _endTime) then {
            _flareState = "DECAYING";
        };
    };

    case "DECAYING": {
        _flareValue = _flareValue - 0.05;
        if (_flareValue <= 0) then {
            _flareValue  = 0;
            _flareState  = "IDLE";
        };
    };
};

// ─── Flare timer — remaining game seconds in current phase ────────────────
private _flareTimer = switch (_flareState) do {
    case "ACTIVE": {
        ((missionNamespace getVariable [QGVAR(spaceWeatherFlareEndTime), time]) - time) max 0
    };
    default { 0 };
};

// ─── Kp geomagnetic index (0–9) ──────────────────────────────────────────
// Base 1 + 11-yr cycle contribution + flare contribution + noise
private _kpRaw   = 1 + (_solarCycle * 4) + _flareValue + (-1 + (2 * ([round (time * 10), 404] call EFUNC(core,deterministicRandom))));
private _kpIndex = round (_kpRaw max 0 min 9);

// ─── Geomagnetic description ──────────────────────────────────────────────
private _geoDesc = switch (true) do {
    case (_kpIndex < 3):  { "Quiet" };
    case (_kpIndex < 6):  { "Active" };
    case (_kpIndex < 8):  { "Storm" };
    default               { "Severe Storm" };
};

// ─── Solar activity (background + flare for radio propagation) ────────────
private _solarActivity = (_solarCycle + _flareValue) min 1;

// ─── Aurora visibility ────────────────────────────────────────────────────
// Requires: elevated geomagnetic activity, clear sky, nighttime
// (before 06:00 OR after 20:00 — grouped so the OR binds correctly),
// and high latitude (>45° N/S).  The world latitude comes from the map
// config, not a crude Y/100000 approximation (which on a 30 km map
// never exceeds 27° and would make aurora impossible).
private _overcast = overcast;
private _daytime  = dayTime;

private _worldLat = getNumber (configFile >> "CfgWorlds" >> worldName >> "latitude");
private _latDeg = abs _worldLat;
if (_latDeg == 0) then { _latDeg = 45; };  // fallback: temperate, aurora possible at storm level

private _aurora = _kpIndex > 4
    && (_overcast < 0.3)
    && ((_daytime < 6) || (_daytime > 20))
    && (_latDeg > 45);

// ─── Store ────────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(solarActivity),              _solarActivity];
missionNamespace setVariable [QGVAR(kpIndex),                    _kpIndex];
missionNamespace setVariable [QGVAR(solarFlareActive),           _flareState != "IDLE"];
missionNamespace setVariable [QGVAR(geomagneticDescription),     _geoDesc];
missionNamespace setVariable [QGVAR(auroraVisibility),           _aurora];
missionNamespace setVariable [QGVAR(spaceWeatherFlareState),     _flareState];
missionNamespace setVariable [QGVAR(spaceWeatherFlareTimer),     _flareTimer];
missionNamespace setVariable [QGVAR(spaceWeatherFlareValue),     _flareValue];

_solarActivity
