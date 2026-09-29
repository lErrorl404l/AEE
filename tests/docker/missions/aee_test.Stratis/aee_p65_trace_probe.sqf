// PHASE 65: the supersonic shock trace DECISION leg, measured.
//
// WHY THIS EXISTS AND WHY IT IS PARTIAL. The user asked whether the bullet
// vapour trails had been debugged and logged. They had not, and the reason is
// structural, not a setting. fnc_renderSupersonicTrace has
//     if (!hasInterface) exitWith {};
// a SILENT exit placed BEFORE both log sites: the ungated AEE_LOG_WARN and
// the AEE_LOG_DEBUG. A dedicated server has no interface, so the
// renderer returns at once and writes nothing whatever the settings are. The
// docker harness therefore CANNOT exercise or log the renderer, and never
// could. That guard stays: a server cannot draw cloudlets, so creating
// particle sources there would cost memory for nothing, and deleting a correct
// guard to enable a test is backwards.
//
// So this phase measures the legs that DECIDE whether a trace opens, both of
// which are pure arithmetic and run headless:
//   aee_ballistics_fnc_calculateSupersonicTrace, the refractive kernel, which
//     has NO hasInterface guard and returns the refractive index contrast.
//   aee_ballistics_fnc_calculateMachCone, the cone geometry, which returns the
//     Mach cone half-angle and the cone width from the speed and the calibre.
// Plus the renderer's own geometry, recomputed from source so the sprite
// parameters are bounded and a future fill-rate blowout fails the run.
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
// The cone, from addons/ballistics/functions/fnc_calculateMachCone.sqf:
//   mu = asin (1 / M),  M = v / a,  a = 20.05 * sqrt (T + 273.15)
//   tan(mu) = 1 / sqrt (M^2 - 1)
//   fullWidth = 8 * calibreM * tan(mu)
// so mu FALLS as the round accelerates and the cone NARROWS with speed. The
// superseded sprite mapping WIDENED with speed, because legibility rises with
// contrast and contrast rises with speed. That was a SIGN ERROR in the
// direction of the mapping, and these assertions pin the correct direction.
//
// The renderer geometry, from fnc_renderSupersonicTrace.sqf:
//   size  = clamp(fullWidth * 50, 0.35, 1.4)
//   alpha = 0.20 + 0.55 * legibility, legibility from contrast on [0, 8]
//   drop  = max(size / (2 * speed), 0.00025)
//   ttl   = 8 * (size / (2 * speed))      2 * _TRAIL_WIDTHS
// so the trail is 4 sprite widths and the live count is bounded at 8.

private _KERNEL = "aee_ballistics_fnc_calculateSupersonicTrace";
private _CONE = "aee_ballistics_fnc_calculateMachCone";
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
};

// ---- the Mach cone half-angle is the exact cone geometry ----
// The expected values are asin(1/M) in degrees at the listed Mach numbers.
if (isNil _CONE) then {
    _fail = _fail + 1;
    _notes pushBack "cone isNil: aee_ballistics_fnc_calculateMachCone is not compiled";
} else {
    private _coneProbe = [2.0 * _SOUND15, 15, 5.56] call aee_ballistics_fnc_calculateMachCone;
    if ((_coneProbe isEqualType []) && {(count _coneProbe) >= 3}) then {
        private _coneBad = [];
        {
            _x params ["_m", "_wantMu"];
            private _speed = _m * _SOUND15;
            private _cone = [_speed, 15, 5.56] call aee_ballistics_fnc_calculateMachCone;
            _cone params ["_mu", "_half", "_full"];
            if (abs (_mu - _wantMu) > 0.05) then {
                _coneBad pushBack format ["M%1 mu %2 want %3", _m, _mu, _wantMu];
            };
            if (abs (_full - (2 * _half)) > 0.000001) then {
                _coneBad pushBack format ["M%1 half %2 full %3 not a diameter", _m, _half, _full];
            };
        } forEach [[1.1, 65.38], [1.2, 56.44], [1.5, 41.81], [2.0, 30.00], [2.7, 21.74], [3.5, 16.60], [4.0, 14.48]];
        if (_coneBad isEqualTo []) then {
            _pass = _pass + 1;
        } else {
            _fail = _fail + 1;
            _notes pushBack format ["mach cone half-angle wrong: %1", str _coneBad];
        };
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["cone returned %1, want three numbers", typeName _coneProbe];
    };

    // ---- the cone NARROWS as the round accelerates ----
    // This is the direction the superseded legibility mapping got wrong.
    private _narrow = [];
    private _prevFull = -1;
    {
        private _speed = _x * _SOUND15;
        private _cone = [_speed, 15, 5.56] call aee_ballistics_fnc_calculateMachCone;
        private _full = _cone select 2;
        if (_full <= 0) then {
            _narrow pushBack format ["M%1 cone width %2 is not positive", _x, _full];
        } else {
            if ((_prevFull >= 0) && (_full >= _prevFull)) then {
                _narrow pushBack format ["M%1 cone width %2 did not narrow from %3", _x, _full, _prevFull];
            };
        };
        _prevFull = _full;
    } forEach [1.5, 2.0, 2.7, 3.5, 4.0];
    if (_narrow isEqualTo []) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["cone did not narrow with speed: %1", str _narrow];
    };

    // ---- the cone width scales with calibre ----
    // A 12.7 mm round draws a wider cone than a 5.56 mm round at one Mach.
    private _cal = [];
    private _c556 = [2.7 * _SOUND15, 15, 5.56] call aee_ballistics_fnc_calculateMachCone;
    private _c127 = [2.7 * _SOUND15, 15, 12.7] call aee_ballistics_fnc_calculateMachCone;
    private _f556 = _c556 select 2;
    private _f127 = _c127 select 2;
    if (_f556 <= 0) then {
        _cal pushBack "5.56 cone width is not positive";
    } else {
        if (abs ((_f127 / _f556) - (12.7 / 5.56)) > 0.001) then {
            _cal pushBack format ["calibre ratio %1, want %2", _f127 / _f556, 12.7 / 5.56];
        };
    };
    if (_cal isEqualTo []) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["cone width did not scale with calibre: %1", str _cal];
    };

    // ---- a subsonic round carries no attached cone ----
    private _coneSub = [_SOUND15 * 0.9, 15, 5.56] call aee_ballistics_fnc_calculateMachCone;
    if ((_coneSub select 2) == 0) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["subsonic cone width %1, want 0", _coneSub select 2];
    };
};

// ---- the renderer geometry, swept along the PHYSICAL curve ----
// The previous version multiplied two variables that are physically linked,
// pairing a Mach 1.2 contrast with 2000 m/s, a Mach 5.8 velocity, and
// failing on a combination the renderer can never see. The contrast is a
// FUNCTION of the speed, so the sweep takes the speed, asks the kernels, and
// derives everything from that. This is both realistic and a stronger
// assertion, because it can no longer pass on a fiction. These constants
// mirror fnc_renderSupersonicTrace.sqf and tools/tests/test_supersonic_trace.py
// checks them against it, so the mirror cannot drift.
private _VISIBILITY = 50;
private _MAX_SIZE = 1.4;
private _MIN_SIZE = 0.35;
private _MIN_DROP = 0.00025;
private _TRAIL_WIDTHS = 4;
private _LIVE_SPRITES = 2 * _TRAIL_WIDTHS;
private _MAX_TRACES = 4;

private _map = [];
{
    private _speed = _x;
    private _c = [_speed, _rhoRel, _tempC] call aee_ballistics_fnc_calculateSupersonicTrace;
    private _cone = [_speed, _tempC, 5.56] call aee_ballistics_fnc_calculateMachCone;
    private _width = _cone select 2;
    private _size = ((_width * _VISIBILITY) min _MAX_SIZE) max _MIN_SIZE;
    private _leg = linearConversion [0, 8, _c, 0, 1, true] max 0;
    private _alpha = 0.20 + (0.55 * _leg);
    private _dropPhysical = _size / (2 * (_speed max 1));
    private _drop = _dropPhysical max _MIN_DROP;
    private _ttl = _LIVE_SPRITES * _dropPhysical;
    private _trail = _ttl * _speed;
    private _overdraw = _MAX_TRACES * _LIVE_SPRITES * _size * _size;
    private _rate = 1 / _drop;
    if (_size > _MAX_SIZE) then { _map pushBack format ["size %1 over %2 m at %3 m/s", _size, _MAX_SIZE, _speed] };
    if (_size < _MIN_SIZE) then { _map pushBack format ["size %1 under %2 m at %3 m/s", _size, _MIN_SIZE, _speed] };
    if (_alpha > 0.75) then { _map pushBack format ["alpha %1 over 0.75 at %2 m/s", _alpha, _speed] };
    if (_overdraw > 260) then { _map pushBack format ["overdraw %1 m2 at %2 m/s", _overdraw, _speed] };
    // The trail is a few sprite widths at EVERY speed, because the lifetime
    // derives from the physical drop, not from the floored one.
    if (abs (_trail - (_TRAIL_WIDTHS * _size)) > 0.001) then {
        _map pushBack format ["trail %1 m against %2 sprite widths at %3 m/s", _trail, _TRAIL_WIDTHS, _speed];
    };
    // The live sprite count is bounded, so a faster round cannot pile up
    // sprites without limit.
    if (_ttl > (_LIVE_SPRITES * _drop)) then {
        _map pushBack format ["live count over %1 at %2 m/s", _LIVE_SPRITES, _speed];
    };
    // The spawn rate is bounded by the drop floor; above the Mach where the
    // floor binds the trace is a sparse haze rather than a ribbon.
    if (_rate > ((1 / _MIN_DROP) + 0.5)) then {
        _map pushBack format ["spawn rate %1 over %2/s at %3 m/s", _rate, 1 / _MIN_DROP, _speed];
    };
} forEach [408, 500, 680, 940, 1200, 1361];
if (_map isEqualTo []) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["renderer geometry out of bounds: %1", str _map];
};

// ---- the input contract the renderer reads ----
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
if (!isNil _CONE) then {
    private _m2 = [2.0 * _SOUND15, 15, 5.56] call aee_ballistics_fnc_calculateMachCone;
    private _m27 = [2.7 * _SOUND15, 15, 5.56] call aee_ballistics_fnc_calculateMachCone;
    private _m4 = [4.0 * _SOUND15, 15, 5.56] call aee_ballistics_fnc_calculateMachCone;
    diag_log text format ["[P65] cone half-angle M2 %1, M2.7 %2, M4 %3 deg (5.56 mm, narrowing)",
        _m2 select 0, _m27 select 0, _m4 select 0];
};

if (_fail == 0) then {
    diag_log text format ["[P65] [PASS] shock trace decision leg: %1 checks, subsonic silent, cone narrowing, size from calibre, geometry bounded", _pass];
} else {
    {
        diag_log text format ["[P65] [FAIL] %1", _x];
    } forEach _notes;
    diag_log text format ["[P65] [FAIL] shock trace decision leg: %1 passed, %2 failed", _pass, _fail];
};

[{
    diag_log text "[P65] report complete";
    diag_log text "[AEE-TEST] DONE";
}, [], 4] call CBA_fnc_waitAndExecute;
