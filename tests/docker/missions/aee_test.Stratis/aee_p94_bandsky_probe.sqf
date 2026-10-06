// PHASE 94: the band sky temperature, headless (aee-thermal-realism T18).
//
// WHY THIS EXISTS.  The band sky kernel replaces the retired fixed -35 K
// offset with a model that follows air temperature, humidity and overcast.
// Water vapour fills the 8-14 um window, so a more humid sky is warmer.  The
// kernel is pure, so a dedicated server calls it directly.  It renders
// nothing.
//
// The probe asserts ORDER, not absolute values: the model is a declared
// ladder, so the monotone response in humidity is the checkable contract.
//
// Emits: [P94] [PASS] / [P94] [FAIL] <reason>.

private _KERNEL = "aee_thermal_fnc_calculateSkyRadiance";
private _pass = 0;
private _fail = 0;
private _notes = [];

if (isNil _KERNEL) then {
    _fail = _fail + 1;
    _notes pushBack "band sky kernel is not compiled";
} else {
    private _humidities = [5, 20, 40, 60, 80, 95];

    // 1. The LWIR band sky is monotone in humidity at fixed air temperature.
    private _lwirMono = true;
    private _lwirVals = [];
    private _prev = -1e9;
    {
        private _t = ["lwir", 15, _x, 0] call aee_thermal_fnc_calculateSkyRadiance;
        _lwirVals pushBack _t;
        if (!(finite _t) || {_t < _prev}) then { _lwirMono = false; };
        _prev = _t;
    } forEach _humidities;
    if (_lwirMono) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["lwir not monotone: %1", str _lwirVals];
    };

    // 2. The MWIR band sky is monotone too.
    private _mwirMono = true;
    private _mwirVals = [];
    _prev = -1e9;
    {
        private _t = ["mwir", 15, _x, 0] call aee_thermal_fnc_calculateSkyRadiance;
        _mwirVals pushBack _t;
        if (!(finite _t) || {_t < _prev}) then { _mwirMono = false; };
        _prev = _t;
    } forEach _humidities;
    if (_mwirMono) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["mwir not monotone: %1", str _mwirVals];
    };

    // 3. A clear dry sky is colder than the air; a full overcast removes the
    //    depression and warms the sky toward the air.
    private _clearDry = ["lwir", 15, 5, 0] call aee_thermal_fnc_calculateSkyRadiance;
    private _fullCloud = ["lwir", 15, 5, 1] call aee_thermal_fnc_calculateSkyRadiance;
    if ((finite _clearDry) && {_clearDry < 15} && {finite _fullCloud} && {_fullCloud > _clearDry}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["clear %1 overcast %2", _clearDry, _fullCloud];
    };

    _notes pushBack format ["lwir95=%1 mwir95=%2", _lwirVals select -1, _mwirVals select -1];
};

if (_fail == 0) then {
    diag_log text format ["[P94] [PASS] band sky: %1 checks, %2", _pass, _notes];
} else {
    diag_log text format ["[P94] [FAIL] band sky: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
