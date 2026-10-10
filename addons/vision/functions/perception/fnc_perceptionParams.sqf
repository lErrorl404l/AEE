#include "..\..\script_component.hpp"

/*
Perception parameter kernel (human-vision model).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The base-grade
driver calls this; the kernel composes the tone and colour stages into the two
parameter arrays the engine effects consume.

The ColorCorrections contract is [brightness, contrast, offset, blend,
colorize, weights, radial] (BIKI Post Process Effects, capture 20240220225631).
The identity is the engine's OWN neutral, not a BIKI-table guess: the base
game's CfgPostProcessTemplates >> Default >> colorCorrections =
{1,1,0,{0,0,0,0},{1,1,1,1},{0,0,0,0}} (functions_f.pbo, applied verbatim by
fn_setppeffecttemplate) renders colour with colorize alpha 1 and all-zero
weights.  The colour stage overrides the identity with the Rec.709 luma weights
(REC709_LUMA_R, REC709_LUMA_G, REC709_LUMA_B), fourth value fixed 0, only when it is active.

Tone stage: fnc_perceptionToneResponse maps the adapted scene luminance to the
display brightness, contrast and black point.  fnc_perceptionBaseGrade then
clamps that triple to the vanilla base-grade anchor plus a small bounded
deviation, so the default image never pushes an extreme look.

Colour stage: when white balance is on, fnc_perceptionIlluminant normalises the
scene illuminant and fnc_perceptionChromaticAdaptation derives the blend slot.
When the mesopic photopic fraction is below 1, fnc_perceptionMesopicColor
derives the colorize slot (the Purkinje shift).  When both colour paths are off
the array is the identity.

The engine has no cone matrix and no oversaturation, so the colour stage is an
approximation: a blend toward the complementary tint, and a desaturation toward
the scotopic hue.  The FilmGrain array is the acuity candidate (sharpness 4.0,
intensity 0.006, monochromatic 1 colour; BIKI FilmGrain defaults otherwise).
The monochromatic element must stay non-zero: the Arma 3 value 0 is monochrome
and drains normal vision to grey.

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
  10: Array - vanilla base-grade anchor [brightness, contrast, offset]
  11: Number - bounded desaturation alpha, 0 to 0.10
  12: Number - atmospheric desaturation alpha, 0 to 0.5
               (fnc_perceptionAtmosphericColor)
  13: Number - acuity grain light-level scale, 0 and up (1 is the base)

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
    ["_desatMax", 0, [0]],
    ["_purkinjeStrength", 0, [0]],
    ["_anchor", [1, 1, 0], [[]]],
    ["_desatAlpha", 0, [0]],
    ["_atmosAlpha", 0, [0]],
    ["_grainScale", 1, [0]]
];

if !(_atmosAlpha isEqualType 0) then { _atmosAlpha = 0; };
if !(_grainScale isEqualType 0) then { _grainScale = 1; };

private _tone = [1, 1, 0];
if (_toneEnabled) then {
    _tone = [_adaptedLum, 100, _strength, _contrastScale] call FUNC(perceptionToneResponse);
};

// Clamp the tone triple to the vanilla anchor plus a small bounded deviation.
private _grade = [_tone, _anchor, _strength, _desatAlpha] call FUNC(perceptionBaseGrade);
private _brightness = _grade select 0;
private _contrast = _grade select 1;
private _offset = _grade select 2;
private _alpha = _grade select 3;

// The colour stage is off when white balance is off and the scene is photopic,
// so the array stays the identity.
private _blend = [0, 0, 0, 0];
// The identity MUST be the engine's own neutral post-process:
// CfgPostProcessTemplates >> Default >> colorCorrections =
// {1,1,0,{0,0,0,0},{1,1,1,1},{0,0,0,0}} (functions_f.pbo; fn_setppeffecttemplate
// feeds that array straight to ppEffectAdjust).  The base game renders colour
// with it: colorize alpha 1 and all-zero desaturation weights.  The colour
// stage only overrides it when active, so the default photopic image keeps the
// original colour.
private _colorize = [1, 1, 1, 1];
private _weights = [0, 0, 0, 0];
// The total desaturation is the larger of the bounded mesopic alpha and the
// atmospheric alpha.  The atmospheric term is a separate physical cause (Mie
// and aerial scattering under cloud, rain and haze) feeding the SAME colorize
// and weights mechanism, not a second colour stage.
private _desat = _alpha max _atmosAlpha;
if (_whiteBalance || (_mesopicW < 1) || (_atmosAlpha > 0)) then {
    private _meso = [_mesopicW, _desatMax, _purkinjeStrength] call FUNC(perceptionMesopicColor);
    // A zero mesopic alpha is the identity: keep the neutral colour and the
    // bounded desaturation alpha, so the default settings never tint.
    if ((_meso select 3) > 0) then {
        // The mesopic path tints toward the scotopic hue.
        _colorize = [_meso select 0, _meso select 1, _meso select 2, 1 - _desat];
        _weights = [REC709_LUMA_R, REC709_LUMA_G, REC709_LUMA_B, 0];
    };
    // The atmospheric path is a pure desaturation toward the Rec.709 luma, so
    // its colorize colour stays white.  It supersedes the mesopic tint when
    // both apply: the larger cause sets the visible grade.
    if (_atmosAlpha > 0) then {
        _colorize = [1, 1, 1, 1 - _desat];
        _weights = [REC709_LUMA_R, REC709_LUMA_G, REC709_LUMA_B, 0];
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
    _weights,
    [-1, -1, 0, 0, 0, 0, 0]
];

// The light-level scale multiplies the acuity grain intensity: a dark scene
// raises it.  The intensity is bounded to the engine FilmGrain range 0 to
// 0.05 (BIKI FilmGrain, default 0.005).  The scale itself is UNSOURCED: the
// issue's 2.25 to 2.7 values are a mod-derived scale, not an intensity.
// The last FilmGrain element is the monochromatic flag.  BIKI Arma 3: 0 is
// monochrome, any other value is colour.  0 desaturates normal vision, so the
// acuity grain ships colour.
private _grainIntensity = ((0.006 * (_grainScale max 0)) max 0) min 0.05;
private _grain = [_grainIntensity, 4.0, 2.01, 0.75, 1.0, 1];

[_cc, _grain]
