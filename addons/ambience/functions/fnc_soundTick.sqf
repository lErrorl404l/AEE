#include "..\script_component.hpp"

/*
Behaviour-gated species emission scheduler (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
For one time bin it decides which species groups call and how often, and
returns the positional one-shots to play.  The pattern kernel fnc_getCallPattern
gives the probability that a group calls in the bin; the guild sets the call
rate, and the cricket rate is the Dolbear inverse, chirps per minute; the
species-to-sound map fnc_speciesSound supplies the media.

The shape lives in the data.  A diurnal bird group peaks at its dawn bin and
falls to near silence at its midday bin, so birds are not constant.  A cricket
follows its temperature-derived rate.  The amphibian chorus is rain-gated by
the pattern kernel.  A group with a speech-like event is only in the mix when
its call fired, so it emits nothing otherwise.

The per-emission volume carries the silence model, so the disturbance, wind
and rain attenuation the CfgSFX bed discarded now apply.  Every emission uses
the same seed, so two clients agree on the schedule.

Each guild call rate is a measured figure (see the rate block below); the
cricket rate is the Dolbear relation.  The bin is one hour.

Arguments:
  0: Number - the hour of day, 0 to 23
  1: Number - the true sun elevation, degrees, negative below the horizon
  2: Number - the month, 1 to 12
  3: Number - the air temperature, Celsius
  4: Number - the wind, metres per second
  5: Number - the rain, 0 to 1
  6: Number - the silence gain, 0 to 1
  7: Array  - the local mix, one [groupId, soundGroup, weight 0 to 1, bins]
              where the groupId carries the guild token for the pattern and
              the soundGroup is an asset-map key for the media
  8: Array  - the asset-map rows (see asset_map.sqf)
  9: Array  - the loaded platform tokens, for example ["enoch"]
  10: Number - the seed
  11: Number - the latitude, degrees (positive north)

Returns:
  Array - emission rows [groupId, media path, volume], one per call
*/

params [
    ["_hour", 12, [0]],
    ["_sunElevationDeg", 45, [0]],
    ["_month", 6, [0]],
    ["_temperatureC", 15, [0]],
    ["_wind", 0, [0]],
    ["_rain", 0, [0]],
    ["_gain", 1, [0]],
    ["_mix", [], [[]]],
    ["_assetMap", [], [[]]],
    ["_platforms", [], [[]]],
    ["_seed", 0, [0]],
    ["_latitude", 45, [0]]
];

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

private _volume = ((_gain max 0) min 1);
private _out = [];

for "_g" from 0 to ((count _mix) - 1) do {
    private _entry = _mix select _g;
    if ((count _entry) >= 4) then {
        private _group = _entry select 0;
        private _soundGroup = _entry select 1;
        private _weight = ((_entry select 2) max 0) min 1;
        private _bins = _entry select 3;

        // A silent listener, or a group that is not in the mix, emits nothing.
        if ((_weight > 0) && (_volume > 0.01) && (_group isEqualType "") && (_soundGroup isEqualType "")) then {
            private _probability = [
                _group, _sunElevationDeg, _hour, _month, _temperatureC,
                _wind, _rain, _bins, _latitude
            ] call FUNC(getCallPattern);

            if (_probability > 0) then {
                // The guild call rate per minute, each a measured figure:
                //   cricket  the Dolbear inverse, chirps per minute, zero at
                //            the regression's own zero (T = 30/7 C).
                //   cicada   Tibicina josei phrase rate, 3.3 to 8.7 phrases
                //            per minute over its temperature range (Sueur and
                //            Aubin, Tibicina calling songs); the mid, 6.
                //   frog     Rana pipiens, 13.2 notes per minute (Advertisement
                //            Call Complexity in Northern Leopard Frogs).
                //   songbird Savannah Sparrow dawn-chorus peak, 89 songs per
                //            hour (Moran and others 2019, Avian Research 10:26,
                //            Fig. 3) = 1.48 per minute.
                //   owl      tawny owl two-call repetition every 18 to 26 s
                //            (Daily and seasonal fluctuation in Tawny Owl
                //            vocalization timing, PMC7159226); the 22 s mid is
                //            2.7 events per minute.
                // A guild with no measured rate falls back to the songbird one.
                private _rate = 89 / 60;
                if ([_soundGroup, "cricket"] call _contains) then {
                    _rate = ((7 * _temperatureC) - 30) max 0;
                };
                if ([_soundGroup, "cicada"] call _contains) then { _rate = 6; };
                if ([_soundGroup, "frog"] call _contains) then { _rate = 13.2; };
                if ([_soundGroup, "songbird"] call _contains) then { _rate = 89 / 60; };
                if ([_soundGroup, "owl"] call _contains) then { _rate = 60 / 22; };

                // The seeded phase turns the fractional expected count into a
                // stable integer, so two clients with the same seed agree.
                private _phase = ((((_seed * 31) + (_g * 17)) mod 1000) / 1000);
                private _count = floor ((_rate * 60 * _probability * _weight) + _phase);

                if (_count > 0) then {
                    private _resolved = [_soundGroup, _platforms, _assetMap] call FUNC(speciesSound);
                    private _media = _resolved select 0;
                    if ((_media isEqualType []) && ((count _media) > 0)) then {
                        private _n = count _media;
                        for "_c" from 0 to (_count - 1) do {
                            private _index = ((_seed + _g + _c) mod _n);
                            _out pushBack [_group, _media select _index, _volume];
                        };
                    };
                };
            };
        };
    };
};

_out
