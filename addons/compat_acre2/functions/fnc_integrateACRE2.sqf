#include "..\script_component.hpp"
/*
    AEE — ACRE2 Custom Signal Integration

    Registers a custom signal strength callback with ACRE2 that modulates
    the baseline signal using AEE's radio propagation index.

    Propagation index (0.3–2.0) → dB shift (propIdx - 1) × 8 → ±8 dB range.
    Called once from XEH_preInit.  Skips if ACRE2 is not loaded.

    ACRE2 contract: the callback returns [_signalPct 0..1, _signalDBm].
    The percent must be 0..1 (ACRE2 normalises internally); the dB shift
    applies to the dBm value, and the percent is recomputed from the
    shifted dBm across the receiver's sensitivity range.  The baseline
    from acre_sys_signal_fnc_getSignalCore is [_Px 0..1, _maxSignal dBm].
    No return value.
*/

if (!isClass (configFile >> "CfgPatches" >> "acre_sys_signal")) exitWith {};

// The callback reads the AEE variable directly from missionNamespace at
// call time — the expression is hardcoded in the compiled string since
// QUOTE(macro) is not reliably available in HEMTT's preprocessor.
private _callback = compile '
    params ["_freq", "_mW", "_receiverID", "_transmitterID"];

    private _baseline = [_freq, _mW, _receiverID, _transmitterID] call acre_sys_signal_fnc_getSignalCore;
    _baseline params ["_Px", "_maxSignal"];

    private _propIdx = missionNamespace getVariable ["aee_radio_radioPropagationIndex", 1];
    if (_propIdx <= 0) then { _propIdx = 1.0 };

    private _dB_shift = (_propIdx - 1) * (missionNamespace getVariable [QEGVAR(compat_acre2,signalDBShift), 8]);

    // Apply the shift in dBm, then recompute the percent over the
    // receiver sensitivity window (defaults: -110..0 dBm).
    private _signalDBm = _maxSignal + _dB_shift;
    private _min = getNumber (configFile >> "CfgRadio" >> "ACRE_BASE_RECEIVER" >> "sensitivityMin");
    private _max = getNumber (configFile >> "CfgRadio" >> "ACRE_BASE_RECEIVER" >> "sensitivityMax");
    if (_max - _min == 0) then { _min = (missionNamespace getVariable [QEGVAR(compat_acre2,signalSensitivityMin), -110]); _max = 0; };

    private _signalPct = ((_signalDBm - _min) / (_max - _min)) max 0 min 1;

    [_signalPct, _signalDBm]
';

[_callback] call acre_api_fnc_setCustomSignalFunc;

diag_log "[AEE][ACRE2] Custom signal function registered (propagation index → ±8 dB shift)";
