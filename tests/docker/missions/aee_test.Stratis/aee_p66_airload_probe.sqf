// PHASE 66: the air-engine-load kernel, measured.
//
// WHY THIS EXISTS.  The exhaust shimmer renderer exits at hasInterface on a
// dedicated server, so its power resolution cannot be exercised headless.  The
// kernel it reaches for an Air class is PURE ARITHMETIC over scalars plus one
// class test, so it IS callable headless, and this probe calls it directly
// with the two reference airframes and asserts both figures.  It does not
// touch the renderer and it does not claim the sprite renders.
//
// Reference airframes, from the kernel header:
//   Piper PA-28-181: mass 1100 kg, rated 134 kW, Cd S = 0.688 m^2, 58 m/s
//     -> 0.5 * 1.225 * 0.688 * 58^3 / 134000 = 0.61
//   Robinson R44: mass 580 kg, rotor disc 81 m^2, rated 131 kW
//     -> 5688^1.5 / sqrt (2 * 1.225 * 81) / 131000 = 0.23

private _KERNEL = "aee_flight_fnc_calculateAirEngineLoad";
private _pass = 0;
private _fail = 0;
private _notes = [];

if (isNil _KERNEL) then {
    _fail = _fail + 1;
    _notes pushBack "kernel isNil: aee_flight_fnc_calculateAirEngineLoad is not compiled";
} else {
    // The kernel compiles and returns a number.
    private _probe = [1100, 58, "B_Plane_CAS_01_F", 134000, 0.688, 50, 0, 1.225] call aee_flight_fnc_calculateAirEngineLoad;
    if (_probe isEqualType 0) then { _pass = _pass + 1; } else {
        _fail = _fail + 1;
        _notes pushBack format ["kernel returned %1, not a number", typeName _probe];
    };

    // PA-28 at 58 m/s against its own 134 kW: 0.61.
    private _pa28 = [1100, 58, "B_Plane_CAS_01_F", 134000, 0.688, 50, 0, 1.225] call aee_flight_fnc_calculateAirEngineLoad;
    if (abs (_pa28 - 0.614) < 0.01) then { _pass = _pass + 1; } else {
        _fail = _fail + 1;
        _notes pushBack format ["PA-28 at 58 m/s gave %1, want about 0.61", _pa28];
    };

    // PA-28 at 58 m/s against the kernel's 150000 W default: 0.55.
    private _pa28d = [1100, 58, "B_Plane_CAS_01_F", 150000, 0.688, 50, 0, 1.225] call aee_flight_fnc_calculateAirEngineLoad;
    if (abs (_pa28d - 0.548) < 0.01) then { _pass = _pass + 1; } else {
        _fail = _fail + 1;
        _notes pushBack format ["PA-28 at 58 m/s on the 150000 W default gave %1, want about 0.55", _pa28d];
    };

    // A parked wing has no drag power, so the idle floor is what remains.
    private _parked = [1100, 0, "B_Plane_CAS_01_F", 150000, 0.688, 50, 0.05, 1.225] call aee_flight_fnc_calculateAirEngineLoad;
    if (abs (_parked - 0.05) < 0.000001) then { _pass = _pass + 1; } else {
        _fail = _fail + 1;
        _notes pushBack format ["a parked wing gave %1, want the 0.05 idle floor", _parked];
    };

    // A fast wing gives a larger fraction than a slow one.
    private _slow = [1100, 30, "B_Plane_CAS_01_F", 150000, 0.688, 50, 0, 1.225] call aee_flight_fnc_calculateAirEngineLoad;
    if (_slow < _pa28d) then { _pass = _pass + 1; } else {
        _fail = _fail + 1;
        _notes pushBack format ["30 m/s gave %1, not under the 58 m/s figure %2", _slow, _pa28d];
    };

    // R44 hovering: 0.23, the ideal induced hover fraction.
    private _r44 = [580, 0, "B_Heli_Light_01_F", 131000, 0.7, 81, 0, 1.225] call aee_flight_fnc_calculateAirEngineLoad;
    if (abs (_r44 - 0.232) < 0.01) then { _pass = _pass + 1; } else {
        _fail = _fail + 1;
        _notes pushBack format ["R44 hover gave %1, want about 0.23", _r44];
    };

    // The rotor term is the hover balance and does not depend on forward
    // speed, which is a stated lower bound rather than a forward-flight model.
    private _r44f = [580, 40, "B_Heli_Light_01_F", 131000, 0.7, 81, 0, 1.225] call aee_flight_fnc_calculateAirEngineLoad;
    if (abs (_r44f - _r44) < 0.000001) then { _pass = _pass + 1; } else {
        _fail = _fail + 1;
        _notes pushBack format ["R44 at 40 m/s gave %1 against the hover %2; the rotor term must be speed-independent", _r44f, _r44];
    };

    // Guards: a non-positive rated power, mass or disc area returns -1.
    private _guards = [];
    {
        private _r = _x call aee_flight_fnc_calculateAirEngineLoad;
        if (_r != -1) then { _guards pushBack format ["%1 -> %2, want -1", str _x, _r] };
    } forEach [
        [1100, 58, "B_Plane_CAS_01_F", 0, 0.688, 50, 0.05, 1.225],
        [0, 58, "B_Plane_CAS_01_F", 134000, 0.688, 50, 0.05, 1.225],
        [580, 0, "B_Heli_Light_01_F", 131000, 0.7, 0, 0.05, 1.225]
    ];
    if (_guards isEqualTo []) then { _pass = _pass + 1; } else {
        _fail = _fail + 1;
        _notes pushBack format ["a guard did not refuse: %1", str _guards];
    };

    // The fraction is clamped to 1: an absurd speed cannot exceed full power.
    private _clamp = [1100, 400, "B_Plane_CAS_01_F", 134000, 0.688, 50, 0, 1.225] call aee_flight_fnc_calculateAirEngineLoad;
    if (_clamp == 1) then { _pass = _pass + 1; } else {
        _fail = _fail + 1;
        _notes pushBack format ["an absurd speed gave %1, want the clamp at 1", _clamp];
    };

    diag_log text format ["[P66] PA-28 58m/s=%1 (134kW) %2 (150kW), parked=%3, 30m/s=%4, R44 hover=%5, R44 40m/s=%6",
        _pa28, _pa28d, _parked, _slow, _r44, _r44f];
};

if (_fail == 0) then {
    diag_log text format ["[P66] [PASS] air engine load: %1 checks, PA-28 0.61/0.55, parked 0.05, R44 0.23", _pass];
} else {
    diag_log text format ["[P66] [FAIL] air engine load: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
