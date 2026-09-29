// PHASE 70: atmospheric transmission and the radiance common-mode, measured.
//
// WHY THIS EXISTS.  The kernel aee_thermal_fnc_calculateAtmosphericTransmission
// is PURE ARITHMETIC over scalars, so a dedicated server can call it directly.
// It returns the path transmission tau that makes the radiance kernel's third
// term live, and it renders nothing.
//
// The probe checks the three published Minkina and Klecha 2016 anchors at
// 15 C and 50 percent relative humidity, then the common-mode property of the
// completed radiance kernel.  It does NOT sweep a cartesian product of linked
// inputs, because that invents pairs the real path can never produce.

private _KERNEL = "aee_thermal_fnc_calculateAtmosphericTransmission";
private _CALC = "aee_thermal_fnc_calculateBandRadiance";
private _pass = 0;
private _fail = 0;
private _notes = [];
private _summary = "";

if (isNil _KERNEL || isNil _CALC) then {
    _fail = _fail + 1;
    _notes pushBack "kernel isNil: the transmission or radiance kernel is not compiled";
    _summary = "kernel not compiled";
} else {
    // 1. The three published anchors at 15 C and 50 percent humidity.
    private _anchors = [[100, 0.9306], [1000, 0.7828], [5000, 0.5724]];
    {
        _x params ["_d", "_want"];
        private _got = [_d, 50, 15, 0, 0, 1.225] call aee_thermal_fnc_calculateAtmosphericTransmission;
        if ((_got isEqualType 0) && (abs (_got - _want) < 1e-3)) then {
            _pass = _pass + 1;
        } else {
            _fail = _fail + 1;
            _notes pushBack format ["anchor %1 m gave %2, want %3", _d, _got, _want];
        };
    } forEach _anchors;

    // 2. A zero-length path absorbs nothing.
    private _zero = [0, 50, 15, 0, 0, 1.225] call aee_thermal_fnc_calculateAtmosphericTransmission;
    if ((_zero isEqualType 0) && (abs (_zero - 1) < 1e-9)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["zero-length path gave %1, want 1", _zero];
    };

    // 3. A negative path is refused.
    private _neg = [-1, 50, 15, 0, 0, 1.225] call aee_thermal_fnc_calculateAtmosphericTransmission;
    if (_neg == -1) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["negative path gave %1, want -1", _neg];
    };

    // 4. Transmission falls with range and with humidity.
    private _near = [100, 50, 15, 0, 0, 1.225] call aee_thermal_fnc_calculateAtmosphericTransmission;
    private _far = [5000, 50, 15, 0, 0, 1.225] call aee_thermal_fnc_calculateAtmosphericTransmission;
    private _dry = [1000, 10, 15, 0, 0, 1.225] call aee_thermal_fnc_calculateAtmosphericTransmission;
    private _wet = [1000, 90, 15, 0, 0, 1.225] call aee_thermal_fnc_calculateAtmosphericTransmission;
    if ((_near > _far) && (_dry > _wet)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["not falling: 100 m %1, 5000 m %2; dry %3, wet %4", _near, _far, _dry, _wet];
    };

    // 5. The common-mode property.  A target and its local background at the
    // SAME range keep their difference scaled by exactly tau, and the path
    // radiance term is added to BOTH identically.  A fixed pair, not a sweep.
    private _tau = 0.7;
    private _tPath = 15;
    private _eps = 0.92;
    private _tAir = 15;
    private _fGround = 0.5;
    private _tTarget = 40;
    private _tBack = 0;
    private _tTarget0 = [_tTarget, _eps, _tAir, _fGround, _tAir] call aee_thermal_fnc_calculateBandRadiance;
    private _tBack0 = [_tBack, _eps, _tAir, _fGround, _tAir] call aee_thermal_fnc_calculateBandRadiance;
    private _tTargetA = [_tTarget, _eps, _tAir, _fGround, _tAir, _tau, _tPath] call aee_thermal_fnc_calculateBandRadiance;
    private _tBackA = [_tBack, _eps, _tAir, _fGround, _tAir, _tau, _tPath] call aee_thermal_fnc_calculateBandRadiance;
    private _diffA = _tTargetA - _tBackA;
    private _diffScaled = _tau * (_tTarget0 - _tBack0);
    private _diffOk = (abs (_diffA - _diffScaled) < (1e-9 + (1e-6 * (abs _diffScaled))));
    if (_diffOk) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["difference %1 not tau x difference0 %2", _diffA, _diffScaled];
    };

    // 6. The path term is added to the target and the background identically.
    private _pathTarget = _tTargetA - (_tau * _tTarget0);
    private _pathBack = _tBackA - (_tau * _tBack0);
    if (abs (_pathTarget - _pathBack) < (1e-9 + (1e-6 * (abs _pathTarget)))) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["path term differs: target %1, background %2", _pathTarget, _pathBack];
    };

    // 7. tau = 1 reproduces the old two-term result exactly.
    private _tOne = [_tTarget, _eps, _tAir, _fGround, _tAir, 1, _tPath] call aee_thermal_fnc_calculateBandRadiance;
    if (abs (_tOne - _tTarget0) < (1e-12 + (1e-12 * (abs _tTarget0)))) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["tau=1 gave %1, want the old result %2", _tOne, _tTarget0];
    };

    private _anchor1000 = [1000, 50, 15, 0, 0, 1.225] call aee_thermal_fnc_calculateAtmosphericTransmission;
    _summary = format [
        "100=%1 1000=%2 5000=%3 diffScale=%4",
        _near,
        _anchor1000,
        _far,
        round ((_diffA / ((_tTarget0 - _tBack0) max 1e-12)) * 1000) / 1000
    ];
};

if (_fail == 0) then {
    diag_log text format ["[P70] [PASS] atmospheric transmission: %1 checks, %2", _pass, _summary];
} else {
    diag_log text format ["[P70] [FAIL] atmospheric transmission: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
