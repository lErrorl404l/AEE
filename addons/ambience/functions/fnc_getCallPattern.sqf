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
minute.  Below 30/7 C (about 4.3 C) the regression itself reaches zero
chirps, so that is the floor, and 30 C is the top of its valid band.  The cicada is diurnal.  The amphibian chorus is gated by
rain.  Wind and rain mask every group through the background noise they
raise (Lengagne & Slater 2002; see below).

Arguments:
   0: String - the group id (the tail names the guild)
   1: Number - the true sun elevation, degrees, negative below the horizon
   2: Number - the hour of day, 0 to 23
   3: Number - the month, 1 to 12
   4: Number - the air temperature, Celsius
   5: Number - the wind speed, m/s 0 or more
   6: Number - the rain, 0 to 1
   7: Array  - the seven temporal weights, each 0 to 1
   8: Number - the latitude, degrees (positive north)

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
    ["_pattern", [], [[]]],
    ["_latitude", 45, [0]]
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
    // Dolbear inverse, chirps per minute.  The regression reaches zero at
    // T = 30/7 C, so that is the floor; 30 C is the top of its valid band.
    private _n60 = (7 * _temperatureC) - 30;
    if ((_temperatureC < (30 / 7)) || (_temperatureC > 30)) then {
        _guildFactor = 0;
    } else {
        _guildFactor = (_n60 / 180) max 0;
    };
};
if (_isCicada) then {
    // Diurnal: no call below the horizon.
    if (_sunElevationDeg <= 0) then { _guildFactor = 0; };
};
if (_isAmphibian) then {
    // Rain gate.  Anuran chorusing rises with rainfall, not with the quiet:
    // in the Australian tropical savanna a species called on any night with
    // more than 9 mm of rain, and the explosive breeders chorused on the
    // night of the first heavy fall (Brooks and others, "Environmental
    // influences on chorusing patterns in an Australian tropical savanna frog
    // community", JCU 88395).  9 mm in a night is about 0.9 mm/h over 10 h
    // of darkness, which is the engine rain level below.
    if (_rain < (0.9 / ENGINE_RAIN_FULL_MMH)) then { _guildFactor = 0.2; };
};

// Seasonal song output, measured.  Moran, Wilson, Mennill and others 2019,
// "Diel and seasonal patterns of variation in the singing behaviour of
// Savannah Sparrows", Avian Research 10:26 (DOI 10.1186/s40657-019-0165-6),
// Fig. 2a: total song output per male per day, in 10-day bins by ordinal day
// (350 at day 120, then 243, 180, 175, 270, 288, 256, 173, 132, 106 at day
// 210), from 58,301 songs by 34 males.  Taking the month boundaries the paper
// states (May from day 121, June 152, July 182, August 213) and dividing each
// month's mean by the late-April peak of 350 gives the monthly factors below.
// The population leaves after August, so the non-breeding months carry the
// lowest measured value, the August 0.30, rather than an invented figure.
// The seasons are reversed in the southern hemisphere, so the month is shifted
// six months there; inside the tropics (|lat| < 23.44 deg, the Tropics of
// Cancer and Capricorn) there is no temperate spring and no seasonal factor.
private _seasonTable = [0.30, 0.30, 0.30, 1.00, 0.57, 0.78, 0.39, 0.30, 0.30, 0.30, 0.30, 0.30];
private _seasonFactor = 1;
private _seasonMonth = _month;
if (_latitude < 0) then { _seasonMonth = ((_month + 5) mod 12) + 1; };  // = aee_lib_fnc_seasonalMonth (kept inline: pure kernel)
if ((_isBird || _isAmphibian) && {(abs _latitude) >= 23.44}) then {
    _seasonFactor = _seasonTable select (((_seasonMonth - 1) max 0) min 11);
};

// Wind and rain suppress calling because they raise the background noise and
// mask the call.  Lengagne & Slater 2002 (Proc R Soc B 269:2121) measured
// BOTH ends of that relation on the same birds: on two dry, calm nights
// (forest background 33.4 dB) 82 % and 86 % of tawny owl pairs called, and on
// two heavy-rain nights (52.2 dB) only 14 % and 5 %.  Calling therefore falls
// from 0.84 at 33.4 dB to 0.095 at 52.2 dB, 0.0396 per dB, and the factor
// here is that rate normalised to the dry, calm value.  The background level
// is the same power sum the acoustics module publishes
// (EFUNC(weather,ambientNoiseLevel)): the measured wind-in-vegetation
// regression L = 2.78 v + 37.4 dB(A) (Komatsu and others 2000) and the rain
// level above, inlined here so the kernel stays pure.
private _levels = [33.4];
private _windMs = _wind max 0;
if (_windMs > 0.5) then { _levels pushBack (2.78 * _windMs + 37.4); };
private _rainMMh = ((_rain max 0) min 1) * ENGINE_RAIN_FULL_MMH;
if (_rainMMh > 0.1) then { _levels pushBack (52.2 + 10 * (log (_rainMMh / 7.6))); };

private _sum = 0;
{ _sum = _sum + (10 ^ (_x / 10)); } forEach _levels;
private _noiseDb = 10 * (log (_sum max 1e-9));

private _maskSupp = ((0.84 - 0.0396 * (_noiseDb - 33.4)) / 0.84) max 0 min 1;

// The measurement is on a calling bird, and so is the masking it describes.
// An anuran chorus is rain-TRIGGERED (the gate above), so the rain term of
// the background must not also silence it; the wind term still applies.
if (_isAmphibian) then {
    private _windOnly = 0;
    if (_windMs > 0.5) then { _windOnly = 2.78 * _windMs + 37.4; };
    private _s2 = (10 ^ (33.4 / 10)) + ([0, 10 ^ (_windOnly / 10)] select (_windOnly > 0));
    private _nd2 = 10 * (log _s2);
    _maskSupp = ((0.84 - 0.0396 * (_nd2 - 33.4)) / 0.84) max 0 min 1;
};

private _prob = _base * _guildFactor * _seasonFactor * _maskSupp;

((_prob max 0) min 1)
