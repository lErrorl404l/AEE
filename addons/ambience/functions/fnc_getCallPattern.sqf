#include "..\script_component.hpp"

/*
Temporal call-pattern kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It turns the hour, the true sun elevation, the month, the air temperature and
the wind and rain into the probability that one species group calls in this
time bin.  The caller passes the group's own temporal pattern, the seven
weights from the corpus (pre_dawn, dawn, morning, midday, afternoon, dusk,
night), so the shape lives in the data and not here.

The cricket rate uses the Dolbear inverse N60 ~= 7 * T_C - 30, chirps per
minute, in its valid band 5 to 30 C.  Below 5 C the kernel returns zero, the
UNSOURCED floor.  The cicada is diurnal.  The amphibian chorus is gated by
rain.  Wind and rain mask every group.  The wind and rain shapes are
modelling choices, UNSOURCED.

Arguments:
   0: String - the group id (the tail names the guild)
   1: Number - the true sun elevation, degrees, negative below the horizon
   2: Number - the hour of day, 0 to 23
   3: Number - the month, 1 to 12
   4: Number - the air temperature, Celsius
   5: Number - the wind speed, m/s 0 or more
   6: Number - the rain, 0 to 1
   7: Array  - the seven temporal weights, each 0 to 1

Returns:
  Number - the calling probability, 0 to 1
*/

params [
    ["_groupId", "", [""]],
    ["_sunElevationDeg", 45, [0]],
    ["_hour", 12, [0]],
    ["_month", 6, [0]],
    ["_temperatureC", 15, [0]],
    ["_wind", 0, [0]],
    ["_rain", 0, [0]],
    ["_pattern", [], [[]]]
];

private _weights = _pattern;
if ((count _weights) < 7) then {
    _weights = [1, 1, 1, 1, 1, 1, 1];
};

// Map the hour to the corpus time bin.  The sun elevation splits the pre-dawn
// from the night at the start and the end of the day.
private _bin = 6;
if ((_hour < 4) || (_hour >= 21)) then { _bin = 6; }
else {
    if (_hour < 6) then { _bin = 0; }
    else {
        if (_hour < 9) then { _bin = 1; }
        else {
            if (_hour < 12) then { _bin = 2; }
            else {
                if (_hour < 15) then { _bin = 3; }
                else {
                    if (_hour < 18) then { _bin = 4; } else { _bin = 5; };
                };
            };
        };
    };
};
if (_sunElevationDeg < -6) then { _bin = 6; };

private _base = ((_weights select _bin) max 0) min 1;

// The guild from the group id.  A group names one guild.  The harness has no
// `in` operator, so a small pure helper scans the id for the guild token.
private _contains = {
    params ["_haystack", "_needle"];
    private _h = toLower _haystack;
    private _n = toLower _needle;
    private _hl = count _h;
    private _nl = count _n;
    if (_nl > _hl) exitWith { false };
    private _found = false;
    for "_i" from 0 to (_hl - _nl) do {
        if ((_h select [_i, _nl]) == _n) then { _found = true; };
    };
    _found
};

private _isCricket = [_groupId, "cricket"] call _contains;
private _isCicada = [_groupId, "cicada"] call _contains;
private _isAmphibian = [_groupId, "amphibian"] call _contains;
private _isBird = [_groupId, "bird"] call _contains;

// Guild modifiers.
private _guildFactor = 1;
if (_isCricket) then {
    // Dolbear inverse, chirps per minute, valid 5 to 30 C, zero below.
    private _n60 = (7 * _temperatureC) - 30;
    if ((_temperatureC < 5) || (_temperatureC > 30)) then {
        _guildFactor = 0;
    } else {
        _guildFactor = ((_n60 - 5) / 175) max 0;
    };
};
if (_isCicada) then {
    // Diurnal: no call below the horizon.
    if (_sunElevationDeg <= 0) then { _guildFactor = 0; };
};
if (_isAmphibian) then {
    // Rain gate: a dry hour damps the chorus.
    if (_rain < 0.2) then { _guildFactor = 0.2; };
};

// The breeding season lifts the bird and amphibian chorus.  AEE publishes no
// season scalar; the month is the source.  The shape is UNSOURCED.
private _seasonFactor = 1;
if (_isBird || _isAmphibian) then {
    if ((_month >= 3) && (_month <= 5)) then { _seasonFactor = 1.0; }
    else { if ((_month >= 6) && (_month <= 8)) then { _seasonFactor = 0.9; }
    else { if ((_month >= 9) && (_month <= 11)) then { _seasonFactor = 0.7; }
    else { _seasonFactor = 0.5; }; }; };
};

// Wind and rain mask every group.  Both shapes are UNSOURCED.
private _windSupp = 1 - (((_wind max 0) / 12) min 1);
private _rainSupp = 1 - (0.4 * ((_rain max 0) min 1));

private _prob = _base * _guildFactor * _seasonFactor * _windSupp * _rainSupp;

((_prob max 0) min 1)
