#include "..\..\script_component.hpp"

/*
Perception parameter kernel (human-vision model, light slice).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The base-grade
driver calls this; the kernel composes the tone stage into the two parameter
arrays the engine effects consume.

The ColorCorrections contract is [brightness, contrast, offset, blend,
colorize, weights, radial] (BIKI Post Process Effects, capture 20240220225631).
The colorize alpha (the fourth value of slot 4) is the desaturation amount: 0
keeps the original colour, 1 is black and white times the colorize colour.  The
identity alpha is 0.  The weight array (slot 5) is the Rec.709 luma
(0.2126, 0.7152, 0.0722), its fourth value fixed 0.

Slice 1 composes the light and tone stage only.  The colour inputs default to
identity, so the blend slot stays [0,0,0,0] and the colorize slot stays
[1,1,1,0].  The colour stage, driven by _whiteBalance, _illuminant and
_mesopicW, arrives in a later slice.  The FilmGrain array is the acuity
candidate (sharpness 4.0, intensity 0.006, BIKI FilmGrain defaults otherwise).

Arguments:
  0: Number - adapted scene luminance, cd/m2
  1: Number - mesopic photopic fraction, 0 scotopic to 1 photopic
  2: Array  - scene illuminant colour (reserved for the colour slice)
  3: Bool   - tone stage enabled
  4: Bool   - white balance enabled (reserved for the colour slice)
  5: Number - model strength, 0 to 1
  6: Number - contrast scale

Returns:
  Array - [ColorCorrections array, FilmGrain array]
*/

params [
    ["_adaptedLum", 1, [0]],
    ["_mesopicW", 1, [0]],
    ["_illuminant", [1, 1, 1], [[]]],
    ["_toneEnabled", true, [true]],
    ["_whiteBalance", false, [false]],
    ["_strength", 1, [0]],
    ["_contrastScale", 1, [0]]
];

private _tone = [1, 1, 0];
if (_toneEnabled) then {
    _tone = [_adaptedLum, 100, _strength, _contrastScale] call FUNC(perceptionToneResponse);
};

private _brightness = _tone select 0;
private _contrast = _tone select 1;
private _offset = _tone select 2;

// The colour stage is identity in the light slice.  The reserved inputs are
// named here so the composition contract is stable across the slices.
private _cc = [
    _brightness,
    _contrast,
    _offset,
    [0, 0, 0, 0],
    [1, 1, 1, 0],
    [0.2126, 0.7152, 0.0722, 0],
    [-1, -1, 0, 0, 0, 0, 0]
];

private _grain = [0.006, 4.0, 2.01, 0.75, 1.0, 0];

[_cc, _grain]
