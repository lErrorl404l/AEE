#include "..\..\script_component.hpp"
/*
 * Fusion mode cycle (issue #204, Track B ENVG-B).
 *
 * The operator can blend between the two fusion channels:
 *   0 = I2 only  (NVG base, no thermal overlay)
 *   1 = Fused    (NVG base + emissive thermal overlay)
 *
 * Real ENVG-B has a third (thermal-only) state, but over a headset NVG
 * the thermal-only view is exactly the engine's TI mode (2) - the
 * operator cycles to it with the vanilla vision key.  So the fusion
 * modes here are: I2-only and fused.
 *
 * The state lives in QGVAR(fusionMode) (0 = I2 only, 1 = fused).
 *
 * Params:
 *   0: _force (SCALAR, optional) - force a specific mode (0 or 1).
 *      Default: cycle 0 <-> 1.
 *
 * Returns: the new mode (SCALAR).
 */
params [["_force", -1, [0]]];

private _mode = missionNamespace getVariable [QGVAR(fusionMode), 0];
if (_force >= 0) then {
    _mode = _force min 1 max 0;
} else {
    _mode = 1 - _mode;
};

missionNamespace setVariable [QGVAR(fusionMode), _mode];

if (_mode == 0) then {
    // Tear the field-of-view frame down with the other fusion effects.
    [false] call FUNC(updateFusionFrame);
    // I2 only: tear down the fusion effects so the NVG base is clean.  Each
    // destroy is reported, so the full handle lifecycle appears in the log:
    // created in fnc_applyFusionPP, destroyed here.  A handle that outlives
    // its mode is a silent leak, and a silent leak cannot be found.
    private _hGrain = missionNamespace getVariable [QGVAR(ppHandle_Fusion_Grain), -1];
    if (_hGrain >= 0) then {
        ppEffectDestroy _hGrain;
        private _logMsg = format ["fusion PP: destroyed grain handle=%1", _hGrain];
        AEE_LOG_DEBUG(_logMsg);
    };
    private _hCC = missionNamespace getVariable [QGVAR(ppHandle_Fusion_CC), -1];
    if (_hCC >= 0) then {
        ppEffectDestroy _hCC;
        private _logMsg = format ["fusion PP: destroyed CC handle=%1", _hCC];
        AEE_LOG_DEBUG(_logMsg);
    };
    missionNamespace setVariable [QGVAR(ppHandle_Fusion_Grain), -1];
    missionNamespace setVariable [QGVAR(ppHandle_Fusion_CC), -1];
};

_mode
