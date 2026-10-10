#include "..\..\script_component.hpp"

/*
Ambient noise floor (issue #109).

Weather raises the local ambient noise floor and hides quiet sounds: rain,
wind, foliage rustle and nearby water each contribute a level, and the floor
is their power sum (fnc_powerSumLevels, ISO 1996-1:2016).  The floor is LOCAL
and distance-independent.  A source is audible over it when its level at the
listener exceeds the floor by a detection threshold (fnc_acousticMasking).

The four contributions are read from engine and AEE state and mapped through
tables.  The LEVELS ARE UNSOURCED modelling ranges; the issue states the
bands and this kernel reproduces their midpoints, so the register holds them.
The mapping shapes are:

  rain     engine rain 0..1 -> dB(A)   drizzle 40-45 .. heavy 55-60
  wind     m/s -> dB(A)                light breeze 25-35 .. gale 55-65
  foliage  density 0..1 -> dB(A)       quiet forest floor 20-30
  water    local fraction 0..1 -> dB(A) stream 40-50, river 50-60

No in-air published law gives a dB(A) level against the engine's rain and
wind scalars.  The nearest real literature is the wind-driven ambient-noise
spectra (Wenz 1962, JASA 34:1936) and rain-on-surface noise (ISO 140-18:2006;
Von Meier 1960, JASA, DOI 10.1121/1.1936237), both qualitative here.

The masking literature is NOT modelled as per-band here.  The engine exposes
one broadband level, so this is a broadband floor.  For the record, the
critical-band theory is: Fletcher 1940, "Auditory Patterns", Rev. Mod. Phys.
12(1):47-65, DOI 10.1103/RevModPhys.12.47 (the critical ratio is near 0 dB
across 250 Hz-4 kHz and rises ~3 dB/octave, NOT the 13-21 dB the issue
states); the auditory filter bandwidth ERB(f) = 24.7*(4.37*f/1000 + 1) Hz,
Glasberg and Moore 1990, Hearing Research 47(1-2):103-138, DOI
10.1016/0378-5955(90)90170-T; and the upward spread of masking, Egan and
Hake 1950, JASA 22(5):622-630, DOI 10.1121/1.1906661.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.

Arguments:
  0: Number - engine rain, 0 to 1
  1: Number - wind speed, m/s
  2: Number - foliage density, 0 to 1
  3: Number - local water fraction, 0 to 1

Returns:
  Number - the ambient noise level in dB(A)
*/

params [
    ["_rain", 0, [0]],
    ["_windMs", 0, [0]],
    ["_foliageDensity", 0, [0]],
    ["_waterFrac", 0, [0]]
];

// [input, dB(A)] breakpoints.  UNSOURCED: the issue's band midpoints.
private _rainTable = [[0, 0], [0.25, 43], [0.5, 48], [0.75, 53], [1.0, 58]];
private _windTable = [[0, 0], [2, 30], [5, 40], [10, 50], [15, 58], [20, 65]];
private _foliageTable = [[0, 0], [1, 25]];
private _waterTable = [[0, 0], [0.5, 45], [1, 55]];

private _terms = [
    [_rainTable, _rain],
    [_windTable, _windMs],
    [_foliageTable, _foliageDensity],
    [_waterTable, _waterFrac]
];

private _levels = [];
{
    _x params ["_table", "_value"];
    private _n = count _table;
    private _db = 0;
    if (_value <= ((_table select 0) select 0)) then {
        _db = ( _table select 0) select 1;
    } else {
        if (_value >= ((_table select (_n - 1)) select 0)) then {
            _db = (_table select (_n - 1)) select 1;
        } else {
            for "_i" from 0 to (_n - 2) do {
                private _lo = _table select _i;
                private _hi = _table select (_i + 1);
                if ((_value >= (_lo select 0)) && (_value <= (_hi select 0))) then {
                    private _span = (_hi select 0) - (_lo select 0);
                    private _frac = if (_span > 0) then {
                        (_value - (_lo select 0)) / _span
                    } else {
                        0
                    };
                    _db = (_lo select 1) + (_frac * ((_hi select 1) - (_lo select 1)));
                };
            };
        };
    };
    _levels pushBack _db;
} forEach _terms;

[_levels] call FUNC(powerSumLevels)
