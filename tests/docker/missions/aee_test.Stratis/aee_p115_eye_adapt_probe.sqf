// PHASE 115: the published eye-adaptation state.
//
// The eye adaptation driver is client-only (it exits at hasInterface on a
// dedicated server), so this probe drives the REAL pure kernel
// fnc_eyeAdaptState with fixtures and asserts the settled-eye and
// falling-time contract that fixes the operator's stuck-adaptation report:
//   - a settled eye reports no pending adaptation (direction 0, tau 0, time 0),
//     even when a settled pool sits a floating-point hair above the target
//     (the RPT showed adapt=[-1.54151,0.501617,0,1198.29]: a settled eye
//     reporting a ~20 minute time to adapt);
//   - an adapting eye reports a time that falls as the remaining gap shrinks,
//     so the perception monitor's stuckAdaptation test (a time that does not
//     fall) is meaningful instead of false-firing on every adapting window.
// It renders nothing.

private _state = missionNamespace getVariable ["aee_optics_fnc_eyeAdaptState", nil];
private _pass = 0;
private _fail = 0;
private _notes = [];

if (isNil "_state") then {
    _fail = _fail + 1;
    _notes pushBack "eyeAdaptState kernel not compiled";
} else {
    // 1. Settled: direction 0, tau 0, time 0.
    private _settled = [[0, 0], 0, 1, 2, 120, 400] call _state;
    if (((_settled select 0) == 0) && {(_settled select 1) == 0} && {(_settled select 2) == 0}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["settled %1", str _settled];
    };

    // 2. A settled pool a hair above the target must still report nothing.
    private _target = -1.54151;
    private _hair = [[_target, _target + 1e-9], _target, 1, 2, 120, 400] call _state;
    if (((_hair select 0) == 0) && {(_hair select 1) == 0} && {(_hair select 2) == 0}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["hair %1", str _hair];
    };

    // 3. The reported time falls as the remaining gap shrinks.
    private _near = [[-2, -2], 0, 1, 2, 120, 400] call _state;
    private _far = [[-2, -2], 2, 1, 2, 120, 400] call _state;
    if (((_near select 2) > 0) && {(_near select 2) < (_far select 2)}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["near %1 far %2", _near select 2, _far select 2];
    };
};

if (_fail isEqualTo 0) then {
    diag_log text format ["[P115] [PASS] eye adaptation state: settled and falling-time contract (%1 checks)", _pass];
} else {
    diag_log text format ["[P115] [FAIL] eye adaptation state: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
