// Night grade - several deliberate problems
params ["_strength"];

private _prio = 1500;
private _cc = ppEffectCreate ["ColorCorrections", _prio];       // result never checked for -1
_cc ppEffectEnable true;
_cc ppEffectAdjust [3, 0.2, 0, [0,0,0,0], [1,1,1,1], [0.299,0.587,0.114,0]];   // brightness 3 > 2
_cc ppEffectCommit 0;

// grain created BELOW the grade -> applied before it
private _grain = ppEffectCreate ["FilmGrain", 1400];
_grain ppEffectEnable true;
_grain ppEffectAdjust [1.5, 0.5, 9, 0.75, 1, true];              // intensity, sharpness, size out of range; bool
_grain ppEffectCommit 0;

// same priority as _cc in same scope
private _blur = ppEffectCreate ["DynamicBlur", 1500];
_blur ppEffectEnable true;
_blur ppEffectAdjust [4];
// (no commit)

private _second = ppEffectCreate ["ColorCorrections", 1501];
_second ppEffectEnable true;
_second ppEffectAdjust [1, 1.4, 0.8, [0.1,0.2,0.4,0.3], [1.5,1,1,0.3], [0.299,0.587,0.114,0]];
_second ppEffectCommit 0;
