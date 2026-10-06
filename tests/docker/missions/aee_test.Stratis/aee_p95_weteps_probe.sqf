// PHASE 95: wet-surface emissivity, headless (aee-thermal-realism T18).
//
// WHY THIS EXISTS.  A thin water film raises a land surface's long-wave
// emissivity toward the liquid-water value 0.96.  The kernel blends the dry
// material value toward 0.96 by the surface wetness and clamps to 0..1.  The
// kernel is pure, so a dedicated server calls it directly.  It renders
// nothing.
//
// Emits: [P95] [PASS] / [P95] [FAIL] <reason>.

private _KERNEL = "aee_thermal_fnc_getEffectiveEmissivity";
private _pass = 0;
private _fail = 0;
private _notes = [];

if (isNil _KERNEL) then {
    _fail = _fail + 1;
    _notes pushBack "emissivity kernel is not compiled";
} else {
    private _dry = [0.90, 0] call aee_thermal_fnc_getEffectiveEmissivity;
    private _mid = [0.90, 0.5] call aee_thermal_fnc_getEffectiveEmissivity;
    private _wet = [0.90, 1] call aee_thermal_fnc_getEffectiveEmissivity;

    // 1. A fully wet surface reaches the liquid-water 0.96.
    if ((_wet isEqualType 0) && {abs (_wet - 0.96) < 1e-9}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["wet gave %1, want 0.96", _wet];
    };

    // 2. A dry surface keeps its dry value.
    if ((_dry isEqualType 0) && {abs (_dry - 0.90) < 1e-9}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["dry gave %1, want 0.90", _dry];
    };

    // 3. Emissivity rises with wetness.
    if ((_dry < _mid) && {_mid < _wet}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["not monotone: dry %1 mid %2 wet %3", _dry, _mid, _wet];
    };

    // 4. An over-unity dry value is clamped to 1.
    private _clamp = [1.5, 0] call aee_thermal_fnc_getEffectiveEmissivity;
    if ((_clamp isEqualType 0) && {abs (_clamp - 1) < 1e-9}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["clamp gave %1, want 1", _clamp];
    };

    _notes pushBack format ["dry=%1 mid=%2 wet=%3", _dry, _mid, _wet];
};

if (_fail == 0) then {
    diag_log text format ["[P95] [PASS] wet emissivity: %1 checks, %2", _pass, _notes];
} else {
    diag_log text format ["[P95] [FAIL] wet emissivity: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
