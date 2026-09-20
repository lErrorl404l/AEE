#include "..\..\script_component.hpp"
/*
 * Fusion post-process (issue #204, Track B ENVG-B).
 *
 * The fusion look over the NVG base: a subtle white-hot tint + grain
 * on the thermal overlay, at the proven A3TI/MKK priorities.  Every
 * effect gets ppEffectForceInNVG true so it renders ONLY over the NVG
 * frame (the I2 base), not the normal view.
 *
 * Priorities (proven non-colliding ladder - A3TI/MKK):
 *   FilmGrain 2005, ColorCorrections 2505.
 * The NVG tube model uses 1200-6000 (RadialBlur 1200, DynamicBlur
 * 4100, CC 5100, FilmGrain 6000); optics 3000/4000/5000; thermal
 * 1300/4200/6500/5200.  Fusion's 2005/2505 are free.
 *
 * Params:
 *   0: _player (OBJECT, default player)
 *
 * Returns: nothing.
 */
params [["_player", player, [objNull]]];
if (isNull _player) exitWith {};

// ─── Handle create/reuse (create once, reuse until torn down) ────────────
private _hGrain = missionNamespace getVariable [QGVAR(ppHandle_Fusion_Grain), -1];
private _hCC    = missionNamespace getVariable [QGVAR(ppHandle_Fusion_CC), -1];
if (_hGrain < 0 || _hCC < 0) then {
    if (_hGrain < 0) then {
        _hGrain = ppEffectCreate ["FilmGrain", 2005];
        if (_hGrain >= 0) then {
            missionNamespace setVariable [QGVAR(ppHandle_Fusion_Grain), _hGrain];
        };
    };
    if (_hCC < 0) then {
        _hCC = ppEffectCreate ["ColorCorrections", 2505];
        if (_hCC >= 0) then {
            missionNamespace setVariable [QGVAR(ppHandle_Fusion_CC), _hCC];
        };
    };
};
if (_hGrain < 0 || _hCC < 0) exitWith {};

// ─── Grain: light sensor noise on the thermal overlay (NETD) ─────────────
// The microbolometer channel has its own noise floor, independent of the
// I2 tube grain.  A3TI fusion values (workshop 3725008325):
//   [_GRAIN, 0.75, 1.5, 0.25, 0, true]  (IRNV WHOT case -2)
_hGrain ppEffectAdjust [0.5, 2.51, 1.67, 0.5, 1.1, true];
_hGrain ppEffectCommit 0;
_hGrain ppEffectEnable true;
_hGrain ppEffectForceInNVG true;

// ─── ColourCorrections: white-hot tint on the overlay ────────────────────
// A3TI fusion values (workshop 3725008325, IRNV WHOT case -2):
//   [_BRT, _CNT, 0, [0,0,0,_ALPHA], [1,1,1,0], [1,1,1,0]]
// with DEFAULT_TIPP_SETTINGS = [1.16, 0.62, 0, 0].
_hCC ppEffectAdjust [1.16, 0.62, 0, [0, 0, 0, 0], [1, 1, 1, 0], [1, 1, 1, 0]];
_hCC ppEffectCommit 0;
_hCC ppEffectEnable true;
_hCC ppEffectForceInNVG true;
