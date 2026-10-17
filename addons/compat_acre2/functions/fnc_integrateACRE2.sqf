#include "..\script_component.hpp"
/*
    AEE — ACRE2 Custom Signal Integration

    Registers a custom signal strength callback with ACRE2 that subtracts
    AEE's environmental excess loss (aee_radio_excessLossDB: cold-battery
    derating and EMP upset, plus HF D-layer absorption recomputed at the
    link's own frequency) from ACRE's own ITM signal.  ACRE keeps the
    distance, frequency and terrain loss; nothing is counted twice.
    Called once from XEH_preInit.  Skips if ACRE2 is not loaded.

    ACRE2 contract: the callback returns [_signalPct 0..1, _signalDBm].
    The percent must be 0..1 (ACRE2 normalises internally); the loss
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

    // AEE environmental excess loss (dB) that ACRE ITM does not model: the
    // battery and EMP terms, plus HF D-layer absorption at THIS link
    // frequency (ITU-R P.533, zero at 30 MHz and above).
    private _excess = missionNamespace getVariable ["aee_radio_excessLossDB", 0];
    private _ionoRef = 0;
    private _ionoLink = 0;
    private _num = missionNamespace getVariable ["aee_radio_dLayerNumerator", 0];
    private _fL = missionNamespace getVariable ["aee_radio_gyroFreqMHz", 1];
    private _fRef = (missionNamespace getVariable ["aee_radio_radioFrequencyHz", 1e8]) / 1e6;
    if (_fRef < 30) then { _ionoRef = _num / (((_fRef + _fL) ^ 1.98) + 10.2); };
    if (_freq < 30) then { _ionoLink = _num / (((_freq + _fL) ^ 1.98) + 10.2); };
    // Flare D-RAP absorption, re-evaluated at the link frequency.
    private _haf = missionNamespace getVariable ["aee_weather_flareHAF", 0];
    private _flareRef = 0;
    private _flareLink = 0;
    if (_haf > 0) then {
        _flareRef = (_haf / _fRef) ^ 1.5;
        _flareLink = (_haf / _freq) ^ 1.5;
    };
    private _signalDBm = _maxSignal - (_excess - _ionoRef + _ionoLink - _flareRef + _flareLink);

    private _min = getNumber (configFile >> "CfgRadio" >> "ACRE_BASE_RECEIVER" >> "sensitivityMin");
    private _max = getNumber (configFile >> "CfgRadio" >> "ACRE_BASE_RECEIVER" >> "sensitivityMax");
    if (_max - _min == 0) then { _min = missionNamespace getVariable ["aee_compat_acre2_signalSensitivityMin", -110]; _max = 0; };

    private _signalPct = ((_signalDBm - _min) / (_max - _min)) max 0 min 1;

    [_signalPct, _signalDBm]
';

[_callback] call acre_api_fnc_setCustomSignalFunc;

AEE_LOG_INFO("[ACRE2] Custom signal function registered (AEE environmental excess loss, dB)");
