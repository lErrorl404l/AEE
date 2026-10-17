#include "..\..\script_component.hpp"
/*
Space weather from real records: sunspot number, solar X-ray flares, the
Kp geomagnetic index and the aurora.

Sunspot number (SSN): the monthly series of fnc_getSpaceWeatherData (SILSO
smoothed record, the NOAA SWPC prediction, then mean Hathaway cycles), read
at the MISSION date and interpolated between months.  Setting
aee_weather_sunspotOverride (>= 0) replaces it.

Kp: a 3-hour Markov chain whose transition probabilities are counted from
the GFZ Kp record since 1932, in the sunspot bin of the current SSN, so
storms arise, persist and decay as observed.  It advances once per 3-hour
UT block of the game clock (a time skip advances it block by block, up to
a day; a longer skip restarts it).  Setting aee_weather_kpOverride (>= 0)
pins it.

Flares: M and X class events arrive as a Poisson process at the GOES-fitted
rate a * SSN^b per year (1976-2016 reports); each takes a peak magnitude,
rise and decay time from the empirical GOES quantiles.  The 1-8 A X-ray
flux rises linearly to the peak and decays exponentially, the GOES end time
being the half-recovery (tau = decay / ln 2).  The flare's HF effect is
NOAA SWPC D-RAP: HAF = 10 log10(flux W/m2) + 65 MHz at the sub-solar
point, scaled by (cos chi)^0.75 elsewhere, with absorption
A(f) = (HAF / f)^1.5 dB.

Aurora: the equatorward edge of the oval sits near 66 deg geomagnetic
latitude at Kp 0 and moves about 2 deg per Kp level (NOAA SWPC, "Tips on
viewing the aurora").  The geomagnetic latitude is the WMM2025 dipole
(aee_magnetism_fnc_geomagneticLatitude).  An aurora whose lower border is
at 110 km is above the observer's horizon out to acos(R / (R + h)) = 10.6
deg of arc beyond the edge; the elevation of the edge follows from that
geometry.  It needs a dark sky: the sun below -12 deg (nautical twilight).

Every random draw is aee_lib_fnc_deterministicRandom on the UT block or
tick, so every machine agrees.
*/

params [];

private _data = call FUNC(getSpaceWeatherData);
private _loc = [] call EFUNC(lib,getWorldLocation);
private _lat = _loc select 0;
private _lon = _loc select 2;
// The instant as [whole days since 2000-01-01, UT hours] (float32 cannot
// hold a Julian Day).
private _ut = missionNamespace getVariable [QEGVAR(core,currentUTInstant), []];
if !((_ut isEqualType []) && {(count _ut) == 2}) then {
    _ut = [date, dayTime, _lon] call EFUNC(lib,gameClockToUT);
};
_ut params ["_dn", "_utH"];

// ─── Sunspot number at the mission date ───────────────────────────────────
date params ["_y", "_mo", "_d"];
private _series = _data get "ssnMonthly";
private _idx = ((_y - (_data get "ssnFirstYear")) * 12) + (_mo - 1);
_idx = (_idx max 0) min ((count _series) - 2);
private _frac = ((_d - 1) / 30.44) min 1;
private _ssn = ((_series select _idx) * (1 - _frac)) + ((_series select (_idx + 1)) * _frac);
private _ssnOverride = missionNamespace getVariable [QGVAR(sunspotOverride), -1];
if !(_ssnOverride isEqualType 0) then { _ssnOverride = -1; };
if (_ssnOverride >= 0) then { _ssn = _ssnOverride; };
_ssn = _ssn max 0;

// ─── Kp: 3-hour Markov chain on the GFZ transition statistics ─────────────
private _block = (_dn * 8) + floor (_utH / 3);   // 3-hour UT blocks since 2000-01-01
private _bins = _data get "kpBins";
private _bin = 0;
{ if (_ssn >= _x) then { _bin = _forEachIndex + 1; }; } forEach _bins;
private _cum = (_data get "kpCum") select _bin;
private _fnc_step = {
    params ["_level", "_seedBlock"];
    private _u = [_seedBlock, 4601] call EFUNC(lib,deterministicRandom);
    private _row = _cum select _level;
    private _next = 27;
    {
        if (_u <= _x) exitWith { _next = _forEachIndex; };
    } forEach _row;
    _next
};
private _state = missionNamespace getVariable [QGVAR(kpState), []];
private _level = 6;
private _lastBlock = _block - 48;
if ((_state isEqualType []) && {(count _state) == 2}) then {
    _state params ["_l", "_b"];
    if ((_block - _b) >= 0 && {(_block - _b) <= 8}) then { _level = _l; _lastBlock = _b; };
};
// A cold start or a long skip spins the chain up for 6 days of blocks so
// the level is a draw from the observed distribution, not the seed.
for "_k" from (_lastBlock + 1) to _block do {
    _level = [_level, _k] call _fnc_step;
};
missionNamespace setVariable [QGVAR(kpState), [_level, _block]];
private _kp = _level / 3;
private _kpOverride = missionNamespace getVariable [QGVAR(kpOverride), -1];
if !(_kpOverride isEqualType 0) then { _kpOverride = -1; };
if (_kpOverride >= 0) then { _kp = _kpOverride min 9; };

// NOAA G-scale: G1 Kp 5, G2 6, G3 7, G4 8, G5 9.
private _kpRound = round _kp;
private _geoDesc = switch (true) do {
    case (_kpRound < 4): { "Quiet" };
    case (_kpRound < 5): { "Active" };
    default { format ["Storm G%1", (_kpRound - 4) min 5] };
};

// ─── Flares: Poisson arrivals at the GOES-fitted rate ─────────────────────
private _flare = missionNamespace getVariable [QGVAR(flareState), []];
private _last = missionNamespace getVariable [QGVAR(flareLastUT), _ut];
if !((_last isEqualType []) && {(count _last) == 2}) then { _last = _ut; };
private _dtDays = ((_dn - (_last select 0)) + ((_utH - (_last select 1)) / 24)) max 0;
private _dtYears = _dtDays / 365.25;
missionNamespace setVariable [QGVAR(flareLastUT), _ut];
// Minute index within an 8192-day cycle: an exact float32 integer seed.
private _tick = ((_dn mod 8192) * 1440) + floor (_utH * 60);
private _fnc_quantile = {
    params ["_q", "_u"];
    private _pos = _u * 20;
    private _i = (floor _pos) min 19;
    private _w = _pos - _i;
    ((_q select _i) * (1 - _w)) + ((_q select (_i + 1)) * _w)
};
if (_dtYears > 0 && _dtYears < 0.01) then {
    {
        _x params ["_key", "_unit", "_salt"];
        private _p = _data get _key;
        private _rate = (_p select 0) * (_ssn ^ (_p select 1));
        private _prob = 1 - exp (-_rate * _dtYears);
        if (([_tick, _salt] call EFUNC(lib,deterministicRandom)) < _prob) then {
            private _mag = [_p select 2, [_tick, _salt + 1] call EFUNC(lib,deterministicRandom)] call _fnc_quantile;
            private _rise = ([_p select 3, [_tick, _salt + 2] call EFUNC(lib,deterministicRandom)] call _fnc_quantile) max 1;
            private _decay = ([_p select 4, [_tick, _salt + 3] call EFUNC(lib,deterministicRandom)] call _fnc_quantile) max 1;
            private _peak = _mag * _unit;
            // A stronger flare replaces a weaker one in progress.
            private _current = if (_flare isEqualTo []) then { 0 } else { _flare select 0 };
            if (_peak > _current) then {
                _flare = [_peak, _dn, _utH, _rise, _decay];
            };
        };
    } forEach [["flareM", 1e-5, 4701], ["flareX", 1e-4, 4801]];
};
private _flux = 0;
if (_flare isNotEqualTo []) then {
    _flare params ["_fPeak", "_fDn", "_fUt", "_fRise", "_fDecay"];
    private _tMin = (((_dn - _fDn) * 24) + (_utH - _fUt)) * 60;
    _flux = if (_tMin < _fRise) then {
        _fPeak * (_tMin / _fRise)
    } else {
        _fPeak * exp (-((_tMin - _fRise) * 0.693147) / _fDecay)
    };
    // The event ends when its flux falls below C1 (1e-6 W/m2).
    if (_tMin > _fRise && _flux < 1e-6) then { _flare = []; _flux = 0; };
};
missionNamespace setVariable [QGVAR(flareState), _flare];
private _flareClass = switch (true) do {
    case (_flux >= 1e-4): { format ["X%1", (round (_flux / 1e-5)) / 10] };
    case (_flux >= 1e-5): { format ["M%1", (round (_flux / 1e-6)) / 10] };
    case (_flux >= 1e-6): { format ["C%1", (round (_flux / 1e-7)) / 10] };
    default { "" };
};

// D-RAP highest affected frequency at the observer (MHz).
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), -90];
if !(_sunElev isEqualType 0) then { _sunElev = -90; };
private _haf = 0;
if (_flux > 0 && _sunElev > 0) then {
    _haf = ((10 * (log _flux)) + 65) max 0;
    _haf = _haf * ((sin _sunElev) ^ 0.75);
};

// ─── Aurora ───────────────────────────────────────────────────────────────
private _year = 2000 + ((_dn + (_utH / 24)) / 365.25);
private _mlat = 0;
if (isNil "aee_magnetism_fnc_geomagneticLatitude") then {
    _mlat = _lat;
} else {
    _mlat = ([_lat, _lon, _year] call aee_magnetism_fnc_geomagneticLatitude) select 0;
};
private _edge = 66 - 2 * _kp;                         // geomagnetic latitude
private _gap = _edge - (abs _mlat);                   // deg of arc to the oval edge
private _hKm = 110;
private _reach = acos (6371 / (6371 + _hKm));         // 10.6 deg
private _auroraElev = 90;
if (_gap > 0) then {
    _auroraElev = if (_gap < _reach) then {
        ((cos _gap) - (6371 / (6371 + _hKm))) atan2 (sin _gap)
    } else { -1 };
};
private _dark = _sunElev < -12;
private _overcast = overcast;
private _aurora = _dark && _auroraElev > 0 && _overcast < 1;
private _auroraIntensity = 0;
if (_aurora) then {
    // Render scale only (no photometric source): the oval's height in the
    // sky and the open sky fraction.
    _auroraIntensity = ((_auroraElev / 90) max 0.05) * (1 - _overcast);
};

// ─── Publish ──────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(sunspotNumber), _ssn];
missionNamespace setVariable [QGVAR(solarActivity), (_ssn / 200) min 1];
missionNamespace setVariable [QGVAR(kpIndex), _kp];
missionNamespace setVariable [QGVAR(geomagneticDescription), _geoDesc];
missionNamespace setVariable [QGVAR(xrayFlux), _flux];
missionNamespace setVariable [QGVAR(flareClass), _flareClass];
missionNamespace setVariable [QGVAR(solarFlareActive), _flux >= 1e-5];
missionNamespace setVariable [QGVAR(flareHAF), _haf];
missionNamespace setVariable [QGVAR(geomagneticLatitude), _mlat];
missionNamespace setVariable [QGVAR(auroraVisibility), _aurora];
missionNamespace setVariable [QGVAR(auroraIntensity), _auroraIntensity];
missionNamespace setVariable [QGVAR(auroraElevationDeg), _auroraElev];
_ssn
