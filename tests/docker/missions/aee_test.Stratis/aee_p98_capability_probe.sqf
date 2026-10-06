// PHASE 98: the runtime thermal capability probe against the optic config,
// headless (aee-thermal-realism T18).
//
// WHY THIS EXISTS.  The capability kernel decides whether an optic supports
// native thermal: a visionMode entry named Ti (any case) AND a non-empty
// thermalMode array.  It is config-driven and pure.  The probe reads the
// real optic config that the generated ThermalOptics.hpp patched and checks
// the kernel against the config's own declaration.  It renders nothing.
//
// Emits: [P98] [PASS] / [P98] [FAIL] <reason>.

private _KERNEL = "aee_thermal_fnc_probeThermalCapability";
private _pass = 0;
private _fail = 0;
private _notes = [];

if (isNil _KERNEL) then {
    _fail = _fail + 1;
    _notes pushBack "capability kernel is not compiled";
} else {
    // The generated block lives on this mode in the loaded config.
    private _mode = configFile >> "CfgWeapons" >> "optic_tws" >> "ItemInfo" >> "OpticsModes" >> "TWS";
    private _vm = getArray (_mode >> "visionMode");
    private _tm = getArray (_mode >> "thermalMode");

    // 1. The config declares the thermal optic: a Ti vision mode and a
    //    non-empty thermalMode array.
    private _declares = false;
    {
        if ((_x == "Ti") || (_x == "TI")) then { _declares = true; };
    } forEach _vm;
    if (_declares && {_tm isNotEqualTo []}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["config declares vm=%1 tm=%2", str _vm, str _tm];
    };

    // 2. The kernel matches the optic config (array form).
    private _got = [_vm, _tm] call aee_thermal_fnc_probeThermalCapability;
    if (_got) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack "kernel false for the config arrays";
    };

    // 3. The kernel matches the optic config (CONFIG sub-form, as the caller
    //    resolves it).
    private _gotCfg = [_mode >> "visionMode", _mode >> "thermalMode"] call aee_thermal_fnc_probeThermalCapability;
    if (_gotCfg) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack "kernel false for the config sub-configs";
    };

    // 4. A negative control: no Ti and an empty thermalMode is not capable.
    private _no = [["Normal"], []] call aee_thermal_fnc_probeThermalCapability;
    if (!_no) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack "kernel true for a non-thermal optic";
    };

    // 5. The upper-case TI spelling is accepted too (mod configs use both).
    private _upper = [["TI"], [0]] call aee_thermal_fnc_probeThermalCapability;
    if (_upper) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack "kernel rejects the uppercase TI token";
    };

    _notes pushBack format ["vm=%1 tm=%2", str _vm, str _tm];
};

if (_fail == 0) then {
    diag_log text format ["[P98] [PASS] thermal capability: %1 checks, %2", _pass, _notes];
} else {
    diag_log text format ["[P98] [FAIL] thermal capability: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
