#include "..\..\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.  Regenerate: python3 tools/gen_gnss.py

GPS tables:
  constellation  GPS SPS Performance Standard 5th ed. (2020), Tables 3.2-1/2/3:
                 the 30 locations of the fully expanded 24-slot constellation,
                 [RAAN deg, argument of latitude deg] at the epoch
                 2016-12-31 23:59:43 UTC (day 6209, 23.9953 h),
                 GHA 100.765 deg, a 26559.8 km,
                 i 55 deg, nodal regression -0.0402 deg/day.
  uereBands      single-frequency user range error, 1 sigma (m), against
                 geomagnetic latitude (deg): FAA SPS PAN #125 (Q1 2024)
                 95 % horizontal errors over 2 x this constellation's HDOP,
                 at the quarter's smoothed sunspot number 136.5.
Return: HASHMAP
Public: No
*/
createHashMapFromArray [
    ["epochDay", 6209],
    ["epochHours", 23.9953],
    ["gha0", 100.765],
    ["aKm", 26559.8],
    ["incDeg", 55],
    ["nodeRate", -0.0402],
    ["maskDeg", 5],
    ["slots", [
    [288.85, 239.54],
    [288.85, 343.09],
    [288.85, 13.22],
    [348.85, 144.75],
    [348.85, 281.39],
    [348.85, 175.79],
    [48.85, 83.29],
    [48.85, 343.21],
    [48.85, 311.08],
    [108.85, 106.64],
    [108.85, 6.57],
    [108.85, 138.77],
    [168.85, 168.46],
    [168.85, 274.01],
    [168.85, 305.1],
    [228.85, 210.3],
    [228.85, 76.62],
    [228.85, 106.76],
    [348.85, 66.33],
    [348.85, 37.77],
    [108.85, 254.09],
    [108.85, 229.39],
    [228.85, 331.87],
    [228.85, 305.43],
    [288.85, 144.4],
    [288.85, 117.96],
    [48.85, 220.43],
    [48.85, 195.73],
    [168.85, 52.08],
    [168.85, 23.52]
    ]],
    ["uereBands", [[5, 3.888], [25, 4.699], [35, 1.591], [45, 1.271], [55, 1.237], [65, 1.66], [75, 1.824]]],
    ["ssnRef", 136.5]
]
