#include "..\script_component.hpp"
/*
    AEE — ACRE2 Custom Signal Integration

    Registers a custom signal strength callback with ACRE2 that modulates
    the baseline signal using AEE's radio propagation index.

    Propagation index (0.3–2.0) → dB shift (propIdx - 1) × 8 → ±8 dB range.
    Called once from XEH_preInit.  Skips if ACRE2 is not loaded.
    No return value.
*/

if (!isClass (configFile >> "CfgPatches" >> "acre_sys_signal")) exitWith {};

// The callback reads the AEE variable directly from missionNamespace at
// call time — the expression is hardcoded in the compiled string since
// QUOTE(macro) is not reliably available in HEMTT's preprocessor.
private _callback = compile '
    params ["_freq", "_mW", "_receiverID", "_transmitterID"];

    private _baseline = [_freq, _mW, _receiverID, _transmitterID] call acre_sys_signal_fnc_getSignalCore;

    private _propIdx = missionNamespace getVariable ["aee_core_radioPropagationIndex", 1];
    if (_propIdx <= 0) then { _propIdx = 1.0 };

    private _dB_shift = (_propIdx - 1) * 8;

    private _signalPct = ((_baseline select 0) + _dB_shift) max 0 min 100;
    private _signalDBm = (_baseline select 1) + _dB_shift;

    [_signalPct, _signalDBm]
';

[_callback] call acre_api_fnc_setCustomSignalFunc;

diag_log "[AEE][ACRE2] Custom signal function registered (propagation index → ±8 dB shift)";
