// PHASE 82: the CBA per-frame handler entry contract.
//
// CBA_fnc_addPerFrameHandler registers a function, and CBA_A3
// addons/common/init_perFrameHandler.sqf runs it as
// `[_args, _handle] call _function`, with `_args` defaulting to [].  A
// registered entry that declares a strict `params` therefore validates
// [_args, _handle] and throws on the type every frame.  This was the live
// defect: 16 "Params: Type Number, expected Bool" and 16 "Params: Type Array,
// expected Bool" errors across fnc_aiTick.sqf and fnc_wildlifeTick.sqf.
//
// A dedicated server has hasInterface false, so the client per-frame handler
// is never added here.  This probe calls the registered entries with the
// exact handler array to prove the signatures accept it headlessly.  A params
// error would land in the RPT as an un-benign Error line and fail the gate.

private _entries = [
    "aee_ai_fnc_aiTickPFH",
    "aee_wildlife_fnc_wildlifeTickPFH"
];
private _pass = 0;
private _fail = 0;
private _notes = [];
{
    private _fn = missionNamespace getVariable [_x, nil];
    if (isNil "_fn") then {
        _fail = _fail + 1;
        _notes pushBack format ["%1 not compiled", _x];
    } else {
        // The exact CBA call shape: [_args, _handle] call _function.
        [[], 12345] call _fn;
        _pass = _pass + 1;
    };
} forEach _entries;

if (_fail == 0) then {
    diag_log text format ["[P82] [PASS] per-frame handler entries accept the CBA handler array: %1", _pass];
} else {
    diag_log text format ["[P82] [FAIL] per-frame handler entries: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
