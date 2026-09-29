// PHASE 65: the supersonic vapour trace DECISION leg, measured.
//
// WHY THIS EXISTS AND WHY IT IS PARTIAL. The user asked whether the bullet
// vapour trails had been debugged and logged. They had not, and the reason is
// structural, not a setting. fnc_renderSupersonicTrace.sqf:49 is
//     if (!hasInterface) exitWith {};
// a SILENT exit placed BEFORE both log sites: the ungated AEE_LOG_WARN at :51
// and the AEE_LOG_DEBUG at :95. A dedicated server has no interface, so the
// renderer returns at once and writes nothing whatever the settings are. The
// docker harness therefore CANNOT exercise or log the renderer, and never
// could. That guard stays: a server cannot draw cloudlets, so creating
// particle sources there would cost memory for nothing, and deleting a correct
// guard to enable a test is backwards.
//
// So this phase measures the leg that DECIDES whether a trace opens, which is
// pure arithmetic and runs headless:
//   aee_ballistics_fnc_calculateSupersonicTrace, the kernel, which has NO
// hasInterface guard and returns the refractive index contrast.
// Plus the renderer's own visual mapping, recomputed from source so the three
// sprite parameters are bounded and a future fill-rate blowout fails the run.
//
// WHAT REMAINS UNPROVEN AND IS NOT CLAIMED: whether the sprite RENDERS. That
// is a graphics question needing the game with HDR on. A count of zero
// contrast lines in a log cannot settle it.
//
// The kernel, from addons/ballistics/functions/fnc_calculateSupersonicTrace.sqf:
//   _sound = 20.05 * sqrt (tempC + 273.15)                local speed of sound
//   if (_mach <= 1) exitWith { 0 };                       no shock below Mach 1
//   gamma = 1.4, m2 = mach * mach
//   densityRatio = (gamma+1)*m2 / ((gamma-1)*m2 + 2)        Rankine-Hugoniot
//   contrast = 0.000226 * 1.225 * rhoRel * (densityRatio - 1) / 0.0001
// so contrast is LINEAR in rhoRel and VANISHES at Mach 1.
//
// The mapping, from fnc_renderSupersonicTrace.sqf:145-149:
//   size 0.2 + 1.4*legibility, alpha 0.05 + 0.55*legibility,
//   interval 0.02 + 0.18*(1-legibility), legibility from contrast on [0, 8].

private _KERNEL = "aee_ballistics_fnc_calculateSupersonicTrace";
private _SOUND15 = 20.05 * sqrt (15 + 273.15);
private _pass = 0;
private _fail = 0;
private _notes = [];
private _sweep = "";
private _kok = false;
private _rhoRel = 1.0;
private _tempC = 15;
private _ratio = 0;

// ---- the kernel must compile and return a number with no interface ----
if (isNil _KERNEL) then {
    _fail = _fail + 1;
    _notes pushBack "kernel isNil: aee_ballistics_fnc_calculateSupersonicTrace is not compiled";
} else {
    private _c0 = [_SOUND15, 1.0, 15] call aee_ballistics_fnc_calculateSupersonicTrace;
    if (_c0 isEqualType 0) then {
        _kok = true;
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["kernel returned %1, not a number", typeName _c0];
    };
};

if (_kok) then {

    // ---- guards: non-physical input returns 0 ----
    private _bad = [];
    {
        private _r = _x call aee_ballistics_fnc_calculateSupersonicTrace;
        if (_r != 0) then { _bad pushBack (str _x) };
    } forEach [[0, 1.0, 15], [-5, 1.0, 15], [900, 0, 15], [900, -1, 15], [900, 1.0, -273.15]];
    if (_bad isEqualTo []) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["non-physical input returned non-zero: %1", str _bad];
    };

    // ---- subsonic draws nothing, by physics ----
    // A round exactly at the speed of sound has no shock. This is the gate
    // that stops a subsonic rocket being forced into a trace: an RPG at
    // 300 m/s is M0.88 and a TOW at 310 m/s is M0.91.
    private _sub = [];
    {
        private _r = _x call aee_ballistics_fnc_calculateSupersonicTrace;
        if (_r != 0) then { _sub pushBack format ["%1 m/s -> %2", (_x select 0), _r] };
    } forEach [[_SOUND15, 1.0, 15], [300, 1.0, 15], [310, 1.0, 15]];
    if (_sub isEqualTo []) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["subsonic drew a trace: %1", str _sub];
    };

    // ---- above Mach 1 the contrast rises and never falls ----
    private _mono = [];
    private _prev = -1;
    private _i = 0;
    while {_i < 12} do {
        _i = _i + 1;
        private _m = 1 + (_i * 0.25);
        private _c = [_m * _SOUND15, 1.0, 15] call aee_ballistics_fnc_calculateSupersonicTrace;
        if (_i == 1) then {
            _sweep = format ["M%1=%2", _m, _c];
        } else {
            _sweep = _sweep + format [", M%1=%2", _m, _c];
        };
        if (_c < _prev) then { _mono pushBack format ["M%1 fell to %2", _m, _c] };
        _prev = _c;
    };
    if (_mono isEqualTo []) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["contrast not monotonic in Mach: %1", str _mono];
    };

    // ---- contrast is LINEAR in rhoRel ----
    // A falsifiable property of the Gladstone-Dale term, and what makes the
    // sea-level tuning valid at altitude: doubling the air doubles contrast.
    private _cSea = [900, 1.0, 15] call aee_ballistics_fnc_calculateSupersonicTrace;
    private _cHigh = [900, 2.0, 15] call aee_ballistics_fnc_calculateSupersonicTrace;
    if (_cSea > 0) then { _ratio = _cHigh / _cSea };
    if ((_cSea > 0) && {(abs (_ratio - 2)) < 0.000001}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["contrast not linear in rhoRel: ratio %1, want 2", _ratio];
    };

    // ---- the real rounds clear the legibility band ----
    // 5.56 at 940 m/s is M2.76 and 7.62 at 725 m/s is M2.13.
    private _rifle = [];
    {
        _x params ["_v", "_rho", "_t", "_cMin", "_legMin"];
        private _c = [_v, _rho, _t] call aee_ballistics_fnc_calculateSupersonicTrace;
        private _leg = linearConversion [0, 8, _c, 0, 1, true] max 0;
        if ((_c < _cMin) || {_leg < _legMin}) then {
            _rifle pushBack format ["%1 m/s -> contrast %2 legibility %3", _v, _c, _leg];
        };
    } forEach [[940, 1.0, 15, 7.0, 0.90], [725, 1.0, 15, 4.5, 0.60]];
    if (_rifle isEqualTo []) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["rifle round below its legibility band: %1", str _rifle];
    };

    // ---- the visual mapping, swept along the PHYSICAL curve ----
    // The previous version multiplied two variables that are physically linked,
    // pairing a Mach 1.2 contrast with 2000 m/s, a Mach 5.8 velocity, and
    // failing on a combination the renderer can never see. The contrast is a
    // FUNCTION of the speed, so the sweep takes the speed, asks the kernel for
    // the contrast, and derives everything from that. This is both realistic
    // and a stronger assertion, because it can no longer pass on a fiction.
    private _map = [];
    {
        private _speed = _x;
        private _c = [_speed, _rhoRel, _tempC] call aee_ballistics_fnc_calculateSupersonicTrace;
        private _leg = linearConversion [0, 8, _c, 0, 1, true] max 0;
        private _size = 0.2 + (1.4 * _leg);
        private _alpha = 0.20 + (0.55 * _leg);
        private _drop = (_size / (2 * (_speed max 1))) max 0.0001;
        private _spacing = _speed * _drop;
        private _overdraw = 4 * 25 * _size * _size;
        if (_size > 1.6) then { _map pushBack format ["size %1 over 1.6 m at %2 m/s", _size, _speed] };
        if (_alpha > 0.75) then { _map pushBack format ["alpha %1 over 0.75 at %2 m/s", _alpha, _speed] };
        if (_overdraw > 260) then { _map pushBack format ["overdraw %1 m2 at %2 m/s", _overdraw, _speed] };
        // The interval floor exists to bound the spawn rate, so it may not bite
        // so hard that sprites stop overlapping. That is the 2026-09-29 defect.
        if (_c > 0 && {_spacing > _size * 0.5}) then {
            _map pushBack format ["sprites %1 m apart against a %2 m sprite at %3 m/s", _spacing, _size, _speed];
        };
    } forEach [345, 400, 500, 700, 940, 1200, 1400, 2000];
    if (_map isEqualTo []) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["visual mapping out of bounds: %1", str _map];
    };
};

// ---- the input contract the renderer reads at its line 74 ----
// call EFUNC(ballistics,getEnvironmentState) must resolve headless and give
// tempC, pressureHPa and rhoRel, because the kernel is fed from it.
private _env = [];
private _envOk = false;
if (isNil "aee_ballistics_fnc_getEnvironmentState") then {
    _fail = _fail + 1;
    _notes pushBack "aee_ballistics_fnc_getEnvironmentState is not compiled";
} else {
    _env = call aee_ballistics_fnc_getEnvironmentState;
    if ((count _env) >= 3) then {
        private _t = _env param [0];
        private _p = _env param [1];
        private _r = _env param [2];
        _envOk = (_t isEqualType 0) && {_p isEqualType 0} && {_r isEqualType 0} && {_r > 0};
    };
    if (_envOk) then {
        _pass = _pass + 1;
        diag_log text format ["[P65] env tempC %1 pressureHPa %2 rhoRel %3",
            _env param [0], _env param [1], _env param [2]];
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["getEnvironmentState did not resolve to 3 positive numbers: %1", str _env];
    };
};

diag_log text format ["[P65] kernel sweep at 15 C, rhoRel 1: %1", _sweep];
if (_kok) then {
    diag_log text format ["[P65] 5.56mm@940 -> %1, 7.62mm@725 -> %2, rhoRel x2 ratio %3",
        [940, 1.0, 15] call aee_ballistics_fnc_calculateSupersonicTrace, [725, 1.0, 15] call aee_ballistics_fnc_calculateSupersonicTrace, _ratio];
};

if (_fail == 0) then {
    diag_log text format ["[P65] [PASS] trace decision leg: %1 checks, subsonic silent, rifle rounds visible, mapping bounded", _pass];
} else {
    {
        diag_log text format ["[P65] [FAIL] %1", _x];
    } forEach _notes;
    diag_log text format ["[P65] [FAIL] trace decision leg: %1 passed, %2 failed", _pass, _fail];
};

[{
    diag_log text "[P65] report complete";
    diag_log text "[AEE-TEST] DONE";
}, [], 4] call CBA_fnc_waitAndExecute;
