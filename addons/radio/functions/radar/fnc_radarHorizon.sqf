#include "..\..\script_component.hpp"
/*
Radar horizon - line-of-sight distance to a target.

  D_max = 4.12 ( sqrt(H_a) + sqrt(H_t) )   [km]

  H_a  antenna height, m
  H_t  target height, m

The 4.12 km factor is sqrt(2 k R_e) with the 4/3 effective earth radius
(k = 4/3, R_e = 6371 km): sqrt(2 * 4/3 * 6371) = 4.12 km.

Source: the 4/3 earth radius is from ITU-R P.834 ("Effects of
tropospheric refraction on radiowave propagation"); the horizon FORMULA
D = sqrt(2 k R_e H) is the standard geometric line of sight, derived
here from that k, not quoted from P.834.  Verified vector:
H_a = 30, H_t = 10 -> 35.6 km.

Pure: reads no engine state, writes none.

Arguments:
  0: Number - antenna height H_a, m
  1: Number - target height H_t, m

Returns:
  Number - horizon distance D_max, km
*/
params [
    ["_ha", 0, [0]],
    ["_ht", 0, [0]]
];

// R_e in metres, so sqrt(2 k R_e) is in metres; divide by 1000 for km.
private _k_earth = 4 / 3;
private _radius_m = 6371000;
private _factor = (sqrt (2 * _k_earth * _radius_m)) / 1000;

_factor * ((sqrt (_ha max 0)) + (sqrt (_ht max 0)))
