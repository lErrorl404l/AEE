// PHASE 71: the Johnson-criteria spatial resolver, measured.
//
// WHY THIS EXISTS.  The kernel aee_thermal_fnc_resolveThermalTarget is PURE
// ARITHMETIC over scalars, so a dedicated server can call it directly.  It
// decides whether a target's angular size is large enough for the device to
// resolve, and at which Johnson task level.  It renders nothing.
//
// The cases below are worked from the published relation FOV = 24/mag
// degrees (docs/wiki/research/sensor-device-library.md) and the Johnson
// thresholds (STANAG 4347 Ed. 1, about 50 percent probability).  The target
// is a person's 0.5 m critical dimension; the range sets the angular size.

private _KERNEL = "aee_thermal_fnc_resolveThermalTarget";
private _pass = 0;
private _fail = 0;
private _notes = [];
private _summary = "";

if (isNil _KERNEL) then {
    _fail = _fail + 1;
    _notes pushBack "kernel isNil: the spatial resolver is not compiled";
    _summary = "kernel not compiled";
} else {
    // 1. The return shape is [resolvable, level, linePairs].
    private _shape = [(0.5 / 300), 640, 4] call aee_thermal_fnc_resolveThermalTarget;
    if ((_shape isEqualType []) && ((count _shape) == 3) && ((_shape select 0) isEqualType false)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["kernel returned %1, want a three-element array", typeName _shape];
    };

    // 2. A person at 300 m through a 4x optic on 640x480 is RECOGNITION
    // (level 2).  FOV = 24/4 = 6 deg, IFOV = 6/640 deg/px, angle = 0.5/300
    // rad = 0.0954930 deg, so 10.186 px = 5.093 line pairs.
    private _r300 = [(0.5 / 300), 640, 4] call aee_thermal_fnc_resolveThermalTarget;
    if ((_r300 select 0) && ((_r300 select 1) == 2)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["300 m gave resolve=%1 level=%2 lp=%3, want true level 2", _r300 select 0, _r300 select 1, _r300 select 2];
    };

    // 3. At 200 m the same target reaches IDENTIFICATION (level 3).
    private _r200 = [(0.5 / 200), 640, 4] call aee_thermal_fnc_resolveThermalTarget;
    if ((_r200 select 1) == 3) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["200 m gave level %1 lp=%2, want level 3", _r200 select 1, _r200 select 2];
    };

    // 4. At 1600 m the person spans under one line pair, so contrast alone
    // would not be enough and the kernel reports UNRESOLVED (level 0).
    private _r1600 = [(0.5 / 1600), 640, 4] call aee_thermal_fnc_resolveThermalTarget;
    if ((!(_r1600 select 0)) && ((_r1600 select 1) == 0) && ((_r1600 select 2) < 1)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["1600 m gave resolve=%1 level=%2 lp=%3, want false level 0 below one line pair", _r1600 select 0, _r1600 select 1, _r1600 select 2];
    };

    // 5. Detection starts at 2 px = 1 line pair.  At 1527 m the person is
    // just inside it; at 1529 m just outside.
    private _in = [(0.5 / 1527), 640, 4] call aee_thermal_fnc_resolveThermalTarget;
    private _out = [(0.5 / 1529), 640, 4] call aee_thermal_fnc_resolveThermalTarget;
    if ((_in select 0) && (!(_out select 0))) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["detection boundary: 1527 m resolve=%1, 1529 m resolve=%2", _in select 0, _out select 0];
    };

    // 6. The level ladder is MONOTONIC in range: closer never gives a lower
    // level.  A single sweep of one variable, the range.
    private _monotonic = true;
    private _lastLevel = -1;
    for "_r" from 1200 to 100 step -100 do {
        private _d = [(0.5 / _r), 640, 4] call aee_thermal_fnc_resolveThermalTarget;
        private _lv = _d select 1;
        if (_lv < _lastLevel) then { _monotonic = false; };
        _lastLevel = _lv;
    };
    if (_monotonic) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack "the Johnson level fell as the range closed";
    };

    // 7. A magnifying optic resolves more than a unity goggle: same target,
    // higher line-pair count at 4x than at 1x.
    private _unity = [(0.5 / 200), 640, 1] call aee_thermal_fnc_resolveThermalTarget;
    if ((_unity select 2) < (_r200 select 2)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["unity goggle lp=%1 not below 4x lp=%2", _unity select 2, _r200 select 2];
    };

    // 8. A magnification below 1 and a non-positive resolution are refused.
    private _badMag = [(0.5 / 200), 640, 0.5] call aee_thermal_fnc_resolveThermalTarget;
    private _badRes = [(0.5 / 200), 0, 4] call aee_thermal_fnc_resolveThermalTarget;
    if ((!(_badMag select 0)) && (!(_badRes select 0)) && ((_badMag select 1) == 0) && ((_badRes select 1) == 0)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack "a magnification below 1 or a zero resolution was not refused";
    };

    _summary = format ["300m=%1lp 200m=%2lp 1600m=%3lp mag1@200m=%4lp", _r300 select 2, _r200 select 2, _r1600 select 2, _unity select 2];
};

if (_fail == 0) then {
    diag_log text format ["[P71] [PASS] spatial resolution: %1 checks, %2", _pass, _summary];
} else {
    diag_log text format ["[P71] [FAIL] spatial resolution: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
