#include "..\..\script_component.hpp"

/*
Perception parameter kernel (human-vision model).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The base-grade
driver calls this; the kernel composes the tone and colour stages into the two
parameter arrays the engine effects consume.

The ColorCorrections contract is [brightness, contrast, offset, blend,
colorize, weights, radial] (BIKI Post Process Effects, capture 20240220225631).
The colorize alpha (the fourth value of slot 4) is the desaturation amount: 0
keeps the original colour, 1 is black and white times the colorize colour.  The
identity alpha is 0.  The weight array (slot 5) is the Rec.709 luma
(0.2126, 0.7152, 0.0722), its fourth value fixed 0.

Tone stage: fnc_perceptionToneResponse maps the adapted scene luminance to the
display brightness, contrast and black point.

Colour stage: when white balance is on, fnc_perceptionIlluminant normalises the
scene illuminant and fnc_perceptionChromaticAdaptation derives the blend slot.
When the mesopic photopic fraction is below 1, fnc_perceptionMesopicColor
derives the colorize slot (the Purkinje shift).  When both colour paths are off
the array is the identity.

The engine has no cone matrix and no oversaturation, so the colour stage is an
approximation: a blend toward the complementary tint, and a desaturation toward
the scotopic hue.  The FilmGrain array is the acuity candidate (sharpness 4.0,
intensity 0.006, BIKI FilmGrain defaults otherwise).

Arguments:
  0: Number - adapted scene luminance, cd/m2
  1: Number - mesopic photopic fraction, 0 scotopic to 1 photopic
  2: Array  - scene illuminant colour (engine ambient colour)
  3: Bool   - tone stage enabled
  4: Bool   - white balance enabled
  5: Number - model strength, 0 to 1
  6: Number - contrast scale
  7: Number - adaptation degree D, 0 to 1
  8: Number - maximum mesopic desaturation alpha, 0 to 0.5
  9: Number - Purkinje tint strength, 0 to 1

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
    ["_contrastScale", 1, [0]],
    ["_adaptDegree", 0.9, [0]],
    ["_desatMax", 0.3, [0]],
    ["_purkinjeStrength", 0.5, [0]]
];

private _tone = [1, 1, 0];
if (_toneEnabled) then {
    _tone = [_adaptedLum, 100, _strength, _contrastScale] call FUNC(perceptionToneResponse);
};

private _brightness = _tone select 0;
private _contrast = _tone select 1;
private _offset = _tone select 2;

// The colour stage is off when white balance is off and the scene is photopic,
// so the array stays the identity.
private _blend = [0, 0, 0, 0];
private _colorize = [1, 1, 1, 0];
if (_whiteBalance || (_mesopicW < 1)) then {
    private _meso = [_mesopicW, _desatMax, _purkinjeStrength] call FUNC(perceptionMesopicColor);
    if ((_meso select 3) > 0) then {
        _colorize = _meso;
    };
    if (_whiteBalance) then {
        private _illum = [_illuminant] call FUNC(perceptionIlluminant);
        _blend = [_illum, _adaptDegree] call FUNC(perceptionChromaticAdaptation);
    };
};

private _cc = [
    _brightness,
    _contrast,
    _offset,
    _blend,
    _colorize,
    [0.2126, 0.7152, 0.0722, 0],
    [-1, -1, 0, 0, 0, 0, 0]
];

private _grain = [0.006, 4.0, 2.01, 0.75, 1.0, 0];

[_cc, _grain]
