// PHASE 86: the rain-scaled film grain kernel, headless (aee-workshop-copy
// item 5).
//
// The kernel is pure, so a dedicated server drives it directly at the four
// branches and asserts the exact six-element FilmGrain arrays.  It also
// asserts that every returned array keeps 1 (colour) as the sixth element,
// never 0 (monochrome) - the invariant fixed at c753730.  It renders nothing.

private _fn = missionNamespace getVariable ["aee_vision_fnc_weatherGrainParams", nil];

private _pass = 0;
private _fail = 0;
private _notes = [];

if (isNil "_fn") then {
    diag_log text "[P86] [FAIL] weatherGrainParams kernel not compiled";
} else {
    // [rain, sunOrMoon, expected array]
    private _cases = [
        [0.6, 0, [0.01, 0.7, 3.5, 1, 1, 1]],
        [0.0, 0, [0.01, 0.5, 0.5, 0.1, 0.1, 1]],
        [0.6, 1, [0.01, 0.45, 3, 1, 1, 1]],
        [0.0, 1, [0.1, 0.5, 0.5, 0.1, 0.1, 1]]
    ];
    {
        _x params ["_rain", "_sun", "_want"];
        private _got = [_rain, _sun] call _fn;
        private _ok = (count _got) == 6;
        if (_ok) then {
            {
                if (abs ((_got select _forEachIndex) - (_want select _forEachIndex)) > 1e-6) then {
                    _ok = false;
                };
            } forEach _want;
        };
        // The colour invariant: the sixth element is 1, never 0.
        if (_ok && {(_got select 5) != 1}) then { _ok = false; };
        if (_ok) then {
            _pass = _pass + 1;
        } else {
            _fail = _fail + 1;
            _notes pushBack format ["rain=%1 sun=%2 got=%3 want=%4", _rain, _sun, str _got, str _want];
        };
    } forEach _cases;
};

if ((_fail == 0) && {_pass >= 4}) then {
    diag_log text format ["[P86] [PASS] weather grain kernel: %1 branches", _pass];
} else {
    diag_log text format ["[P86] [FAIL] weather grain kernel: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
