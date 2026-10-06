// PHASE 101: the cross-module consistency evaluator, headless.
//
// The runtime monitor runs on the server, but the evaluator it drives is pure:
// it reads no world state and calls no module function.  This probe loads the
// compiled-in invariant table and drives the evaluator with an agreeing map
// and a three-way disagreeing map, the same fixtures the Python kernel test
// uses.  The disagreeing map splits the ground chain, so INV-2 must raise
// exactly three producers and no other row may fail.
//
// The probe caps its own work at 200 ms and prints the diag_tickTime
// measurement.  It renders nothing and needs no player.
//
// Emits [P101] PASS/FAIL lines.

private _loadTable = missionNamespace getVariable ["aee_core_fnc_consistencyLoadTable", nil];
private _evaluate = missionNamespace getVariable ["aee_core_fnc_evaluateConsistency", nil];

if (isNil "_loadTable" || {isNil "_evaluate"}) exitWith {
    diag_log text "[P101] [FAIL] consistency kernels not compiled (loadTable/evaluate)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

private _table = [] call _loadTable;

// The agreeing map: every invariant holds.  The aperture 34.25 lies on the
// default lux-to-aperture line for an adapted luminance of 100 cd/m2, and the
// prior wind sample keeps INV-3 monotone.
private _agree = [
    ["aee_core_illuminanceLux", 100],
    ["aee_optics_eyeAdaptedLux", 100],
    ["aee_optics_eyeAperture", 34.25],
    ["aee_core_currentTemperature", 15],
    ["aee_thermal_groundNodeStack", 16],
    ["aee_core_groundSurfaceTemp", 14],
    ["aee_core_avgGroundTemp", 15],
    ["aee_core_currentWindStr", 5],
    ["aee_environmental_scentDispersionIntensity", 0.5],
    ["aee_core_currentTurbulence", 0.3],
    ["aee_thermal_humanCoreTempC", 37],
    ["aee_core_coreBodyTemp", 37.5],
    ["aee_core_currentSunElevation", 30],
    ["aee_thermal_skyBandTempC", -20],
    ["aee_core_lightIsNight", false],
    ["aee_environmental_nightClassification", 0],
    ["aee_core_currentWindStrRef", [4, 0.4, 0.2]]
];

// The three-way disagreeing map: the air temperature drops away from the three
// ground values, so the ground chain splits three ways.
private _disagree = +_agree;
{
    private _pair = _disagree select _forEachIndex;
    switch (_pair select 0) do {
        case "aee_core_currentTemperature": {
            _disagree set [_forEachIndex, ["aee_core_currentTemperature", 0]];
        };
        case "aee_thermal_groundNodeStack": {
            _disagree set [_forEachIndex, ["aee_thermal_groundNodeStack", 100]];
        };
        case "aee_core_groundSurfaceTemp": {
            _disagree set [_forEachIndex, ["aee_core_groundSurfaceTemp", 100]];
        };
        case "aee_core_avgGroundTemp": {
            _disagree set [_forEachIndex, ["aee_core_avgGroundTemp", 100]];
        };
    };
} forEach _disagree;

private _t0 = diag_tickTime;

// 1. The table is non-empty and every row carries the fixed 8-field layout.
private _layoutOk = (count _table) > 0;
{
    if ((count _x) != 8) then { _layoutOk = false; };
} forEach _table;
if (_layoutOk) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["table layout %1 rows", count _table];
};

// 2. The agreeing map passes every row.
private _agreeResult = [_table, _agree] call _evaluate;
private _agreeOk = _agreeResult select 0;
{
    if !(_x select 1) then { _agreeOk = false; };
} forEach (_agreeResult select 1);
if (_agreeOk) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "agreeing map raised a row";
};

// 3. The disagreeing map fails and raises exactly INV-2.
private _disResult = [_table, _disagree] call _evaluate;
private _verdicts = _disResult select 1;
private _failed = [];
{
    if !(_x select 1) then { _failed pushBack (_x select 0); };
} forEach _verdicts;
if (!(_disResult select 0) && {_failed isEqualTo ["INV-2"]}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["failed rows %1", str _failed];
};

// 4. INV-2 names three modules in disagreement.
private _inv2 = [];
{
    if ((_x select 0) == "INV-2") then { _inv2 = _x; };
} forEach _verdicts;
if ((count _inv2) == 4) then {
    if ((_inv2 select 3) == 3) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["INV-2 disagreement %1 (expected 3)", _inv2 select 3];
    };
} else {
    _fail = _fail + 1;
    _notes pushBack "INV-2 row missing";
};

// 5. A missing producer is no-data, not a failure: the evaluator never throws.
private _noData = [_table, [["aee_core_illuminanceLux", 100]]] call _evaluate;
if (_noData select 0) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "no-data map failed";
};

private _ms = (diag_tickTime - _t0) * 1000;
if (_ms < 200) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["work %1 ms (cap 200)", _ms];
};

diag_log text format ["[P101] work %1 ms for 6 checks", _ms];

if (_fail == 0) then {
    diag_log text format ["[P101] [PASS] consistency: table, agreement, three-way disagreement and no-data (%1 checks)", _pass];
} else {
    diag_log text format ["[P101] [FAIL] consistency: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
