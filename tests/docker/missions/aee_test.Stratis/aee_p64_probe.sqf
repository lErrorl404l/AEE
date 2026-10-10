// PHASE 64: the CBA engine-event bridge, measured. Re-measures the table.
//
// SEVEN runs were lost to probe faults. Recorded so the next reader avoids them:
//  1. exec runs SQS, not SQF, so the preprocessor never strips "//" and every
//     comment line is tokenised as code. Use execVM. Never inline a probe.
//  2. "default" is the UNARY switch-case form, not nil-coalescing. Use
//     getOrDefault or an isNil guard.
//  3. A private in an execVM file is not visible inside a code block that
//     CBA_fnc_waitAndExecute runs later. Publish via missionNamespace.
//  4. A raw BIS addEventHandler cannot take a class name. The engine says
//     "addeventhandler: Type String, expected Object,Group".
//  5. doFire and commandFire both fail to parse on this engine. Slots 5 and 6
//     of a Fired event are BOTH objects, so typeName cannot separate them, and
//     the fire primitive could not be made to work. The argument order is
//     therefore NOT measured here. Read it from CBA instead:
//     cba_xeh/fnc_compileEventHandlers.sqf:125 rebinds legacy "fired" as
//     _this = [0,1,2,3,4,6,5], swapping the magazine and the projectile.
//
// What this measures, none of which needs a weapon to fire:
//  (A) the acceptance boolean of CBA_fnc_addClassEventHandler per event.
//      The return value IS the answer: false for anything absent from
//      XEH_EVENTS, which is the whole of the HandleDamage question.
//  (B) that a per-object raw HandleDamage handler installed from a class Init
//      handler does attach. Init is in XEH_EVENTS and was measured firing, so
//      the install needs no damage event to prove itself.
private _okBis = ["CAManBase", "FiredBIS", { diag_log text "[P64] BIS-FIRED" }, true, [], false] call CBA_fnc_addClassEventHandler;
private _okLegacy = ["CAManBase", "Fired", { diag_log text "[P64] LEGACY-FIRED" }, true, [], false] call CBA_fnc_addClassEventHandler;
private _okBoom = ["CAManBase", "Explosion", { diag_log text "[P64] CLASS-EXPLOSION" }, true, [], false] call CBA_fnc_addClassEventHandler;
private _okHitPart = ["CAManBase", "HitPart", { diag_log text "[P64] CLASS-HITPART" }, true, [], false] call CBA_fnc_addClassEventHandler;
private _okHd = ["CAManBase", "HandleDamage", { diag_log text "[P64] CLASS-HD" }, true, [], false] call CBA_fnc_addClassEventHandler;
private _okInit = ["CAManBase", "Init", { diag_log text "[P64] CLASS-INIT" }, true, [], false] call CBA_fnc_addClassEventHandler;

private _okAttach = ["AllVehicles", "Init", {
    params ["_unit"];
    if (isNil "_unit") exitWith {};
    if (isNull _unit) exitWith {};
    _unit addEventHandler ["HandleDamage", { diag_log text "[P64] RAW-HD-FIRED" }];
    diag_log text "[P64] RAW-HD-INSTALLED";
}, true, [], true] call CBA_fnc_addClassEventHandler;

diag_log text format ["[P64] ACCEPT FiredBIS=%1 Fired=%2 Explosion=%3 HitPart=%4 HandleDamage=%5 Init=%6 AllVehicles-Init=%7", _okBis, _okLegacy, _okBoom, _okHitPart, _okHd, _okInit, _okAttach];

private _v1 = "B_MRAP_01_F" createVehicle [4600, 4600, 0];
private _v2 = "B_MRAP_01_F" createVehicle [4620, 4600, 0];
diag_log text "[P64] step1 two vehicles created after registration";

// The decisive check for the rewiring: AEE's own per-object installer must
// have attached a real HandleDamage handler to these vehicles. "It
// compiles" is not "it works", and nothing else in the harness can see
// this, because the armour and collision gates filter on the unit being a
// vehicle and no phase damages one.
private _vId1 = (_v1 getVariable ["aee_core_ehId_aee_core_collisionDamage", -1]);
private _vId2 = (_v2 getVariable ["aee_core_ehId_aee_core_collisionDamage", -1]);
private _aId1 = (_v1 getVariable ["aee_core_ehId_aee_armour_penetrationGateHandler", -1]);
diag_log text format ["[P64] INSTALL coreHandleDamage v1=%1 v2=%2 armourHandleDamage v1=%3", _vId1, _vId2, _aId1];
if ((_vId1 >= 0) && {_vId2 >= 0} && {_aId1 >= 0}) then {
    diag_log text "[P64] [PASS] AEE engine handlers are attached to real objects";
} else {
    diag_log text "[P64] [FAIL] AEE engine handlers are NOT attached; the rewiring does not work";
};

// The replace path, which the first version of this probe could not reach.
// The vehicles above are created AFTER registration, so the id variable is
// unset and the remove branch never ran. The 2026-09-29 in-game RPT showed the
// installer applied to the SAME object twice, and the remove branch is where
// the engine rejected the call with "removeeventhandler: Type Number, expected
// Array". Driving the same key twice on one object is the only way to reach it
// here, so the branch is no longer dead in the harness.
private _v1IdBefore = (_v1 getVariable ["aee_core_ehId_aee_core_collisionDamage", -1]);
[_v1, "HandleDamage", { diag_log text "[P64] RAW-HD-REPLACED" }, "collisionDamage"] call aee_lib_fnc_attachObjectEngineHandler;
private _v1IdAfter = (_v1 getVariable ["aee_core_ehId_aee_core_collisionDamage", -1]);
diag_log text format ["[P64] REPLACE before=%1 after=%2", _v1IdBefore, _v1IdAfter];
if ((_v1IdBefore >= 0) && {_v1IdAfter >= 0}) then {
    diag_log text "[P64] [PASS] the installer replaces an existing handler and keeps a live id";
} else {
    diag_log text "[P64] [FAIL] the replace path lost or never set the handler id";
};

[{
    diag_log text "[P64] report complete";
}, [], 5] call CBA_fnc_waitAndExecute;
