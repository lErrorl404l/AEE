// PHASE 124: the terrain symbol size and the map marker palette, asserted on
// the live merged config.
//
// Defect 1: the terrain symbol size is the vanilla engine value, so the
// location icons (CfgLocationTypes) and the map object icons (RscMapControl)
// draw at the size a player expects, not a shrunken one.
//
// Defect 2: every CfgMarkerColors class reaches a scope, so the engine builds
// the marker colour picker (a parentless reopen logs "Updating base class
// 'Default'->''" and drops the scope, and a scope-less class logs "No entry
// .../scope" and "'/' is not a value").  The AEE marker set is registered and
// editor-visible, so the picker is stable, and an arbitrary AEE marker type
// places.
//
// Every fact is engine config, so the probe reads the merged config live.  It
// renders nothing.
//
// Emits [P124] PASS/FAIL lines.

private _pass = 0;
private _fail = 0;
private _notes = [];

// ── DEFECT 1A: the location icon size is the vanilla engine value, expressed
// in the interface scale: "<size> / (safezoneH * 0.7)" is <size> at the Normal
// interface size (safeZoneH 1.42857) and scales with it.  The parentless
// roots (Mount, Name) have no icon; the eight icon classes do. ─────────────
private _iconScale = safeZoneH * 0.7;
private _locationSizes = [
    ["Hill", 14], ["ViewPoint", 16], ["RockArea", 12], ["BorderCrossing", 16],
    ["VegetationBroadleaf", 18], ["VegetationFir", 18],
    ["VegetationPalm", 18], ["VegetationVineyard", 16]
];
{
    _x params ["_cls", "_size"];
    private _got = getNumber (configFile >> "CfgLocationTypes" >> _cls >> "size");
    if (abs (_got - _size / _iconScale) < 0.01) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["location %1 size=%2 want %3", _cls, _got, _size / _iconScale];
    };
} forEach _locationSizes;

// ── DEFECT 1B: the map object icon size is the vanilla ui_f value, expressed
// in the interface scale. ──────────────────────────────────────────────────
private _objectSizes = [
    ["Bush", 7], ["SmallTree", 12], ["Tree", 12], ["Rock", 12],
    ["church", 24], ["Chapel", 24], ["Cross", 24], ["Ruin", 16],
    ["hospital", 24], ["fuelstation", 24], ["Stack", 16],
    ["transmitter", 24], ["watertower", 24], ["lighthouse", 24],
    ["power", 24], ["powersolar", 24], ["powerwind", 24], ["powerwave", 24],
    ["Fountain", 11], ["Tourism", 16], ["ViewTower", 16],
    ["busstop", 24], ["quay", 24], ["Shipwreck", 24],
    ["Bunker", 14], ["Fortress", 16]
];
{
    _x params ["_cls", "_size"];
    private _got = getNumber (configFile >> "RscMapControl" >> _cls >> "size");
    if (abs (_got - _size / _iconScale) < 0.01) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["object %1 size=%2 want %3", _cls, _got, _size / _iconScale];
    };
} forEach _objectSizes;

// ── DEFECT 2A: every CfgMarkerColors class reaches a scope.  The engine reads
// the scope through the Default parent, so a restated parent gives scope=1. ──
private _colours = [
    "ColorAEE", "ColorWEST", "ColorEAST", "ColorGUER", "ColorCIV", "ColorUNKNOWN"
];
{
    private _scope = getNumber (configFile >> "CfgMarkerColors" >> _x >> "scope");
    if (_scope > 0) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["colour %1 scope=%2", _x, _scope];
    };
} forEach _colours;

// ── DEFECT 2B: the AEE marker set is registered and editor-visible, so the
// picker is stable, and an arbitrary AEE marker type places. ────────────────
private _aee = ("true" configClasses (configFile >> "CfgMarkers")) select {
    ((configName _x) select [0, 4]) isEqualTo "AEE_"
};
private _visible = _aee select { getNumber (_x >> "scope") > 0 };
private _count = count _visible;
// The dynamic variation entry adds ONE editor-visible AEE marker
// (aee-dynamic-variation-system); the collapsed count follows the generator.
if (_count == 5613) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["AEE editor-visible markers=%1", _count];
};

private _marker = createMarkerLocal ["aee_p124_marker", [0, 0, 0]];
_marker setMarkerTypeLocal "AEE_b_inf";
if ((markerType _marker) isEqualTo "AEE_b_inf") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["arbitrary marker type read back=%1", markerType _marker];
};
deleteMarkerLocal _marker;

if (_fail == 0) then {
    diag_log text format ["[P124] [PASS] terrain symbol size and marker palette on %1 (%2 checks, AEE markers %3)", worldName, _pass, _count];
} else {
    diag_log text format ["[P124] [FAIL] terrain symbol size and marker palette: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
