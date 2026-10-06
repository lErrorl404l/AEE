#include "..\script_component.hpp"

/*
Species match kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It is an ordered ladder, the same shape as fnc_worldLightingClass: match the
Koppen family, add the water and settlement overlays, apply the season rule,
then the temperature band, then the temporal weight, then a seeded jitter.
Activity comes from the true sun elevation against the corpus activity class,
never a night boolean, so dawn and dusk resolve from the elevation alone.
The same inputs on any machine return the same rows.

Arguments:
   0: String - the Koppen biome code
   1: Number - the true sun elevation, degrees, negative below the horizon
   2: Number - the air temperature, Celsius
   3: Number - the month, 1 to 12
   4: Number - the water fraction, 0 to 1
   5: Number - the vegetation score, 0 to 1
   6: String - the surface material class ("ground", "concrete", ...)
   7: Number - the structure fraction, 0 to 1
   8: Array  - the weather [wind, rain 0 to 1, ...]
   9: Number - the mission seed
  10: Array  - the ecology corpus rows (14 columns, see ecology_corpus.sqf)

Returns:
  Array - weighted [groupId, weight] rows, weight above 0 and up to 1.
*/

params [
    ["_biome", "", [""]],
    ["_sunElevationDeg", 45, [0]],
    ["_temperatureC", 15, [0]],
    ["_month", 6, [0]],
    ["_waterFrac", 0, [0]],
    ["_vegScore", 0, [0]],
    ["_surfaceMaterial", "ground", [""]],
    ["_structureFrac", 0, [0]],
    ["_weather", [], [[]]],
    ["_seed", 0, [0]],
    ["_corpus", [], [[]]]
];

if (_corpus isEqualTo []) exitWith { [] };

private _wind = 0;
private _rain = 0;
if ((count _weather) >= 1) then { _wind = _weather select 0; };
if ((count _weather) >= 2) then { _rain = _weather select 1; };
if !(_wind isEqualType 0) then { _wind = 0; };
if !(_rain isEqualType 0) then { _rain = 0; };

// The family from the Koppen first letter.  A tropical, B arid, C temperate,
// D and E cold.  This is the mapping the retired fnc_speciesForBiome used.
private _family = "temperate";
private _first = toLower (_biome select [0, 1]);
if (_first == "a") then { _family = "tropical"; };
if (_first == "b") then { _family = "arid"; };
if ((_first == "d") || (_first == "e")) then { _family = "cold"; };

private _water = ((_waterFrac max 0) min 1);
private _struct = ((_structureFrac max 0) min 1);
private _base = ((_vegScore max 0) min 1);

// A built-up or hard-surfaced cell is the settlement overlay cue.
private _settled = (_struct > 0.35) || (_surfaceMaterial == "concrete");

private _out = [];
for "_i" from 0 to ((count _corpus) - 1) do {
    private _row = _corpus select _i;
    if ((count _row) >= 14) then {
        // 1. Family, then the water and settlement overlays.
        private _rowFamily = _row select 0;
        private _familyOk = false;
        if (_rowFamily == _family) then { _familyOk = true; };
        if ((_rowFamily == "water") && (_water > 0.5)) then { _familyOk = true; };
        if ((_rowFamily == "settlement") && _settled) then { _familyOk = true; };

        if (_familyOk) then {
            // 2. Season rule: the month must be in the group season list.
            private _months = _row select 4;
            private _inSeason = false;
            for "_m" from 0 to ((count _months) - 1) do {
                if ((_months select _m) == _month) then { _inSeason = true; };
            };

            // 3. Temperature band.
            private _band = _row select 5;
            private _tempOk = (_temperatureC >= (_band select 0)) && (_temperatureC <= (_band select 1));

            if (_inSeason && _tempOk) then {
                // 4. Temporal weight from the true sun elevation.
                private _activity = _row select 3;
                private _active = 0;
                if (_activity == "diurnal") then {
                    if (_sunElevationDeg > -6) then { _active = 1; };
                };
                if (_activity == "nocturnal") then {
                    if (_sunElevationDeg < 6) then { _active = 1; };
                };
                if (_activity == "crepuscular") then {
                    if ((abs _sunElevationDeg) <= 15) then { _active = 1; } else { _active = 0.3; };
                };

                if (_active > 0) then {
                    private _bin = 3;
                    if (_sunElevationDeg < -6) then { _bin = 6; } else {
                        if (_sunElevationDeg < 0) then { _bin = 0; } else {
                            if (_sunElevationDeg < 15) then { _bin = 1; } else {
                                if (_sunElevationDeg < 40) then { _bin = 4; } else { _bin = 3; };
                            };
                        };
                    };
                    private _bins = _row select 10;
                    private _temporal = _active * (_bins select _bin);

                    // 5. Habitat pull from the group weights and the sample.
                    private _hab = _row select 9;
                    private _pull = (_hab select 0) * _base;
                    private _pullWater = (_hab select 2) * _water;
                    if (_pullWater > _pull) then { _pull = _pullWater; };
                    private _pullStruct = (_hab select 3) * _struct;
                    if (_pullStruct > _pull) then { _pull = _pullStruct; };
                    private _habFactor = 0.5 + (0.5 * _pull);

                    // Wind and rain suppress the call, per the group rule.
                    private _windRule = _row select 6;
                    if (_wind > (_windRule select 0)) then {
                        _habFactor = _habFactor * (1 - (_windRule select 1));
                    };
                    private _rainRule = _row select 7;
                    if (_rain > (_rainRule select 0)) then {
                        _habFactor = _habFactor * (1 - (_rainRule select 1));
                    };

                    // 6. Seeded jitter, so a one-step seed change moves the mix.
                    private _hash = ((_seed * 101) + ((_i + 1) * 37)) mod 997;
                    if (_hash < 0) then { _hash = -_hash; };
                    private _jitter = 0.25 + (((_hash mod 100) / 100) * 0.75);

                    private _weight = ((_temporal * _habFactor * _jitter) max 0) min 1;
                    if (_weight > 0) then {
                        _out pushBack [_row select 1, _weight];
                    };
                };
            };
        };
    };
};

_out
