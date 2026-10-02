// PHASE 77: a soldier is not a vehicle.
//
// WHY THIS EXISTS. aee_mobility_fnc_classifyVehicle used to resolve any class
// by corpus, band or token, so a soldier could band-match a light vehicle on
// its own engine mass. The live case is the traction model, which reads
// `vehicle _unit`. On a man on foot that returns the man. Commit c6e8b5e gates
// the classifier on the three engine vehicle families (LandVehicle, Air, Ship).
// The classifier emits no log, so the RPT cannot show the fix. This probe reads
// the kernel directly and confirms the return value. The classifier carries no
// hasInterface gate, so a dedicated server can run it.
//
// RETURN CONTRACT (fnc_classifyVehicle.sqf):
//   ARRAY [classToken, vehicleType, isTracked, hasTurret, massKg, lengthM,
//          widthM, heightM, matchedBy]
//   "none" is the sentinel for a non-vehicle: classToken is "" and matchedBy
//   is "none", for example ["", "wheeled", false, false, 0, 0, 0, 0, "none"].
//
// WHAT IS PROVEN HEADLESSLY: the classifier returns the none sentinel for a
// spawned soldier (a CAManBase). This is a pure kernel result.
//
// WHAT STILL NEEDS A CLIENT RUN: nothing for this claim. A client only exercises
// the classifier through the traction path, which this probe covers by testing
// the kernel itself.
//
// Bounded and deterministic: one spawned soldier, one call, one delete.
// Emits: [P77] [PASS] / [P77] [FAIL] <reason> lines.

private _fnClassify = missionNamespace getVariable ["aee_mobility_fnc_classifyVehicle", nil];
if (isNil "_fnClassify") exitWith {
    diag_log text "[P77] [FAIL] aee_mobility_fnc_classifyVehicle not compiled";
};

private _grp = createGroup [west, true];
private _unit = _grp createUnit ["B_Soldier_F", [4210, 4250, 0], [], 0, "NONE"];

if (isNull _unit) exitWith {
    diag_log text "[P77] [FAIL] soldier unit could not be spawned";
    if (!isNull _grp) then { deleteGroup _grp; };
};

private _result = [_unit] call _fnClassify;
private _token = _result select 0;
private _matchedBy = _result select 8;
private _isMan = _unit isKindOf "CAManBase";
private _isLand = _unit isKindOf "LandVehicle";

diag_log text format ["[P77] DIAG unit=%1 isMan=%2 isLand=%3 classified=%4",
    typeOf _unit, _isMan, _isLand, _result];

if (_isMan && {_token == ""} && {_matchedBy == "none"}) then {
    diag_log text format ["[P77] [PASS] a soldier is not a vehicle: token=empty matchedBy=none (%1)", typeOf _unit];
} else {
    diag_log text format ["[P77] [FAIL] a soldier resolved as a vehicle: token=%1 matchedBy=%2 result=%3",
        _token, _matchedBy, _result];
};

deleteVehicle _unit;
if (!isNull _grp) then { deleteGroup _grp; };
