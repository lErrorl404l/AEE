// PHASE 85: the star brightness model, headless (aee-workshop-copy item 3).
//
// The three kernels are pure functions of their arguments, so a dedicated
// server drives them directly.  A fixed mission date is set for the run; the
// model itself is a function of the phase arguments passed below.  The probe
// asserts that light pollution lowers the NELM, that a fuller moon raises the
// brightness coefficient, and that high overcast fades the value.  It renders
// nothing.

setDate [2035, 1, 1, 0, 0];

private _fnNelm = missionNamespace getVariable ["aee_environmental_fnc_calculateLimitingMagnitude", nil];
private _fnCoef = missionNamespace getVariable ["aee_environmental_fnc_starBrightnessCoefficient", nil];
private _fnFade = missionNamespace getVariable ["aee_environmental_fnc_starWeatherFade", nil];

private _pass = 0;
private _fail = 0;
private _notes = [];

if (isNil "_fnNelm" || {isNil "_fnCoef"} || {isNil "_fnFade"}) then {
    diag_log text "[P85] [FAIL] star brightness functions not compiled";
} else {
    // Light pollution: 100 houses must lower the NELM below the 0-house value.
    private _nelm0 = [0.001, 0.1, 0] call _fnNelm;
    private _nelm100 = [0.001, 0.1, 100] call _fnNelm;
    if (_nelm100 < _nelm0) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["nelm houses 0=%1 not above houses 100=%2", _nelm0, _nelm100];
    };

    // Moon phase: the coefficient rises from new (0.0) to half (0.5).
    private _coefNew = [0.0, 0.5, 0] call _fnCoef;
    private _coefHalf = [0.5, 0.5, 0] call _fnCoef;
    if (_coefHalf > _coefNew) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["coef moon 0.0=%1 not below moon 0.5=%2", _coefNew, _coefHalf];
    };

    // Weather: high overcast fades the value to zero.
    private _fadeClear = [10, 0.0, 0.0] call _fnFade;
    private _fadeCloud = [10, 1.0, 0.0] call _fnFade;
    if (_fadeCloud < _fadeClear) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["fade clear=%1 not above overcast 1.0=%2", _fadeClear, _fadeCloud];
    };
};

if ((_fail == 0) && {_pass >= 3}) then {
    diag_log text format ["[P85] [PASS] star brightness model: %1 checks", _pass];
} else {
    diag_log text format ["[P85] [FAIL] star brightness model: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
