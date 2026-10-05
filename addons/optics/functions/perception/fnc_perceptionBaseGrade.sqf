#include "..\..\script_component.hpp"

/*
Base-anchor clamp kernel (human-vision model, grade slice).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The composition
kernel calls this; the kernel bounds the composed grade to the base game's own
neutral default plus a small deviation, so normal vision never pushes an extreme
look.

The base game ships the neutral default grade brightness 1, contrast 1, offset
0.  AEE reads that anchor from the loaded config at run time and never ships or
copies the Bohemia config.  This kernel takes the tone triple, the anchor and
the tone strength and allows only a small bounded deviation: a tiny contrast
and black-point lift.  Contrast may only rise and the black point may only
deepen, so the grade cannot wash out or flatten the image.  The desaturation
alpha is bounded to 0 to 0.10.

Per-constant source register:
  fallback anchor         [1, 1, 0].  SOURCED: a3\functions_f\config.cpp line
                          3553 of functions_f.pbo, build 2025-08-11.  The
                          fallback is a number triple with a source; it is not
                          shipped content.
  brightness bound        0.03 either side of the anchor.  UNSOURCED:
                          operator-tunable small deviation.
  contrast bound          0.00 to 0.08 above the anchor.  UNSOURCED:
                          operator-tunable small deviation; contrast may only
                          rise.
  offset bound            -0.02 to 0.00 from the anchor.  UNSOURCED:
                          operator-tunable; the black point may only deepen.
  desaturation alpha      0 to 0.10.  UNSOURCED: the engine desaturates only and
                          the bounded improvement must not drain the image.

Arguments:
  0: Array  - tone triple [brightness, contrast, offset] from the tone kernel
  1: Array  - anchor triple [brightness, contrast, offset] from the base game
  2: Number - tone strength, 0 to 1
  3: Number - desaturation alpha, clamped 0 to 0.10

Returns:
  Array - [brightness, contrast, offset, alpha].  A malformed input falls back
          to the neutral anchor and returns the in-bound four-vector.
*/

params [
    ["_tone", [1, 1, 0], [[]]],
    ["_anchor", [1, 1, 0], [[]]],
    ["_strength", 1, [0]],
    ["_desatAlpha", 0, [0]]
];

// Guard the tone triple: a malformed value keeps the neutral tone.
private _bT = 1;
private _cT = 1;
private _oT = 0;
if ((_tone isEqualType []) && ((count _tone) >= 3)) then {
    private _t0 = _tone select 0;
    private _t1 = _tone select 1;
    private _t2 = _tone select 2;
    if ((_t0 isEqualType 0) && (_t1 isEqualType 0) && (_t2 isEqualType 0)) then {
        _bT = _t0;
        _cT = _t1;
        _oT = _t2;
    };
};

// Guard the anchor: a malformed value keeps the neutral anchor.
private _b0 = 1;
private _c0 = 1;
private _o0 = 0;
if ((_anchor isEqualType []) && ((count _anchor) >= 3)) then {
    private _a0 = _anchor select 0;
    private _a1 = _anchor select 1;
    private _a2 = _anchor select 2;
    if ((_a0 isEqualType 0) && (_a1 isEqualType 0) && (_a2 isEqualType 0)) then {
        _b0 = _a0;
        _c0 = _a1;
        _o0 = _a2;
    };
};

private _s = 0;
if (_strength isEqualType 0) then {
    _s = ((_strength max 0) min 1);
};

private _alpha = 0;
if (_desatAlpha isEqualType 0) then {
    _alpha = ((_desatAlpha max 0) min 0.10);
};

private _db = ((_bT - 1) * _s);
private _dc = ((_cT - 1) * _s);
private _do = (_oT * _s);

private _b = (((_b0 + _db) max (_b0 - 0.03)) min (_b0 + 0.03));
private _c = (((_c0 + _dc) max _c0) min (_c0 + 0.08));
private _o = (((_o0 + _do) max (_o0 - 0.02)) min _o0);

[_b, _c, _o, _alpha]
