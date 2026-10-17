private _h = ppEffectCreate ["ColorCorrections", 1600];
if (_h < 0) exitWith {};
_h ppEffectEnable true;
_h ppEffectAdjust [1, 1, 0, [0, 0, 0, 0], [1, 1, 1, 1], [0.299, 0.587, 0.114, 0]];
_h ppEffectCommit 0;
