#include "..\..\script_component.hpp"
/*
 * Fusion HUD compass tape activity gate (issue #204).
 *
 * The drawn display ported from workshop 3810296503 whale_ecoti_llll is shown
 * only while the operator has fusion on and is looking through an image
 * intensifier tube: the setting QGVAR(fusionHud), fusion mode 1, vision mode 1,
 * a live unit and no open map.  Every driver calls this once per frame; it is a
 * handful of getVariable reads, so the idle cost is negligible.
 *
 * The source gated on its own on/off flag (whale_ecoti_llll_on).  Fusion mode 1
 * is the aee equivalent: the optics vision dispatch sets it only when the
 * operator asked for fusion on a fusion-capable headset.
 *
 * Returns: BOOL - true when the tape display should be up.
 */
if (!hasInterface) exitWith { false };

private _on = missionNamespace getVariable [QGVAR(fusionHud), true];
if !(_on isEqualType true) then { _on = true; };
if (!_on) exitWith { false };

private _mode = missionNamespace getVariable [QGVAR(fusionMode), 0];
if !(_mode isEqualType 0) then { _mode = 0; };
if (_mode != 1) exitWith { false };

private _player = call CBA_fnc_currentUnit;
if (isNull _player) exitWith { false };
if (!alive _player) exitWith { false };
if ((currentVisionMode _player) != 1) exitWith { false };
if (visibleMap) exitWith { false };

true
