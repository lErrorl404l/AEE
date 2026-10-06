#include "..\..\script_component.hpp"

/*
Perception deviation kernel (discolouration and blindness detection, pure).

The perception driver reconstructs the view state each tick.  This kernel
compares the model's expectation against the state that reached the render
and reports the deviations an operator must know about.  It is pure: no
world, no module global, no engine command and no log line.  The caller
supplies every input, so the tests drive it with fixtures.

Flags returned, in order:
  discolouration   the applied grade differs from the expected grade beyond
                   the per-channel tolerance
  blindness        the pupil sits on a clamp, the aperture is pinned and the
                   scene and adapted lux are extreme
  gradeMismatch    the applied grade is absent or malformed
  stuckAdaptation  the direction is non-zero and the time to adapt did not
                   fall over the window since the previous sample
  detail           a short string naming the flags that fired

Constants (graded):
  GRADE_TOL      0.02 per channel.  UNSOURCED.  It matches the aperture pin
                 threshold the eye driver uses, the engine's own rounding.
  ALPHA_TOL      0.02.  UNSOURCED.  Same reasoning as GRADE_TOL.
  APERTURE_EPS   0.5.  UNSOURCED.  An aperture within this of a clamp end
                 counts as pinned.
  PUPIL_EPS      0.1 mm.  UNSOURCED.  A pupil within this of a clamp end
                 counts as clamped.
  LUX_FLOOR      0.01 cd/m2.  UNSOURCED.  At or below this the scene reads
                 as effectively black.
  STUCK_TOL      0.05 s.  UNSOURCED.  A time to adapt that fell by less than
                 this over the window did not move.

Arguments:
  0:  Array  - expected grade [brightness, contrast, offset, alpha]
  1:  Array  - applied grade [brightness, contrast, offset, alpha]
  2:  Array  - adapted state [level, target, direction, timeToAdapt]
  3:  Number - aperture actually applied
  4:  Number - pupil diameter, mm
  5:  Number - aperture clamp low end
  6:  Number - aperture clamp high end
  7:  Number - pupil clamp low end, mm
  8:  Number - pupil clamp high end, mm
  9:  Number - scene illuminance, lux
  10: Number - adapted luminance, cd/m2
  11: Number - previous time to adapt, s; -1 when unknown

Returns:
  Array - [discolouration, blindness, gradeMismatch, stuckAdaptation, detail]
*/

params [
    ["_expected", [1, 1, 0, 0], [[]]],
    ["_applied", [1, 1, 0, 0], [[]]],
    ["_adaptedState", [0, 0, 0, 0], [[]]],
    ["_aperture", 8, [0]],
    ["_pupilMm", 4.9, [0]],
    ["_apertureMin", 8, [0]],
    ["_apertureMax", 50, [0]],
    ["_pupilMin", 1.9, [0]],
    ["_pupilMax", 8.0, [0]],
    ["_sceneLux", 1, [0]],
    ["_adaptedLux", 1, [0]],
    ["_prevTimeToAdapt", -1, [0]]
];

private _gradeTol = 0.02;
private _alphaTol = 0.02;
private _apertureEps = 0.5;
private _pupilEps = 0.1;
private _luxFloor = 0.01;
private _stuckTol = 0.05;

private _detail = "";
private _sep = "";

// ── Grade comparison ────────────────────────────────────────────────────────
private _appliedOk = (_applied isEqualType []) && {(count _applied) >= 3};
private _gradeMismatch = !_appliedOk;

private _discolouration = false;
if (_appliedOk && {(_expected isEqualType [])} && {(count _expected) >= 3}) then {
    for "_i" from 0 to 2 do {
        private _e = _expected select _i;
        private _a = _applied select _i;
        if !(_e isEqualType 0) then { _e = 0; };
        if !(_a isEqualType 0) then { _a = 0; };
        if (abs(_a - _e) > _gradeTol) then { _discolouration = true; };
    };
    if ((count _expected) >= 4 && {(count _applied) >= 4}) then {
        private _ea = _expected select 3;
        private _aa = _applied select 3;
        if !(_ea isEqualType 0) then { _ea = 0; };
        if !(_aa isEqualType 0) then { _aa = 0; };
        if (abs(_aa - _ea) > _alphaTol) then { _discolouration = true; };
    };
};

// ── Blindness ───────────────────────────────────────────────────────────────
private _pupilClamped = (_pupilMm <= (_pupilMin + _pupilEps)) || {_pupilMm >= (_pupilMax - _pupilEps)};
private _aperturePinned = (_aperture <= (_apertureMin + _apertureEps)) || {_aperture >= (_apertureMax - _apertureEps)};
private _luxExtreme = (_sceneLux <= _luxFloor) || {_adaptedLux <= _luxFloor};
private _blindness = _pupilClamped && {_aperturePinned} && {_luxExtreme};

// ── Stuck adaptation ────────────────────────────────────────────────────────
private _stuckAdaptation = false;
if ((_adaptedState isEqualType []) && {(count _adaptedState) >= 4}) then {
    private _dir = _adaptedState select 2;
    private _time = _adaptedState select 3;
    if !(_dir isEqualType 0) then { _dir = 0; };
    if !(_time isEqualType 0) then { _time = 0; };
    if ((_dir != 0) && {(_prevTimeToAdapt isEqualType 0)} && {_prevTimeToAdapt >= 0}) then {
        if ((_prevTimeToAdapt - _time) < _stuckTol) then { _stuckAdaptation = true; };
    };
};

if (_discolouration) then { _detail = _detail + _sep + "discolouration"; _sep = " "; };
if (_blindness) then { _detail = _detail + _sep + "blindness"; _sep = " "; };
if (_gradeMismatch) then { _detail = _detail + _sep + "gradeMismatch"; _sep = " "; };
if (_stuckAdaptation) then { _detail = _detail + _sep + "stuckAdaptation"; _sep = " "; };

[_discolouration, _blindness, _gradeMismatch, _stuckAdaptation, _detail]
