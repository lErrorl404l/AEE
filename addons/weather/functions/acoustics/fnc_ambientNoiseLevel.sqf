#include "..\..\script_component.hpp"

/*
Ambient noise floor (issue #109).

Weather raises the local ambient noise floor and hides quiet sounds: rain,
wind, foliage rustle and nearby water each contribute a level, and the floor
is their power sum (fnc_powerSumLevels, ISO 1996-1:2016).  The floor is LOCAL
and distance-independent.  A source is audible over it when its level at the
listener exceeds the floor by a detection threshold (fnc_acousticMasking).

The four contributions are read from engine and AEE state and mapped through
tables, each from a field measurement (PROVENANCE below):

  rain     rate mm/h -> dB(A)          52.2 at 7.6 mm/h, +10 log10(R/7.6)
  wind     m/s -> dB(A)                measured wind-in-vegetation law below
  foliage  density 0..1 -> dB(A)       dry calm forest 33.4
  water    local fraction 0..1 -> dB(A) 55 at a riffle stream's edge

PROVENANCE.

  wind SOURCED.  Wind-induced vegetation noise.  The measured regression is
    L_A = 2.78 * v + 37.4 dB(A), with v the wind speed in m/s (Sneddon and
    others, reported in Komatsu, Kato, Kuwano, Namba, Kondo, Inoue and
    Yamaguchi 2000, "Physical Characteristics of Wind-induced Foliage
    Sounds of Planting Trees", Journal of the INCE of Japan 24(4):268-276,
    DOI 10.11372/souonseigyo1977.24.268, section 2, page 269: "L = 2.78 y +
    37.4 ... y = 5 m/s ... L = 51.3 dBA").  The table holds that regression
    at 2, 5, 10, 15 and 20 m/s.  Its 0 m/s row is a deliberate zero, not the
    regression's 37.4 dB intercept: the row is the wind contribution, and the
    source measured from 5 m/s up, so a dead calm adds no wind-induced
    foliage noise.  The receiver sat 5 m from the trunk of a
    planted tree, so the value is the floor a listener under vegetation
    hears, not a bare-ground value.  Komatsu section 4.2, page 271, records
    the same order for its own six-tree set.

  water DERIVED.  A riffle stream measured in the field (the Bravona,
    Corsica; JASA 159(5):3999, 2026) never fell below 40 dB(A) at 200 m and
    lost 10-20 dB(A) over that distance, so 50-60 dB(A) at the water: the
    row reaches 55 dB(A) with the listener at the water's edge.
  rain SOURCED.  Heavy rain raised the forest background to 52.2 dB against
    33.4 dB dry (Lengagne & Slater 2002, Proc R Soc B 269:2121).  Heavy rain
    starts at 7.6 mm/h (AMS Glossary of Meteorology), and the impact power of
    rain grows with the rate, so L = 52.2 + 10 log10(R / 7.6), R in mm/h
    (the engine level times ENGINE_RAIN_FULL_MMH).
  foliage SOURCED.  The dry, calm forest background was 33.4 dB
    (Lengagne & Slater 2002, the same measurement): full foliage density
    carries it, and a sparser cover has proportionally fewer leaves, so
    10 log10(density) less.  The water row scales the same way with the
    fraction of water in earshot.

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

// [input, dB(A)] breakpoints.  The wind row is the measured regression
// L_A = 2.78 * v + 37.4 dB(A), Komatsu and others 2000, section 2, page 269
// (see the header).  Its 0 m/s entry is a deliberate zero: the row is the
// wind contribution, so a dead calm adds no wind-induced foliage noise.
// Rain, foliage and water are set after the table pass (below).
private _windTable = [[0, 0], [2, 42.96], [5, 51.3], [10, 65.2], [15, 79.1], [20, 93]];

private _terms = [
    [_windTable, _windMs]
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

// Each term below is a sum of incoherent sources, so its level grows as
// 10 log10 of the source count: the rain rate, the leaf cover and the water
// surface in earshot.
// Rain: Lengagne & Slater 2002, 52.2 dB(A) at 7.6 mm/h.
private _rMMh = (_rain max 0) * ENGINE_RAIN_FULL_MMH;
_levels pushBack ([0, 52.2 + 10 * (log ((_rMMh max 0.01) / 7.6))] select (_rMMh > 0.1));
// Foliage: Lengagne & Slater 2002, 33.4 dB(A) in a full, dry, calm forest.
_levels pushBack ([0, 33.4 + 10 * (log (_foliageDensity max 0.001))] select (_foliageDensity > 0.001));
// Water: the Bravona riffle, 55 dB(A) at the water's edge.
_levels pushBack ([0, 55 + 10 * (log (_waterFrac max 0.001))] select (_waterFrac > 0.001));
[_levels] call FUNC(powerSumLevels)
