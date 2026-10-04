#include "..\script_component.hpp"

/*
Scintillation: worsening shot noise in the dark.

A starved tube shows individual scintillation events, so dark-scene speckle
is stronger than the existing uniform grain.  This kernel returns the
FilmGrain tuple [intensity, sharpness, size].  The sharpness band 1.0-1.2
and the size band 2.25-2.70 follow the ACE3-derived ranges already in the
parent.  The 0.55, 0.25, 0.5 and 0.1 coefficients are UNSOURCED.

Arguments:
  0: Number - scene illuminance, lux
  1: Number - tube noise in [0, 1]
  2: Number - rain intensity in [0, 1]
  3: Number - strength

Returns:
  Array - [grainIntensity in [0, 1], sharpness, grainSize].
*/

params [
    ["_lux", 0.001, [0]],
    ["_noise", 0.1, [0]],
    ["_rain", 0, [0]],
    ["_strength", 1, [0]]
];

private _dark = 1 - ((_lux / 0.1) min 1);
private _raw = _strength * ((0.55 * _dark) + (0.25 * ((_noise max 0) min 1)));
private _intensity = ((_raw * (1 + ((_rain max 0) min 1) * 0.5)) max 0) min 1;
private _sharpness = 1.2 - 0.2 * ((_noise max 0) min 1);
private _size = 2.25 + 0.45 * ((_noise max 0) min 1);

[_intensity, _sharpness, _size]
