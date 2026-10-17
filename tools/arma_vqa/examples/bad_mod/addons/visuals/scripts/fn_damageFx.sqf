// Damage FX
private _h = ppEffectCreate ["ColorCorrections", 1700];
if (_h < 0) exitWith {};
_h ppEffectEnable true;
_h ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,0.2], [0.299,0.587,0.114,0]];
_h ppEffectCommit 0;

// fade back to normal... and immediately switch it off
_h ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,1], [0.299,0.587,0.114,0]];
_h ppEffectCommit 5;
_h ppEffectEnable false;
ppEffectDestroy _h;

"WetDistortion" ppEffectAdjust [1,1,1, 4.1,3.7,2.5,1.85, 0.0054,0.0041,0.009,0.007, 0.5,0.3,10,6];
"WetDistortion" ppEffectCommit 0;
"WetDistortion" ppEffectEnable true;

// flat colours with by-name syntax
"colorCorrections" ppEffectAdjust [1,1,0, 0,0,0,0, 1,1,1,1, 0.299,0.587,0.114,0];
"colorCorrections" ppEffectCommit 0;
"colorCorrections" ppEffectEnable true;

private _adv = ppEffectCreate ["LightShafts", 100];
private _typo = ppEffectCreate ["ChromaticAberration", 200];
private _nvg = ppEffectCreate ["RadialBlur", 100];
_nvg ppEffectEnable true;
_nvg ppEffectAdjust [0.02, 0.02, 0.1, 0.1];
_nvg ppEffectCommit 0;
// NVG night vision mode toggled elsewhere; effect never forced into NVG
ppEffectDestroy _nvg;
"colorCorrections" ppEffectForceInNVG true;
