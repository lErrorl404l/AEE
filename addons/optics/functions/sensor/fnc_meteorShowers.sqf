#include "..\..\script_component.hpp"

/*
Meteor shower data (issue #122 dynamic night sky).

GENERATED from data/astronomy/sources/imo_cal2025.txt (IMO 2025
Meteor Shower Calendar, IMO INFO(3.1-24), Table 5 'Working List of
Visual Meteor Showers') by tools/validation/gen_meteor_showers.py.
Do not edit by hand.

Each entry is [code, name, startMonth, startDay, endMonth, endDay,
peakMonth, peakDay, lambdaDeg, raDeg, decDeg, vinfKmS, r, zhr].
Dates give the activity window and peak (2025).  lambdaDeg is the
solar longitude at maximum (equinox 2000.0).  raDeg and decDeg are
the radiant in degrees.  vinfKmS is the pre-atmospheric velocity.
r is the population index.  zhr is the Zenithal Hourly Rate.
*/
private _showers = [
    ["QUA", "Quadrantids", 12, 28, 1, 12, 1, 3, 283.15, 230, 49, 41, 2.1, 80],
    ["LYR", "April Lyrids", 4, 14, 4, 30, 4, 22, 32.32, 271, 34, 49, 2.1, 18],
    ["ETA", "eta-Aquariids", 4, 19, 5, 28, 5, 6, 45.5, 338, -1, 66, 2.4, 50],
    ["PER", "Perseids", 7, 17, 8, 24, 8, 12, 140.0, 48, 58, 59, 2.2, 100],
    ["ORI", "Orionids", 10, 2, 11, 7, 10, 21, 208, 95, 16, 66, 2.5, 20],
    ["LEO", "Leonids", 11, 6, 11, 30, 11, 17, 235.27, 152, 22, 71, 2.5, 10],
    ["GEM", "Geminids", 12, 4, 12, 20, 12, 14, 262.2, 112, 33, 35, 2.6, 150],
    ["URS", "Ursids", 12, 17, 12, 26, 12, 22, 270.7, 217, 76, 33, 2.8, 10]
];

_showers
