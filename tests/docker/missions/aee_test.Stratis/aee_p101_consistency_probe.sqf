// PHASE 101: the cross-module consistency evaluator, headless.
//
// The runtime monitor runs on the server, but the evaluator it drives is pure:
// it reads no world state and calls no module function.  This probe loads the
// compiled-in invariant table, drives the REAL INV-2 ground-surface producer
// (aee_thermal_fnc_calculateGroundTemperature) and hands the evaluator the
// REAL aee_core_groundSurfaceTemp container that producer publishes, then
// drives a disagreeing map.  The disagreeing map drops the air temperature
// away from the real container, so INV-2 must raise exactly two of its
// producers and no other row may fail.
//
// The ground-surface value is never a synthetic scalar.  A made-up number
// passes the row without ever exercising the container resolution the row
// depends on, which is the false assurance the unit test carried.
//
// The probe caps its own work at 200 ms and prints the diag_tickTime
// measurement.  It renders nothing and needs no player.
//
// Emits [P101] PASS/FAIL lines.

private _loadTable = missionNamespace getVariable ["aee_diagnostics_fnc_consistencyLoadTable", nil];
private _evaluate = missionNamespace getVariable ["aee_diagnostics_fnc_evaluateConsistency", nil];
private _groundProducer = missionNamespace getVariable ["aee_thermal_fnc_calculateGroundTemperature", nil];

if (isNil "_loadTable" || {isNil "_evaluate"}) exitWith {
    diag_log text "[P101] [FAIL] consistency kernels not compiled (loadTable/evaluate)";
};
if (isNil "_groundProducer") exitWith {
    diag_log text "[P101] [FAIL] ground-surface producer not compiled (calculateGroundTemperature)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

private _table = [] call _loadTable;

// Drive the REAL producer at a real map position.  The thermal wrapper solves
// the 4-layer node stack and publishes aee_core_groundSurfaceTemp as a
// per-cell HashMap of the solved surface temperature in C, keyed
// "<floor(x/5)>_<floor(y/5)>_<material>" (fnc_calculateGroundTemperature.sqf,
// lines 133-142).  The probe reads that real container and invents no value.
private _probePos = [worldSize / 2, worldSize / 2, 0];
[_probePos] call _groundProducer;
private _groundContainer = missionNamespace getVariable ["aee_core_groundSurfaceTemp", nil];

// The container must be real: a HashMap carrying at least one numeric cell.
// A missing or empty container reads no-data, which PASSES, so the probe would
// prove nothing.  This guard is the whole point of the change.
private _containerOk = false;
private _groundMean = 0;
if (!(isNil "_groundContainer") && {_groundContainer isEqualType createHashMap}) then {
    private _cells = values _groundContainer;
    private _numeric = 0;
    private _sum = 0;
    {
        if (_x isEqualType 0) then { _sum = _sum + _x; _numeric = _numeric + 1; };
    } forEach _cells;
    if (_numeric > 0) then {
        _containerOk = true;
        _groundMean = _sum / _numeric;
    };
};

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

// 2. The REAL producer published a resolvable container.
if (_containerOk) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "ground-surface container missing or empty";
};

// The agreeing map.  It is a night scene, so INV-1's night-scoped comparison
// runs: the eye scene illuminance (100 lx) equals the core illuminance
// (100 lx) at a sun elevation below the horizon.  INV-2's ground-surface
// producer is the REAL container; the air and average-ground references are
// pinned to the container's real mean, so the row resolves and agrees.
private _agree = [
    ["aee_core_illuminanceLux", 100],
    ["aee_eye_eyeSceneLux", 100],
    ["aee_core_currentTemperature", _groundMean],
    ["aee_core_groundSurfaceTemp", _groundContainer],
    ["aee_core_avgGroundTemp", _groundMean],
    ["aee_core_currentSunElevation", -30],
    ["aee_thermal_skyBandTempC", -20],
    ["aee_core_lightIsNight", true],
    ["aee_lighting_nightClassification", 4]
];

// 3. The agreeing map passes every row AND INV-2 resolves the container.  A
//    no-data row also passes, so the detail is checked, not only the pass.
private _agreeResult = [_table, _agree] call _evaluate;
private _agreeOk = _agreeResult select 0;
private _inv2Detail = "no-data";
{
    if !(_x select 1) then { _agreeOk = false; };
    if ((_x select 0) == "INV-2") then { _inv2Detail = _x select 2; };
} forEach (_agreeResult select 1);
if (_agreeOk && {(_inv2Detail find "range") == 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["agreeing map pass %1 INV-2 detail %2", _agreeOk, _inv2Detail];
};

// 4. The disagreeing map drops the air temperature 100 C below the real
//    container, so INV-2 fails and raises exactly two producers.  The
//    container is left unchanged: the real value, not a synthetic stand-in.
private _disagree = +_agree;
{
    if ((_x select 0) == "aee_core_currentTemperature") then {
        _disagree set [_forEachIndex, ["aee_core_currentTemperature", _groundMean - 100]];
    };
} forEach _disagree;
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

// 5. INV-2 names two producers in disagreement.
private _inv2 = [];
{
    if ((_x select 0) == "INV-2") then { _inv2 = _x; };
} forEach _verdicts;
if ((count _inv2) == 4) then {
    if ((_inv2 select 3) == 2) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["INV-2 disagreement %1 (expected 2)", _inv2 select 3];
    };
} else {
    _fail = _fail + 1;
    _notes pushBack "INV-2 row missing";
};

// 6. A missing producer is no-data, not a failure: the evaluator never throws.
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

diag_log text format ["[P101] work %1 ms for 7 checks", _ms];

if (_fail == 0) then {
    diag_log text format ["[P101] [PASS] consistency: table, real ground container, agreement, ground-chain disagreement and no-data (%1 checks)", _pass];
} else {
    diag_log text format ["[P101] [FAIL] consistency: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
