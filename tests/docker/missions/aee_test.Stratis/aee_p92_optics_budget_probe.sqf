// PHASE 92: the optics per-tick budget and the eye-aperture day anchor.
//
// The client per-frame handler exits at hasInterface on a dedicated server,
// so the loop itself cannot run here.  This probe measures the pure optics
// kernels the loop drives, warm-up plus best of three, and asserts the
// eye-aperture day anchor that fixes the daytime blowout.  The BI wiki
// setAperture Namikaze calibration is 50 = daylight outdoor, below 20 = a
// very bright scene; a value close to 0 pins a near-maximum light intake and
// over-exposes a daylit scene (the operator's normal-vision blowout).

private _aperture = missionNamespace getVariable ["aee_eye_fnc_eyeAperture", nil];
private _compose = missionNamespace getVariable ["aee_vision_fnc_perceptionParams", nil];
private _pass = 0;
private _fail = 0;
private _notes = [];

if (isNil "_aperture" || isNil "_compose") then {
    _fail = _fail + 1;
    _notes pushBack "optics kernels not compiled";
} else {
    // 1. The day anchor is a daylight value and is NARROWER (higher) than the
    //    wide night anchor.  A regression to the old 0.2 day anchor fails.
    private _dayAperture = [100000] call _aperture;
    private _nightAperture = [0.001] call _aperture;
    if ((_dayAperture > 20) && (_dayAperture > _nightAperture)) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["day aperture %1 night %2", _dayAperture, _nightAperture];
    };

    // 2. The night ambient comes from the physical sky, not the engine.  The
    //    engine ambient brightness is an indoor-scale render artifact at night
    //    (~51 lx) and must not override the real night sky (~0.25 lx moonlit).
    private _ambientKernel = missionNamespace getVariable ["aee_eye_fnc_eyeAmbientLux", nil];
    if (isNil "_ambientKernel") then {
        _fail = _fail + 1;
        _notes pushBack "eyeAmbientLux kernel not compiled";
    } else {
        private _nightAmbient = [0.25, 51, 1, -10] call _ambientKernel;
        private _dayAmbient = [0.001, 84987, 1, 30] call _ambientKernel;
        if ((_nightAmbient < 0.5) && (_dayAmbient > 80000)) then {
            _pass = _pass + 1;
        } else {
            _fail = _fail + 1;
            _notes pushBack format ["night %1 day %2", _nightAmbient, _dayAmbient];
        };
    };

    // 3. Per-tick budget: warm-up then best of three.  Ten iterations of the
    //    two pure kernels the optics tick composes (20 calls).  The budget is
    //    generous: it exists to catch an accidental per-call engine read or a
    //    kernel rebuild, not to benchmark the CPU.
    private _work = {
        for "_i" from 1 to 10 do {
            [100000] call _aperture;
            [100, 1, [1, 1, 1], true, false, 0.25, 1, 0.9, 0, 0, [1, 1, 0], 0] call _compose;
        };
    };
    [] call _work;   // warm-up
    private _best = 1e9;
    for "_r" from 1 to 3 do {
        private _t0 = diag_tickTime;
        [] call _work;
        private _ms = (diag_tickTime - _t0) * 1000;
        if (_ms < _best) then { _best = _ms; };
    };
    if (_best < 50) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["budget %1 ms for 20 kernel calls", _best];
    };
};

if (_fail isEqualTo 0) then {
    diag_log text format ["[P92] [PASS] optics budget: day aperture anchor and per-tick kernel budget (%1 checks)", _pass];
} else {
    diag_log text format ["[P92] [FAIL] optics budget: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
