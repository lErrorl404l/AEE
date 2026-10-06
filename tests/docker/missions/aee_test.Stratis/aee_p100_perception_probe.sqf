// PHASE 100: the perception aggregate and deviation kernels, headless.
//
// The perception driver runs on a client and exits at hasInterface on a
// dedicated server, so the view state it composes each tick cannot be read
// here.  The two kernels the driver calls are pure: no world read, no module
// global, no engine command.  This probe drives them with fixed fixtures and
// asserts the schema length, a clean view, the discolouration flag and the
// blindness flag.  It also reads the runtime module-health report (task 4),
// which is written 10 s after core postInit and is therefore present by now.
//
// The probe caps its own work at 200 ms and prints the diag_tickTime
// measurement.  It renders nothing and needs no player.
//
// Emits [P100] PASS/FAIL lines.

missionNamespace setVariable ["aee_core_logDebug", false];
missionNamespace setVariable ["aee_optics_logDebug", false];

private _sample = missionNamespace getVariable ["aee_optics_fnc_perceptionSample", nil];
private _deviation = missionNamespace getVariable ["aee_optics_fnc_perceptionDetectDeviation", nil];

if (isNil "_sample" || {isNil "_deviation"}) exitWith {
    diag_log text "[P100] [FAIL] perception kernels not compiled (sample/deviation)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// The source clamp ends: aperture 8..50 (fnc_eyeAperture), pupil 1.9..8.0 mm
// (fnc_eyePupilSteady), the same fixture bounds the deviation kernel test uses.
private _identity = [1, 1, 0, 0];
private _noAdapt = [0, 0, 0, 0];

private _t0 = diag_tickTime;

// 1. The aggregate lays the view out in one fixed-length array.  The schema is
//    14 fields; a map with a few keys must still return every field, with the
//    graded default where a key is absent.
private _state = [[["sceneLux", 100], ["adaptedLux", 50], ["eyeAperture", 20]]] call _sample;
if ((count _state) == 14) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["schema length %1 (expected 14)", count _state];
};

// 2. A clean view raises no flag and an empty detail.
private _clean = [_identity, _identity, _noAdapt, 20, 4.9, 8, 50, 1.9, 8, 100, 50, -1] call _deviation;
if (_clean isEqualTo [false, false, false, false, ""]) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["clean view flags %1", str _clean];
};

// 3. An applied grade beyond the per-channel tolerance raises discolouration.
private _discol = [_identity, [1.2, 1, 0, 0], _noAdapt, 20, 4.9, 8, 50, 1.9, 8, 100, 50, -1] call _deviation;
if ((_discol select 0) && {(_discol select 4) == "discolouration"}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["discolouration flag %1 detail %2", _discol select 0, _discol select 4];
};

// 4. A clamped pupil, a pinned aperture and an extreme lux raise blindness.
private _blind = [_identity, _identity, _noAdapt, 8, 1.9, 8, 50, 1.9, 8, 0.001, 0.001, -1] call _deviation;
if ((_blind select 1) && {(_blind select 4) == "blindness"}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["blindness flag %1 detail %2", _blind select 1, _blind select 4];
};

// 5. The module-health report: one row per module, both init flags read.  Every
//    core module must have come up, so a module that never ran is named here
//    rather than hidden by a missing row.  A host-compat module is skipped by
//    the engine when its host mod is absent (the Docker mission loads only CBA),
//    so only those rows may carry false flags.
private _health = missionNamespace getVariable ["aee_core_moduleHealth", []];
private _healthOk = (_health isEqualType []) && {(count _health) > 0};
if (_healthOk) then {
    {
        if ((_x isEqualType []) && {(count _x) >= 3}
            && {((_x select 0) isEqualType "")}
            && {((_x select 1) isEqualType false)}
            && {((_x select 2) isEqualType false)}) then {
            private _hostCompat = (((_x select 0) select [0, 7]) == "compat_");
            if (!_hostCompat && {!(_x select 1) || {!(_x select 2)}}) then {
                _healthOk = false;
            };
        } else {
            _healthOk = false;
        };
    } forEach _health;
};
if (_healthOk) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["module health %1 rows", count _health];
};

private _ms = (diag_tickTime - _t0) * 1000;
if (_ms < 200) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["work %1 ms (cap 200)", _ms];
};

private _summary = _health apply {
    if ((_x isEqualType []) && {(count _x) >= 3}) then {
        format ["%1=%2/%3", _x select 0, _x select 1, _x select 2]
    } else {
        "malformed"
    };
};
diag_log text format ["[P100] module health: %1", _summary joinString " "];
diag_log text format ["[P100] work %1 ms for 6 checks", _ms];

if (_fail == 0) then {
    diag_log text format ["[P100] [PASS] perception kernels: schema, clean, discolouration, blindness and module health (%1 checks)", _pass];
} else {
    diag_log text format ["[P100] [FAIL] perception kernels: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
