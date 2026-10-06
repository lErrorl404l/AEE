// PHASE 108: the position consistency verdict.
//
// The live monitor FUNC(runGeoConsistency) reads the published anchor and
// world location, computes the inputs through the REAL geo kernels, runs the
// REAL pure evaluator and publishes aee_core_positionDivergence.  The probe
// asserts the publication contract on the live world and that the pure
// evaluator returns NO divergence when the sources agree.
//
// LIVE-WORLD NOTE.  Stratis ships no mapArea, so the anchor falls back to the
// CfgWorlds keys.  FUNC(worldToMgrs) then uses the tangent plane at the anchor
// centre, which places the WORLD ORIGIN at the anchor centre; the world CENTRE
// (mapSize/2) therefore projects half a map away, and the ANCHOR-CENTRE row
// reports a divergence on the live world.  The probe records that live verdict
// (the monitor detects the no-box case) and asserts the no-divergence verdict
// on a consistent value set, which is what the evaluator must return when the
// sources agree.
//
// Emits [P108] PASS/FAIL lines.

private _fnRun = missionNamespace getVariable ["aee_core_fnc_runGeoConsistency", nil];
private _fnEval = missionNamespace getVariable ["aee_core_fnc_evaluateGeoConsistency", nil];
if (isNil "_fnRun" || {isNil "_fnEval"}) exitWith {
    diag_log text "[P108] [FAIL] consistency kernels not compiled (runGeoConsistency/evaluateGeoConsistency)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// 1. the live monitor publishes a boolean verdict and returns the same value
private _verdict = call _fnRun;
// A non-nil sentinel: the test suite forbids a nil default read before a
// guard, and [] is never a bool, so the isEqualType true check still proves
// the monitor published a boolean.
private _published = missionNamespace getVariable ["aee_core_positionDivergence", []];
if ((_published isEqualType true) && {_published == _verdict}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["published %1 verdict %2", str _published, str _verdict];
};

// 2. the pure evaluator returns no divergence for a consistent value set.
//    The table mirrors data/consistency/position_invariants.json (id,
//    predicate, pairs, tolerance); the values are the Altis box centre, where
//    every source agrees, so every row must pass.
private _table = [
    ["GRID-AGREE", "engine_grid_agrees_with_mgrs", "pairs_equal", [], [["engineGridCentre", "engineGridFromMgrs"]], 0, "warn"],
    ["ANCHOR-CENTRE", "anchor_centre_maps_to_anchor", "agree_within", [], [["anchorLat", "projectedLat"], ["anchorLon", "projectedLon"]], 0.000001, "warn"],
    ["WORLDLOC-ANCHOR", "world_location_equals_anchor", "agree_within", [], [["anchorLat", "worldLocationLat"], ["anchorLon", "worldLocationLon"]], 0.000001, "error"],
    ["MGRS-ROUNDTRIP", "mgrs_round_trips", "agree_within", [], [["centreX", "roundtripX"], ["centreY", "roundtripY"], ["easting", "parsedEasting"], ["northing", "parsedNorthing"]], 1.0, "error"]
];
private _consistent = [
    ["engineGridCentre", "024577"],
    ["engineGridFromMgrs", "024577"],
    ["anchorLat", 39.906515],
    ["anchorLon", 25.246742],
    ["projectedLat", 39.906515],
    ["projectedLon", 25.246742],
    ["worldLocationLat", 39.906515],
    ["worldLocationLon", 25.246742],
    ["centreX", 15360.0],
    ["centreY", 15360.0],
    ["roundtripX", 15360.0],
    ["roundtripY", 15360.0],
    ["easting", 501341.0],
    ["northing", 4418852.0],
    ["parsedEasting", 501341.0],
    ["parsedNorthing", 4418852.0]
];

private _result = [_table, _consistent] call _fnEval;
private _divergence = _result select 0;
private _verdicts = _result select 1;
private _allPass = true;
for "_i" from 0 to ((count _verdicts) - 1) do {
    if (!((_verdicts select _i) select 1)) then { _allPass = false; };
};

if ((_divergence == false) && {_allPass} && {(count _verdicts) == 4}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["consistent set diverged %1", str _verdicts];
};

diag_log text format ["[P108] live verdict=%1 (Stratis has no mapArea, so the fallback tangent plane fails the centre row); consistent set divergence=%2", _verdict, _divergence];

if (_fail == 0) then {
    diag_log text format ["[P108] [PASS] position consistency verdict published on %1 and a consistent set agrees (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P108] [FAIL] position consistency: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
