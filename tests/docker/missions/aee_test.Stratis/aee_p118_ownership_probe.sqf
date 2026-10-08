// P117 ownership probe (ADR-027).
//
// Two assertions, both read-only:
//
//  1. The engine-class ownership sentinels are live and every live config
//     value matches AEE's declared value. A mismatch is the silent load-order
//     loss: another mod loaded after AEE and won the config merge for a class
//     AEE owns.
//
//  2. When the merge-order probe addon (probe_owner) is loaded, report who won
//     the config merge for the class it re-declares. docker_test.sh
//     --merge-order loads the probe once before and once after AEE and asserts
//     the winner each time: AEE wins when it loads last, and loses when it does
//     not. That is the ceiling ADR-027 records.
//
// Emits one [P118] line and exits. Writes no state.

private _pass = true;
private _notes = [];

private _sentinels = missionNamespace getVariable ["aee_core_ownershipSentinels", []];
if !(_sentinels isEqualType []) then { _sentinels = []; };
if (_sentinels isEqualTo []) then {
    _pass = false;
    _notes pushBack "sentinel registry empty";
};

private _mismatch = 0;
{
    _x params [["_id", ""], ["_path", []], ["_prop", ""], ["_type", ""], ["_expected", 0]];
    private _cfg = configFile;
    { _cfg = _cfg >> _x; } forEach _path;
    private _entry = _cfg >> _prop;
    private _live = switch (_type) do {
        case "number": { getNumber _entry };
        case "array": { getArray _entry };
        case "text": { getText _entry };
        default { nil };
    };
    private _ok = if (isNull _entry) then { false } else {
        switch (_type) do {
            case "number": { abs (_live - _expected) <= (0.000001 + abs (_expected) * 0.000001) };
            case "array": { _live isEqualTo _expected };
            case "text": { _live isEqualTo _expected };
            default { false };
        };
    };
    if (!_ok) then { _mismatch = _mismatch + 1; };
} forEach _sentinels;
_notes pushBack format ["sentinels=%1 mismatch=%2", count _sentinels, _mismatch];

if ((isClass (configFile >> "CfgPatches" >> "probe_before")) || (isClass (configFile >> "CfgPatches" >> "probe_after"))) then {
    // The probe addon re-declares CfgVehicles/B_MBT_01_cannon_F/mass. The
    // BEFORE variant is independent (loads before AEE); the AFTER variant
    // requires aee_mobility (loads after AEE).
    private _probeMass = 999999;
    private _live = getNumber (configFile >> "CfgVehicles" >> "B_MBT_01_cannon_F" >> "mass");
    private _aeeMass = -1;
    {
        if (((_x select 1) isEqualTo ["CfgVehicles", "B_MBT_01_cannon_F"]) && {(_x select 2) == "mass"}) then {
            _aeeMass = _x select 4;
        };
    } forEach _sentinels;
    private _winner = "unknown";
    if (abs (_live - _probeMass) < 0.5) then { _winner = "probe"; };
    if (abs (_live - _aeeMass) < 0.5) then { _winner = "aee"; };
    if (_winner == "unknown") then { _pass = false; };
    _notes pushBack format ["winner=%1 live=%2 aee=%3 probe=%4", _winner, _live, _aeeMass, _probeMass];
} else {
    if (_mismatch > 0) then { _pass = false; };
};

private _msg = _notes joinString " | ";
if (_pass) then {
    diag_log text format ["[P118] [PASS] ownership %1", _msg];
} else {
    diag_log text format ["[P118] [FAIL] ownership %1", _msg];
};
