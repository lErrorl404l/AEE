#include "..\..\script_component.hpp"

/*
Base-grade and acuity parameter kernel (image realism).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The grade
driver reads the settings and calls this; the kernel builds the two parameter
arrays the engine effects consume.

The engine has no scriptable sharpening.  The creatable post-process set is
RadialBlur, ChromAberration, WetDistortion, ColorCorrections, DynamicBlur,
FilmGrain, ColorInversion, SSAO and Resolution.  There is no "Sharpen" effect,
so the acuity candidate is FilmGrain at high sharpness and low intensity.  It
is a display-aesthetic compromise, not added human acuity: contrast
sensitivity is a band-pass function (Campbell and Robson 1968, J Physiol, DOI
10.1113/jphysiol.1968.sp008574).

ColorCorrections slot order (BIKI Post Process Effects, capture 20240220225631):
  [brightness, contrast, offset, blend, colorize, weights, radial].  The
  colorize alpha (slot 4) is the saturation: 0 is the identity, 1 is black and
  white times the colorize colour.  Slot 5 holds the luma weights for the
  desaturation, its fourth value fixed 0.  Slot 6 is the optional Arma 3
  radial, default [-1,-1,0,0,0,0,0].  A wrong length or a colorize alpha of 1
  is the black-and-white class that drained normal vision to grey.

Per-constant source register (UNSOURCED values are marked beside the clamp):
  contrast    1.15, range 0.8 to 1.6.  ACES tone scale is an S-shaped curve
              with a mid-grey log-log gamma below 1.55 (docs.acescentral.com,
              tone-mapping).  The engine contrast is linear, so this is a
              stand-in.  Exact default UNSOURCED.
  brightness  1.0, range 0.7 to 1.3.  BIKI Post Process Effects:
              ColorCorrections brightness, 0 black, 1 unchanged, 2 white.
  offset      -0.02, range -0.1 to 0.1.  Negative offset is proven in
              community code (AsYetUntitled/Framework fn_flashbang.sqf -0.01;
              Liberation-RX -0.35).  The BIKI range line says 0 and up.
              Exact default UNSOURCED.
  weights     [0.2126, 0.7152, 0.0722, 0], fixed.  The Rec.709 luma and the ASC
              CDL luma, used as the engine "rgb weights for desaturation"
              (slot 5).  Nonzero, so the engine desaturation is valid.  The
              repo treats [0,0,0,0] as a broken effect; the wiki has no such
              warning, so the repo rule is the authority and the wiki basis is
              UNSOURCED.
  saturation  0.0, range 0 to 0.5.  The colorize alpha (slot 4): BIKI gives 0
              as the original colour and 1 as black and white.  So 0 is the
              identity.  The engine desaturates only.
  blend       [0,0,0,0], fixed.  BIKI ColorCorrections blend, alpha 0 keeps
              the original colour.
  sharpness   4.0, range 1 to 20.  BIKI FilmGrain parameter named sharpness,
              default 1.25.  The wiki does not state what it sharpens.
              UNSOURCED that it sharpens the scene.
  grain       0.006, range 0 to 0.05.  BIKI FilmGrain intensity, default 0.005.
  grain size  2.01, range 1 to 8.  BIKI FilmGrain, default 2.01.
  intensityX  0.75, 1.0, BIKI FilmGrain defaults.
  monochrome  0, BIKI FilmGrain Arma 3, 0 colour, 1 monochrome.

Arguments:
  0: Number - display contrast (0.8 to 1.6)
  1: Number - display brightness (0.7 to 1.3)
  2: Number - black-point offset (-0.1 to 0.1)
  3: Number - desaturation weight (0 to 0.5)
  4: Number - FilmGrain sharpness (1 to 20)
  5: Number - FilmGrain intensity (0 to 0.05)

Returns:
  Array - [ColorCorrections array, FilmGrain array]
*/

params [
    ["_contrast", 1.15, [0]],
    ["_brightness", 1.0, [0]],
    ["_offset", -0.02, [0]],
    ["_saturation", 0, [0]],
    ["_sharpness", 4.0, [0]],
    ["_grain", 0.006, [0]]
];

_contrast = (_contrast max 0.8) min 1.6;
_brightness = (_brightness max 0.7) min 1.3;
_offset = (_offset max -0.1) min 0.1;
_saturation = (_saturation max 0) min 0.5;
_sharpness = (_sharpness max 1) min 20;
_grain = (_grain max 0) min 0.05;

private _cc = [
    _brightness,
    _contrast,
    _offset,
    [0, 0, 0, 0],
    [1, 1, 1, _saturation],
    [0.2126, 0.7152, 0.0722, 0],
    [-1, -1, 0, 0, 0, 0, 0]
];
private _grainParams = [_grain, _sharpness, 2.01, 0.75, 1.0, 0];

[_cc, _grainParams]
