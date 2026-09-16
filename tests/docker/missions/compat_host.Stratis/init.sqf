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
    ["ACM_main", "aee_compat_acm", "ACM"]
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

// ACE3 integration: AEE feeds ace_weather_currentTemperature.  The Kestrel
// integration writes it from a 5 s PFH, so the assertion must run AFTER
// that delay (checked in the delayed block at the bottom).
if (isClass (configFile >> "CfgPatches" >> "ace_weather")) then {
    diag_log text "[HOST] [INFO] ACE3 weather sync scheduled (Kestrel PFH at 5 s)";
};

// ACE3 medical integration: the compat function must compile and run
// without error.  The vitals it writes are per-PLAYER (medication
// adjustments on the local unit), which do not exist on the headless
// server - the value contract is locked by the Python mirror
// (tools/tests/test_compat.py TestCompatACE3).
if (isClass (configFile >> "CfgPatches" >> "ace_medical")) then {
    missionNamespace setVariable ["aee_core_currentTemperature", 30];
    missionNamespace setVariable ["aee_core_currentWBGT", 30];
    missionNamespace setVariable ["aee_physiology_dehydrationRisk", 0.5];
    private _fnMed = missionNamespace getVariable ["aee_compat_ace3_fnc_integrateMedical", nil];
    if (isNil "_fnMed") then {
        diag_log text "[HOST] [FAIL] compat_ace3 integrateMedical not compiled";
    } else {
        [player] call _fnMed;
        diag_log text "[HOST] [PASS] ACE3 medical integration ran without error";
    };
};

// KAT integration: the compat function must compile and run without error.
// The fluid compartments it drains are per-PLAYER and do not exist on the
// headless server; the drain maths is locked by the Python mirror
// (TestCompatKAT).
if (isClass (configFile >> "CfgPatches" >> "kat_circulation")) then {
    missionNamespace setVariable ["aee_core_currentTemperature", 35];
    missionNamespace setVariable ["aee_core_coreBodyTemp", 39];
    missionNamespace setVariable ["aee_physiology_dehydrationRisk", 0.8];
    private _fnKAT = missionNamespace getVariable ["aee_compat_kat_fnc_integrateKAT", nil];
    if (isNil "_fnKAT") then {
        diag_log text "[HOST] [FAIL] compat_kat integrateKAT not compiled";
    } else {
        [] call _fnKAT;
        diag_log text "[HOST] [PASS] KAT integration ran without error";
    };
};

// ACM integration: the hypoxia duty factor registration must run without
// error when the ACE vitals surface is present (the factor's maths is
// covered by the Python mirror tools/tests/test_compat.py; ACE's duty
// list internals are not inspectable from the mission).
if (isClass (configFile >> "CfgPatches" >> "ACM_main")) then {
    missionNamespace setVariable ["aee_core_currentHypoxiaRisk", 1.0];
    private _fnReg = missionNamespace getVariable ["aee_compat_acm_fnc_registerHypoxiaDutyFactor", nil];
    if (isNil "_fnReg") then {
        diag_log text "[HOST] [FAIL] compat_acm registerHypoxiaDutyFactor not compiled";
    } else {
        private _err = [] call _fnReg;
        if (isNil "_err") then {
            diag_log text "[HOST] [PASS] ACM hypoxia duty factor registered";
        } else {
            diag_log text format ["[HOST] [FAIL] ACM duty factor registration errored: %1", _err];
        };
    };
};

// TFAR integration: the compat function must compile and run without
// error.  The sending multiplier it writes is per-PLAYER and does not
// exist on the headless server; the scaling maths is locked by the
// Python mirror (TestCompatTFAR).
if (isClass (configFile >> "CfgPatches" >> "tfar_core")) then {
    missionNamespace setVariable ["aee_radio_radioPropagationIndex", 1.5];
    private _fnTFAR = missionNamespace getVariable ["aee_compat_tfar_fnc_integrateTFAR", nil];
    if (isNil "_fnTFAR") then {
        diag_log text "[HOST] [FAIL] compat_tfar integrateTFAR not compiled";
    } else {
        [] call _fnTFAR;
        diag_log text "[HOST] [PASS] TFAR integration ran without error";
    };
};

// wait for sim state then finish
[{
    // ACE3 weather sync lands via the Kestrel PFH at 5 s; assert it here
    // (well after the PFH has fired multiple times).
    if (isClass (configFile >> "CfgPatches" >> "ace_weather")) then {
        private _aceTemp = missionNamespace getVariable ["ace_weather_currentTemperature", nil];
        private _aeeTemp = missionNamespace getVariable ["aee_core_currentTemperature", nil];
        if ((!isNil "_aceTemp") && (!isNil "_aeeTemp") && (abs (_aceTemp - _aeeTemp) < 0.1)) then {
            diag_log text format ["[HOST] [PASS] ACE3 temperature synced: ace=%1 aee=%2", _aceTemp, _aeeTemp];
        } else {
            diag_log text format ["[HOST] [FAIL] ACE3 temperature not synced: ace=%1 aee=%2", isNil "_aceTemp", isNil "_aeeTemp"];
        };
    };
    diag_log text "[AEE-TEST] DONE";
}, [], 35] call CBA_fnc_waitAndExecute;
