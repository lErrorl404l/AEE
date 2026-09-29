// PHASE 69: the sensor detection threshold kernel, measured.
//
// WHY THIS EXISTS.  The kernel aee_thermal_fnc_calculateSensorThreshold is
// PURE ARITHMETIC over scalars, so a dedicated server can call it directly.
// It derives a detection threshold in normalised contrast from the device
// NETD, the signal-to-noise multiple and the background temperature.  It
// renders nothing.
//
// The probe checks a fixed set of device and background pairs.  It does NOT
// sweep a cartesian product of linked inputs, because that would invent
// pairs the real call path can never produce.

private _KERNEL = "aee_thermal_fnc_calculateSensorThreshold";
private _pass = 0;
private _fail = 0;
private _notes = [];
private _summary = "";

if (isNil _KERNEL) then {
    _fail = _fail + 1;
    _notes pushBack "kernel isNil: the sensor threshold kernel is not compiled";
    _summary = "kernel not compiled";
} else {
    // 1. The closed form on a hand-computed case: 5 * 0.05 * 5.0121 / 288.15.
    private _ref = [0.05, 5, 15] call aee_thermal_fnc_calculateSensorThreshold;
    private _expect = 5 * 0.05 * 5.0121 / 288.15;
    if ((_ref isEqualType 0) && (abs (_ref - _expect) < 1e-9)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["closed form gave %1, want %2", _ref, _expect];
    };

    // 2. A cooler device gives a LOWER threshold, so the decision is
    // per-device: the cooled 0.02 C device is more sensitive than the
    // uncooled 0.05 C device.
    private _cooled = [0.02, 5, 15] call aee_thermal_fnc_calculateSensorThreshold;
    if ((_cooled isEqualType 0) && (_cooled < _ref)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["cooled %1 not below uncooled %2", _cooled, _ref];
    };

    // 3. A higher signal-to-noise multiple gives a higher threshold.
    private _snr10 = [0.05, 10, 15] call aee_thermal_fnc_calculateSensorThreshold;
    if ((_snr10 isEqualType 0) && (_snr10 > _ref)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["multiple 10 gave %1, not above %2", _snr10, _ref];
    };

    // 4. The threshold falls below one display band (1/16 = 0.0625).  This
    // is the physical finding: the SENSOR is finer than the DISPLAY, so the
    // two are different quantities and must not be conflated.
    if ((_ref isEqualType 0) && (_ref < (1 / 16))) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["threshold %1 not below one band 0.0625", _ref];
    };

    // 5. A non-positive NETD is refused with -1.
    private _zero = [0, 5, 15] call aee_thermal_fnc_calculateSensorThreshold;
    private _neg = [-0.05, 5, 15] call aee_thermal_fnc_calculateSensorThreshold;
    if ((_zero == -1) && (_neg == -1)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["non-positive NETD gave %1 and %2, want -1", _zero, _neg];
    };

    // 6. The exponent follows the background segment.  A 35 C background is
    // above 290 K, so the day exponent 4.4580 applies.
    private _day = [0.05, 5, 35] call aee_thermal_fnc_calculateSensorThreshold;
    private _dayExpect = 5 * 0.05 * 4.4580 / 308.15;
    if ((_day isEqualType 0) && (abs (_day - _dayExpect) < 1e-9)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["day segment gave %1, want %2", _day, _dayExpect];
    };

    _summary = format ["uncooled=%1 cooled=%2 snr10=%3", _ref, _cooled, _snr10];
};

if (_fail == 0) then {
    diag_log text format ["[P69] [PASS] sensor threshold: %1 checks, %2", _pass, _summary];
} else {
    diag_log text format ["[P69] [FAIL] sensor threshold: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
