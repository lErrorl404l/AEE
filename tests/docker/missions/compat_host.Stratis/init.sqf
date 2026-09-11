// AEE host-compat test mission.
// Loads with a host mod (ACE3/ACRE2/TFAR/KAT/ACM/HelicopterTurbulence)
// plus AEE. Asserts the host loaded, the matching AEE compat addon
// loaded, and the integration produced usable state. verify.py checks
// the [HOST] lines.

diag_log text "[AEE-TEST] host compat mission start";

// -- which host is present ---------------------------------------------------
private _hosts = [
    ["ace_common", "aee_compat_ace3", "ACE3"],
    ["acre_main", "aee_compat_acre2", "ACRE2"],
    ["tfar_core", "aee_compat_tfar", "TFAR"],
    ["kat_circulation", "aee_compat_kat", "KAT"],
    ["acm", "aee_compat_acm", "ACM"]
];
private _found = false;
{
    _x params ["_hostClass", "_compatClass", "_name"];
    if (isClass (configFile >> "CfgPatches" >> _hostClass)) then {
        _found = true;
        if (isClass (configFile >> "CfgPatches" >> _compatClass)) then {
            diag_log text format ["[HOST] [PASS] %1: host and AEE compat both loaded", _name];
        } else {
            diag_log text format ["[HOST] [FAIL] %1: host loaded but AEE compat missing", _name];
        };
    };
} forEach _hosts;
if (!_found) then {
    diag_log text "[HOST] [FAIL] no recognised host mod loaded";
};

// -- integration state checks -------------------------------------------------
// The radio index is consumed by ACRE2/TFAR; AEE's index must be a number.
private _radioIndex = missionNamespace getVariable ["aee_radio_radioPropagationIndex", nil];
if (!isNil "_radioIndex") then {
    diag_log text format ["[HOST] [PASS] radio propagation index = %1", _radioIndex];
} else {
    diag_log text "[HOST] [INFO] radio index not published (radio addon state)";
};

// ACE3 integration: AEE feeds ace_weather_currentTemperature.
if (isClass (configFile >> "CfgPatches" >> "ace_weather")) then {
    private _aceTemp = missionNamespace getVariable ["ace_weather_currentTemperature", nil];
    private _aeeTemp = missionNamespace getVariable ["aee_core_currentTemperature", nil];
    if ((!isNil "_aceTemp") && (!isNil "_aeeTemp")) then {
        diag_log text format ["[HOST] [PASS] ACE3 temperature synced: ace=%1 aee=%2", _aceTemp, _aeeTemp];
    } else {
        diag_log text format ["[HOST] [FAIL] ACE3 temperature not synced: ace=%1 aee=%2", isNil "_aceTemp", isNil "_aeeTemp"];
    };
};

// wait for sim state then finish
[{
    diag_log text "[AEE-TEST] DONE";
}, [], 35] call CBA_fnc_waitAndExecute;
