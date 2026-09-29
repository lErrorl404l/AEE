// PHASE 68: the thermal edge kernel, measured.
//
// WHY THIS EXISTS.  The kernel aee_thermal_fnc_evaluateThermalEdge is PURE
// ARITHMETIC over scalars, so a dedicated server can call it directly.  It
// decides a thermal EDGE from a selection's band radiance and a LOCAL
// background radiance, with no scene window and no renderer.
//
// The inputs are physically reachable.  The local background is the band
// radiance of one selection at -5 C; the signal is the band radiance of
// another selection in the SAME air, swept from -40 C to +60 C.  The probe
// sweeps ONE variable, the signal temperature.  It does NOT sweep a
// cartesian product of linked inputs, because that invents pairs the real
// path can never produce.

private _KERNEL = "aee_thermal_fnc_evaluateThermalEdge";
private _CALC = "aee_thermal_fnc_calculateBandRadiance";
private _pass = 0;
private _fail = 0;
private _notes = [];
private _summary = "";

if (isNil _KERNEL || isNil _CALC) then {
    _fail = _fail + 1;
    _notes pushBack "kernel isNil: the edge kernel or the radiance kernel is not compiled";
    _summary = "kernel not compiled";
} else {
    private _tAir = 15;
    private _eps = 0.95;
    private _fGround = 0.5;
    private _tGround = 15;
    private _tBg = -5;
    private _bg = [_tBg, _eps, _tAir, _fGround, _tGround] call aee_thermal_fnc_calculateBandRadiance;
    _summary = format ["bg=%1 at %2 C", _bg, _tBg];

    // 1. The kernel compiles and returns a two-element array.
    private _shape = [_bg, _bg] call aee_thermal_fnc_evaluateThermalEdge;
    if ((_shape isEqualType []) && ((count _shape) == 2)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["kernel returned %1, want a two-element array", typeName _shape];
    };

    // 2. A signal at its local background is background, not an edge.
    private _atBg = [_bg, _bg] call aee_thermal_fnc_evaluateThermalEdge;
    if ((!(_atBg select 0)) && (abs ((_atBg select 1) - 0) < 1e-9)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["at the background gave decision=%1 contrast=%2, want false and 0", _atBg select 0, _atBg select 1];
    };

    // 3. A clearly hotter signal is an edge.
    private _hot = [40, _eps, _tAir, _fGround, _tGround] call aee_thermal_fnc_calculateBandRadiance;
    private _above = [_hot, _bg] call aee_thermal_fnc_evaluateThermalEdge;
    if ((_above select 0) && ((_above select 1) > 0)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["a hot signal gave decision=%1 contrast=%2, want an edge", _above select 0, _above select 1];
    };

    // 4. A colder signal is below its background, not an edge, clamped at 0.
    private _cold = [-30, _eps, _tAir, _fGround, _tGround] call aee_thermal_fnc_calculateBandRadiance;
    private _below = [_cold, _bg] call aee_thermal_fnc_evaluateThermalEdge;
    if ((!(_below select 0)) && (abs ((_below select 1) - 0) < 1e-9)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["a below-background signal gave decision=%1 contrast=%2, want false and the 0 clamp", _below select 0, _below select 1];
    };

    // 5. A single-variable sweep of the signal temperature.  The contrast is
    // non-decreasing and the decision flips from false to true once and
    // stays true.  A single sweep, not a product of linked inputs.
    private _seenEdge = false;
    private _monotonic = true;
    private _lastContrast = -1;
    private _flips = 0;
    for "_t" from -40 to 60 step 5 do {
        private _rad = [_t, _eps, _tAir, _fGround, _tGround] call aee_thermal_fnc_calculateBandRadiance;
        private _d = [_rad, _bg] call aee_thermal_fnc_evaluateThermalEdge;
        private _c = _d select 1;
        if (_c < _lastContrast) then { _monotonic = false; };
        _lastContrast = _c;
        if ((_d select 0) && !(_seenEdge)) then { _flips = _flips + 1; };
        if (_d select 0) then { _seenEdge = true; };
    };
    if (_monotonic && (_flips == 1)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["sweep not monotone single-flip: monotonic=%1 flips=%2", _monotonic, _flips];
    };
};

if (_fail == 0) then {
    diag_log text format ["[P68] [PASS] thermal edge: %1 checks, %2", _pass, _summary];
} else {
    diag_log text format ["[P68] [FAIL] thermal edge: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
