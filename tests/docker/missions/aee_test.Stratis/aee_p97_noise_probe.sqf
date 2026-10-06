// PHASE 97: the thermal noise floor, headless (aee-thermal-realism T18).
//
// WHY THIS EXISTS.  The noise kernel replaced the engine `viewDistance`
// proxy with a real sensor-to-target range supplied by the caller.  The
// noise grows as range squared, carries a detector-resolution factor and a
// humidity term, and clamps to 0..1.  The kernel is pure, so a dedicated
// server calls it directly.  It renders nothing.
//
// Emits: [P97] [PASS] / [P97] [FAIL] <reason>.

private _KERNEL = "aee_thermal_fnc_calculateThermalNoise";
private _pass = 0;
private _fail = 0;
private _notes = [];

if (isNil _KERNEL) then {
    _fail = _fail + 1;
    _notes pushBack "noise kernel is not compiled";
} else {
    private _ranges = [100, 300, 900, 2700];

    // 1. The noise rises strictly with range for a fixed device.
    private _mono = true;
    private _prev = -1e9;
    private _vals = [];
    {
        private _n = [0.05, _x, 640, 50] call aee_thermal_fnc_calculateThermalNoise;
        _vals pushBack _n;
        if (!(finite _n) || {_n <= _prev}) then { _mono = false; };
        _prev = _n;
    } forEach _ranges;
    if (_mono) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["not monotone in range: %1", str _vals];
    };

    // 2. Humidity raises the noise at a fixed range.
    private _dry = [0.05, 900, 640, 0] call aee_thermal_fnc_calculateThermalNoise;
    private _wet = [0.05, 900, 640, 100] call aee_thermal_fnc_calculateThermalNoise;
    if ((finite _dry) && {finite _wet} && {_wet > _dry}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["humidity dry %1 wet %2", _dry, _wet];
    };

    // 3. The result is clamped to 1 at an extreme range.
    private _far = [0.05, 100000, 640, 50] call aee_thermal_fnc_calculateThermalNoise;
    if ((finite _far) && {abs (_far - 1) < 1e-9}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["far gave %1, want 1", _far];
    };

    // 4. A higher-resolution detector has less spatial noise.
    private _lowRes = [0.05, 900, 320, 50] call aee_thermal_fnc_calculateThermalNoise;
    private _highRes = [0.05, 900, 1280, 50] call aee_thermal_fnc_calculateThermalNoise;
    if ((finite _lowRes) && {finite _highRes} && {_lowRes > _highRes}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["resolution 320 %1 1280 %2", _lowRes, _highRes];
    };

    _notes pushBack format ["noise2700=%1", _vals select -1];
};

if (_fail == 0) then {
    diag_log text format ["[P97] [PASS] thermal noise: %1 checks, %2", _pass, _notes];
} else {
    diag_log text format ["[P97] [FAIL] thermal noise: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
