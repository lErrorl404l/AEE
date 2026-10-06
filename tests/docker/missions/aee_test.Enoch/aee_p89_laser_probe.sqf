// PHASE 89: the laser marker daylight alpha, headless (aee-workshop-copy item
// 8).
//
// The kernel is pure, so a dedicated server drives it directly and asserts the
// engine sunOrMoon mapping: alpha 1 at night (0), 0.2 at full day (1), 0.7 at
// the half, and the 0..1 clamp.  The setting default is asserted too.  It
// renders nothing.
//
// The colour hue lives in fnc_ltmDraw.sqf: only the fourth (alpha) element of
// the two drawLine3D colours changes.  That is pinned by the Python source
// contract in tools/tests/test_ltm.py, so this probe checks the alpha seam.

private _fn = missionNamespace getVariable ["aee_nightvision_fnc_ltmDaylightAlpha", nil];

private _pass = 0;
private _fail = 0;
private _notes = [];

if (isNil "_fn") then {
    diag_log text "[P89] [FAIL] ltmDaylightAlpha kernel not compiled";
} else {
    private _night = [0.0] call _fn;
    if (abs (_night - 1.0) < 1e-6) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["alpha(0)=%1", _night]; };

    private _day = [1.0] call _fn;
    if (abs (_day - 0.2) < 1e-6) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["alpha(1)=%1", _day]; };

    private _mid = [0.5] call _fn;
    if (abs (_mid - 0.7) < 1e-6) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["alpha(0.5)=%1", _mid]; };

    private _low = [-1.0] call _fn;
    private _high = [2.0] call _fn;
    if ((abs (_low - 1.0) < 1e-6) && {abs (_high - 0.0) < 1e-6}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["clamp low=%1 high=%2", _low, _high];
    };

    private _fade = missionNamespace getVariable ["aee_nightvision_ltmDaylightFade", false];
    if (_fade) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack "ltmDaylightFade default off"; };
};

if ((_fail == 0) && {_pass >= 5}) then {
    diag_log text format ["[P89] [PASS] laser daylight alpha: %1 checks", _pass];
} else {
    diag_log text format ["[P89] [FAIL] laser daylight alpha: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
