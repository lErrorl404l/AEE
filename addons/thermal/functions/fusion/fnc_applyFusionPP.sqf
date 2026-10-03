#include "..\..\script_component.hpp"
/*
 * Fusion post-process (issue #204, Track B ENVG-B).
 *
 * The fusion look over the NVG base: a subtle white-hot tint, a slight
 * chromatic offset and sensor noise on the thermal overlay.  Every effect
 * gets ppEffectForceInNVG true so it renders ONLY over the NVG frame (the
 * I2 base), not the normal view.
 *
 * The parameter values are the A3TI fusion branch (workshop 3725008325,
 * fn_ppEffects.sqf, IRNV WHOT case -2).  ChromAberration [0.004,0.004,true],
 * ColorCorrections the DEFAULT_TIPP_SETTINGS brightness and contrast
 * [1.16, 0.62, 0, [0,0,0,0], [1,1,1,0], [1,1,1,0]], DynamicBlur [0.25], and
 * FilmGrain [_GRAIN, 0.75, 1.5, 0.25, 0, true] with _GRAIN = 0.  The grain
 * parameters are the fusion branch and NOT the DTV branch: A3TI uses
 * [0.5, 2.51, 1.67, 0.5, 1.1, true] on its DTV path (case -1), and an earlier
 * revision of this file mis-cited those as fusion values.
 *
 * Priorities (proven non-colliding ladder - A3TI/MKK, re-based into the
 * HUD-safe CfgOpticsEffect band so they do not collide with AEE's other
 * stacks):
 *   ChromAberration 1905, FilmGrain 2005, DynamicBlur 2105, CC 2505.
 * The NVG tube model uses 1200-6000 (RadialBlur 1200, DynamicBlur 4100,
 * CC 5100, FilmGrain 6000); optics 3000/4000/5000; thermal
 * 1300/4200/6500/5200.  Fusion's 1905/2005/2105/2505 are free.
 *
 * Params:
 *   0: _player (OBJECT, default player)
 *
 * Returns: nothing.
 */
params [["_player", player, [objNull]]];
if (isNull _player) exitWith {};

// ─── Handle create/reuse (create once, reuse until torn down) ────────────
private _hChroma  = missionNamespace getVariable [QGVAR(ppHandle_Fusion_Chroma), -1];
private _hGrain   = missionNamespace getVariable [QGVAR(ppHandle_Fusion_Grain), -1];
private _hDynBlur = missionNamespace getVariable [QGVAR(ppHandle_Fusion_DynBlur), -1];
private _hCC      = missionNamespace getVariable [QGVAR(ppHandle_Fusion_CC), -1];
if (_hChroma < 0) then {
    _hChroma = ppEffectCreate ["ChromAberration", 1905];
    if (_hChroma >= 0) then {
        missionNamespace setVariable [QGVAR(ppHandle_Fusion_Chroma), _hChroma];
        private _logMsg = format ["fusion PP: created chroma handle=%1", _hChroma];
        AEE_LOG_DEBUG(_logMsg);
    };
};
if (_hGrain < 0) then {
    _hGrain = ppEffectCreate ["FilmGrain", 2005];
    if (_hGrain >= 0) then {
        missionNamespace setVariable [QGVAR(ppHandle_Fusion_Grain), _hGrain];
        private _logMsg = format ["fusion PP: created grain handle=%1", _hGrain];
        AEE_LOG_DEBUG(_logMsg);
    };
};
if (_hDynBlur < 0) then {
    _hDynBlur = ppEffectCreate ["DynamicBlur", 2105];
    if (_hDynBlur >= 0) then {
        missionNamespace setVariable [QGVAR(ppHandle_Fusion_DynBlur), _hDynBlur];
        private _logMsg = format ["fusion PP: created dynBlur handle=%1", _hDynBlur];
        AEE_LOG_DEBUG(_logMsg);
    };
};
if (_hCC < 0) then {
    _hCC = ppEffectCreate ["ColorCorrections", 2505];
    if (_hCC >= 0) then {
        missionNamespace setVariable [QGVAR(ppHandle_Fusion_CC), _hCC];
        private _logMsg = format ["fusion PP: created CC handle=%1", _hCC];
        AEE_LOG_DEBUG(_logMsg);
    };
};
if (_hChroma < 0 || _hGrain < 0 || _hDynBlur < 0 || _hCC < 0) exitWith {};

// ─── ChromAberration: the lens colour fringing of the fused optic ─────────
// A3TI fusion values (workshop 3725008325, IRNV WHOT case -2):
//   [0.004, 0.004, true]
_hChroma ppEffectAdjust [0.004, 0.004, true];
_hChroma ppEffectCommit 0;
_hChroma ppEffectEnable true;
_hChroma ppEffectForceInNVG true;

// ─── Grain: light sensor noise on the thermal overlay (NETD) ─────────────
// The microbolometer channel has its own noise floor, independent of the
// I2 tube grain.  A3TI fusion values (workshop 3725008325, IRNV WHOT
// case -2): [_GRAIN, 0.75, 1.5, 0.25, 0, true] with _GRAIN = 0.
_hGrain ppEffectAdjust [0, 0.75, 1.5, 0.25, 0, true];
_hGrain ppEffectCommit 0;
_hGrain ppEffectEnable true;
_hGrain ppEffectForceInNVG true;

// ─── DynamicBlur: the fused display softness ─────────────────────────────
// A3TI fusion values (workshop 3725008325, IRNV WHOT case -2): [0.25].
_hDynBlur ppEffectAdjust [0.25];
_hDynBlur ppEffectCommit 0;
_hDynBlur ppEffectEnable true;
_hDynBlur ppEffectForceInNVG true;

// ─── ColourCorrections: white-hot tint on the overlay ────────────────────
// A3TI fusion values (workshop 3725008325, IRNV WHOT case -2):
//   [_BRT, _CNT, 0, [0,0,0,_ALPHA], [1,1,1,0], [1,1,1,0]]
// with DEFAULT_TIPP_SETTINGS = [1.16, 0.62, 0, 0].
_hCC ppEffectAdjust [1.16, 0.62, 0, [0, 0, 0, 0], [1, 1, 1, 0], [1, 1, 1, 0]];
_hCC ppEffectCommit 0;
_hCC ppEffectEnable true;
_hCC ppEffectForceInNVG true;
