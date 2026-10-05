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
//   cap   = sqrt (190 / (4 * 8)) = 2.44 m   rendering-budget, not physical
//   size  = clamp(fullWidth * _VISIBILITY, 0.35, cap)
//   _VISIBILITY = 15 px at 100 m for the 5.56 mm round at Mach 2.76
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
private _MAX_TRACES = 4;
// The cap is DERIVED from the measured overdraw budget, not chosen, so the
// worst case is the budget exactly: 4 traces * 8 live sprites * cap^2.
private _OVERDRAW_BUDGET_M2 = 190;
private _TRAIL_WIDTHS = 4;
private _LIVE_SPRITES = 2 * _TRAIL_WIDTHS;
private _MAX_SIZE = sqrt (_OVERDRAW_BUDGET_M2 / (_MAX_TRACES * _LIVE_SPRITES));
private _MIN_SIZE = 0.35;
private _MIN_DROP = 0.00025;
// _VISIBILITY is DERIVED from a stated pixel target at a stated reference
// range: the reference 5.56 mm round at Mach 2.76 must subtend at least 15
// pixels at 100 m.  1080p, 60 degree horizontal FOV gives the focal length.
private _FOCAL_LENGTH_PX = 1662.8;
private _TARGET_PX = 15;
private _REF_RANGE_M = 100;
private _REF_MACH = 2.76;
private _REF_CALIBRE_M = 0.00556;
private _REF_CONE_M = (8 * _REF_CALIBRE_M) / sqrt ((_REF_MACH * _REF_MACH) - 1);
private _VISIBILITY = (_TARGET_PX * _REF_RANGE_M) / (_FOCAL_LENGTH_PX * _REF_CONE_M);

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
    if (_overdraw > (_OVERDRAW_BUDGET_M2 + 0.0001)) then { _map pushBack format ["overdraw %1 m2 over the budget at %2 m/s", _overdraw, _speed] };
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

// The cap must be exactly the sqrt of the measured budget over the
// worst-case sprite count, and the reference round must clear the 0.8 m
// regression floor the user confirmed by eye.
if (abs (_MAX_SIZE - sqrt (_OVERDRAW_BUDGET_M2 / (_MAX_TRACES * _LIVE_SPRITES))) > 0.0001) then {
    _map pushBack format ["cap %1 is not the sqrt of the budget over %2 sprites", _MAX_SIZE, _MAX_TRACES * _LIVE_SPRITES];
};
private _refDrawn = (8 * 0.00556 / sqrt ((2.76 * 2.76) - 1)) * _VISIBILITY;
if (_refDrawn < 0.8) then {
    _map pushBack format ["the reference 5.56 mm round draws %1 m, under the 0.8 m regression floor", _refDrawn];
};

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

// ---- exhaust plume power ramp, swept along the physical curve ----
// The renderer exits at hasInterface on a dedicated server, so the sprite
// cannot be observed here.  This measures the decision leg: the pure kernel
// and the area-derived live count, both of which run headless.
private _EXHAUST = "aee_mobility_fnc_calculateExhaustPlume";
if (isNil _EXHAUST) then {
    _fail = _fail + 1;
    _notes pushBack "exhaust kernel isNil: aee_mobility_fnc_calculateExhaustPlume is not compiled";
} else {
    // [idleTempC, fullTempC, idleDepthM, fullDepthM], the four declared tiers.
    private _tiers = [
        [300, 480, 0.35, 0.60],
        [420, 600, 0.35, 1.00],
        [480, 750, 0.40, 1.50],
        [550, 1200, 0.50, 2.50]
    ];
    private _exhaustBad = [];
    private _sizeLo = 1e9;
    private _sizeHi = -1e9;
    {
        _x params ["_iT", "_fT", "_iD", "_fD"];
        if (_iD < _sizeLo) then { _sizeLo = _iD; };
        if (_fD > _sizeHi) then { _sizeHi = _fD; };
        private _p0 = [0, _iT, _fT, _iD, _fD] call aee_mobility_fnc_calculateExhaustPlume;
        private _p1 = [1, _iT, _fT, _iD, _fD] call aee_mobility_fnc_calculateExhaustPlume;
        private _ph = [0.5, _iT, _fT, _iD, _fD] call aee_mobility_fnc_calculateExhaustPlume;
        private _pUp = [2, _iT, _fT, _iD, _fD] call aee_mobility_fnc_calculateExhaustPlume;
        private _pDn = [-1, _iT, _fT, _iD, _fD] call aee_mobility_fnc_calculateExhaustPlume;
        if (abs ((_p0 select 0) - _iT) > 0.0001) then { _exhaustBad pushBack format ["tier %1 idle temp %2 want %3", _x, (_p0 select 0), _iT]; };
        if (abs ((_p0 select 1) - _iD) > 0.0001) then { _exhaustBad pushBack format ["tier %1 idle depth %2 want %3", _x, (_p0 select 1), _iD]; };
        if (abs ((_p1 select 0) - _fT) > 0.0001) then { _exhaustBad pushBack format ["tier %1 full temp %2 want %3", _x, (_p1 select 0), _fT]; };
        if (abs ((_p1 select 1) - _fD) > 0.0001) then { _exhaustBad pushBack format ["tier %1 full depth %2 want %3", _x, (_p1 select 1), _fD]; };
        if (abs ((_ph select 0) - ((_iT + _fT) / 2)) > 0.0001) then { _exhaustBad pushBack format ["tier %1 mid temp %2 not linear", _x, (_ph select 0)]; };
        if (abs ((_ph select 1) - ((_iD + _fD) / 2)) > 0.0001) then { _exhaustBad pushBack format ["tier %1 mid depth %2 not linear", _x, (_ph select 1)]; };
        if (abs ((_pUp select 1) - _fD) > 0.0001) then { _exhaustBad pushBack format ["tier %1 power 2 did not clamp to full", _x]; };
        if (abs ((_pDn select 1) - _iD) > 0.0001) then { _exhaustBad pushBack format ["tier %1 power -1 did not clamp to idle", _x]; };
        private _s = 0;
        private _prevD = -1;
        private _prevT = -1;
        while {_s <= 10} do {
            private _r = [(_s / 10), _iT, _fT, _iD, _fD] call aee_mobility_fnc_calculateExhaustPlume;
            if ((_r select 1) < (_prevD - 0.0001)) then { _exhaustBad pushBack format ["tier %1 depth fell at power %2", _x, (_s / 10)]; };
            if ((_r select 0) < (_prevT - 0.0001)) then { _exhaustBad pushBack format ["tier %1 temp fell at power %2", _x, (_s / 10)]; };
            _prevD = _r select 1;
            _prevT = _r select 0;
            _s = _s + 1;
        };
    } forEach _tiers;

    // An inverted pair and a non-positive declaration are refused, not run.
    private _inv = [0.5, 600, 400, 1.0, 0.5] call aee_mobility_fnc_calculateExhaustPlume;
    if ((_inv select 1) != 0) then { _exhaustBad pushBack "an inverted pair was not refused"; };
    private _neg = [0.5, -1, 400, 0.35, 0.6] call aee_mobility_fnc_calculateExhaustPlume;
    if ((_neg select 1) != 0) then { _exhaustBad pushBack "a non-positive temperature was not refused"; };
    if (abs (_sizeLo - 0.35) > 0.0001) then { _exhaustBad pushBack format ["size floor %1 want 0.35", _sizeLo]; };
    if (abs (_sizeHi - 2.5) > 0.0001) then { _exhaustBad pushBack format ["size ceiling %1 want 2.5", _sizeHi]; };

    // The area-derived live count, mirrored from fnc_applyExhaustShimmerFX and
    // pinned by tools/tests/test_exhaust_shimmer.py.
    private _overdrawBudget = 190;
    private _sources = 3;
    private _maxLive = 12;
    private _minLive = 4;
    private _liveBad = [];
    private _worst = 0;
    private _prevLive = 1e9;
    private _d = 0.35;
    while {_d <= 2.5001} do {
        private _allowed = _overdrawBudget / (_sources * _d * _d);
        private _live = ((floor _allowed) min _maxLive) max _minLive;
        private _over = _sources * _live * _d * _d;
        if (_live > _prevLive) then { _liveBad pushBack format ["live count rose at %1 m", _d]; };
        if (_over > (_overdrawBudget + 0.0001)) then { _liveBad pushBack format ["overdraw %1 m2 at %2 m", _over, _d]; };
        if (_over > _worst) then { _worst = _over; };
        _prevLive = _live;
        _d = _d + 0.01;
    };

    if ((_exhaustBad isEqualTo []) && (_liveBad isEqualTo [])) then {
        _pass = _pass + 1;
        diag_log text format ["[P65] [PASS] exhaust plume power ramp: 4 tiers linear and monotone, size %1..%2 m, worst overdraw %3 m2 at or below %4", _sizeLo, _sizeHi, _worst, _overdrawBudget];
    } else {
        _fail = _fail + 1;
        {
            _notes pushBack format ["exhaust: %1", _x];
        } forEach (_exhaustBad + _liveBad);
    };
};

// ---- the engine reader: measured on this server ----------------------------
// The renderer reads collectiveRTD for a helicopter and throttleRTD for fixed
// wing, both gated on difficultyEnabledRTD and both compiled at run time so a
// build without RotorLib still loads.  The harness dedicated-server binary
// carries collectiveRTD and difficultyEnabledRTD but NOT throttleRTD, so the
// fixed-wing token would fail the script parse and is therefore never named
// here.  This block MEASURES what the server exposes and asserts the FALLBACK
// the renderer takes without a usable reader: no published value, so the
// declared idle fraction drives the plume.  It never asserts a value the
// server cannot produce.
private _rtdOn = difficultyEnabledRTD;
private _rtdHeli = createVehicle ["B_Heli_Light_01_F", [2000, 3000, 100], [], 0, "FLY"];
private _collective = nil;
if (!isNull _rtdHeli) then { _collective = collectiveRTD _rtdHeli; };
if (isNil "_collective") then { _collective = []; };
if (!isNull _rtdHeli) then { deleteVehicle _rtdHeli; };
diag_log text format ["[P65] reader: difficultyEnabledRTD %1, collectiveRTD %2 (%3), throttleRTD absent from the harness server binary",
    _rtdOn, _collective, typeName _collective];

// The fallback the renderer takes without a usable reader: no published value,
// so the declared idle fraction (0.05) drives the plume.  The kernel is linear,
// so the land row gives 0.35 + (0.60 - 0.35) * 0.05 = 0.3625 m at the idle
// fraction and 0.60 m at full.
private _idle = [0.05, 300, 480, 0.35, 0.60] call aee_mobility_fnc_calculateExhaustPlume;
private _full = [1, 300, 480, 0.35, 0.60] call aee_mobility_fnc_calculateExhaustPlume;
if ((abs ((_idle select 1) - 0.3625) > 0.0001) || {abs ((_full select 1) - 0.60) > 0.0001}) then {
    _fail = _fail + 1;
    _notes pushBack format ["declared fallback wrong: idle %1 want 0.3625, full %2 want 0.60", _idle select 1, _full select 1];
} else {
    _pass = _pass + 1;
    diag_log text "[P65] reader: RTD not exercised headless, declared idle and full fallback asserted";
};

// ---- engine load, derived from tractive demand plus acceleration ----------
// A road vehicle has no throttle reader, so the renderer derives its load.
// The renderer exits at hasInterface on a dedicated server, so this measures
// the pure kernel: it sweeps the PHYSICAL curve, taking the force and the
// speed and asking the kernel for the fraction.  It does not assert over a
// cartesian product of linked inputs, because that invents a bug the
// renderer can never hit.
private _LOAD = "aee_mobility_fnc_calculateEngineLoad";
if (isNil _LOAD) then {
    _fail = _fail + 1;
    _notes pushBack "engine load kernel isNil: aee_mobility_fnc_calculateEngineLoad is not compiled";
} else {
    private _ratedW = 150000;
    private _idleF = 0.05;
    private _loadBad = [];
    private _loadSweep = "";

    // Zero force, zero acceleration, zero speed reaches the idle floor and
    // not a hard zero.  The engine publishes no rpm for a road vehicle, so a
    // stationary engine at high rpm cannot be distinguished from idle.
    private _still = [0, 0, 1500, 0, _ratedW, _idleF] call aee_mobility_fnc_calculateEngineLoad;
    if (abs (_still - _idleF) > 0.0001) then {
        _loadBad pushBack format ["still load %1 want idle %2", _still, _idleF];
    };

    // Linear in force at fixed speed, and rising.  The drag term is a
    // function of speed alone, so it is constant across a force sweep.
    private _speedF = 20;
    private _massF = 1500;
    private _f1 = [1000, _speedF, _massF, 0, _ratedW, _idleF] call aee_mobility_fnc_calculateEngineLoad;
    private _f2 = [2000, _speedF, _massF, 0, _ratedW, _idleF] call aee_mobility_fnc_calculateEngineLoad;
    private _f3 = [3000, _speedF, _massF, 0, _ratedW, _idleF] call aee_mobility_fnc_calculateEngineLoad;
    if ((_f2 - _f1) <= 0) then { _loadBad pushBack "force sweep did not rise"; };
    if (abs ((_f3 - _f2) - (_f2 - _f1)) > 0.0001) then { _loadBad pushBack "load not linear in force"; };
    _loadSweep = format ["force %1/%2/%3", _f1, _f2, _f3];

    // Linear in acceleration at fixed force and speed, and rising.
    private _a1 = [1000, _speedF, _massF, 0, _ratedW, _idleF] call aee_mobility_fnc_calculateEngineLoad;
    private _a2 = [1000, _speedF, _massF, 1, _ratedW, _idleF] call aee_mobility_fnc_calculateEngineLoad;
    private _a3 = [1000, _speedF, _massF, 2, _ratedW, _idleF] call aee_mobility_fnc_calculateEngineLoad;
    if ((_a2 - _a1) <= 0) then { _loadBad pushBack "acceleration sweep did not rise"; };
    if (abs ((_a3 - _a2) - (_a2 - _a1)) > 0.0001) then { _loadBad pushBack "load not linear in acceleration"; };

    // The clamp holds at the top: a huge force cannot exceed 1.
    private _hot = [1000000000, 60, _massF, 0, _ratedW, _idleF] call aee_mobility_fnc_calculateEngineLoad;
    if (_hot > 1) then { _loadBad pushBack format ["load %1 above 1", _hot]; };

    // A non-positive rated power is refused with the -1 sentinel.
    private _noPwr = [1000, _speedF, _massF, 0, 0, _idleF] call aee_mobility_fnc_calculateEngineLoad;
    if (_noPwr != -1) then { _loadBad pushBack format ["rated power 0 was not refused, got %1", _noPwr]; };
    private _negPwr = [1000, _speedF, _massF, 0, -5000, _idleF] call aee_mobility_fnc_calculateEngineLoad;
    if (_negPwr != -1) then { _loadBad pushBack format ["negative rated power was not refused, got %1", _negPwr]; };

    if (_loadBad isEqualTo []) then {
        _pass = _pass + 1;
        diag_log text format ["[P65] [PASS] engine load derived: %1, idle floor %2, clamp and refusal hold", _loadSweep, _idleF];
    } else {
        _fail = _fail + 1;
        {
            _notes pushBack format ["engine load: %1", _x];
        } forEach _loadBad;
    };
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
