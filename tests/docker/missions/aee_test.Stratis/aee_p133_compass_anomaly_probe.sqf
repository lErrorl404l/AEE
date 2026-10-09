// PHASE 133: the maritime compass anomaly scale, headless.
//
// fnc_calculateMagneticAnomaly computes a dipole flux density but omitted the
// vacuum permeability mu0 = 4pi*1e-7, so it returned the magnetic field
// strength H (A/m) rather than the flux density B (tesla): about 795775x too
// large.  The operator RPT of 2026-10-08 logged anomaly 8.22e7 nT (roughly
// 1700x Earth's 50000 nT field) and pinned the compass deviation at the +10
// deg clamp (dev=12.57 for most of the run).  This probe drives the REAL
// kernel and asserts a physically bounded flux density with an ordinary ground
// vehicle at 50 m.  It renders nothing.
//
// Emits [P133] PASS/FAIL lines.

private _fnMag = missionNamespace getVariable ["aee_magnetism_fnc_calculateMagneticAnomaly", nil];
if (isNil "_fnMag") exitWith {
    diag_log text "[P133] [FAIL] magnetic anomaly function not compiled";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// 1. A vehicle-scale dipole (1000 A m^2) 50 m away, on axis: B = mu0/4pi *
//    M/r^3 * 2 = 1e-7 * 1000/125000 * 2 * 1e9 = 1.6 nT.  Bounded, not 8.22e7.
private _b = [[0, 0, 50], [0, 0, 0], 1000] call _fnMag;
private _expected = (1e-7 * 1000 / (50 * 50 * 50)) * 2 * 1e9;
if ((abs (_b - _expected) < 1e-3) && {_b < 100}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["50 m vehicle = %1 nT (expected %2)", _b, _expected];
};

// 2. The unit error is the missing mu0: the pre-fix formula is 1/(4pi*1e-7)
//    = 795775x the corrected value.  Prove the kernel no longer carries it.
private _wrong = (1000 / (4 * pi * 125000)) * 2 * 1e9;
private _ratio = _wrong / _b;
if (abs (_ratio - 1 / (4 * pi * 1e-7)) < 1) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["scale ratio %1", _ratio];
};

// 3. The deviation from a 50 m vehicle never reaches the 10 deg clamp.
//    deviation = anomaly/50000 * 57.2957795.
private _devDeg = (_b / 50000) * 57.2957795;
if (abs (_devDeg) < 1) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["50 m deviation %1 deg", _devDeg];
};

// 4. The 1/r^3 falloff holds (doubling distance -> 1/8 field).
private _b2 = [[0, 0, 100], [0, 0, 0], 1000] call _fnMag;
if (abs (_b2 - _b / 8) < 1e-4) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["100 m = %1 nT (expected %2)", _b2, _b / 8];
};

diag_log text format ["[P133] compass anomaly: 50m=%1 nT expected=%2 dev=%3 deg 100m=%4 nT ratio=%5",
    _b, _expected, _devDeg, _b2, _ratio];

if (_fail == 0) then {
    diag_log text format ["[P133] [PASS] compass anomaly scale: bounded flux density (%1 checks)", _pass];
} else {
    diag_log text format ["[P133] [FAIL] compass anomaly scale: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
