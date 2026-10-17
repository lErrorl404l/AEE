private _h = ppEffectCreate ["DynamicBlur", 1600];
if (_h < 0) exitWith {};
_h ppEffectEnable true;
_h ppEffectAdjust [0.5];
_h ppEffectCommit 0;
