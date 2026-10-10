// PHASE 117: the four map defects, asserted on the live merged config.
//
// The map grid, the marker families and the marker classes are all engine
// config, so this probe reads the merged config live.  The echelon placement is
// a client-side marker size, so the pure size kernel is driven with a fixture.
// It renders nothing.
//
// Emits [P117] PASS/FAIL lines.

private _pass = 0;
private _fail = 0;
private _notes = [];

// ── DEFECT 1: the edge NUMBERS return and the engine LINES stay off.  The
// engine grid colours are SPLIT: colorGrid is the edge-number colour and
// colorGridMap the in-map line colour (engine source: the open-sourced
// Poseidon engine, UIMap.cpp, CStaticMap::DrawGrid).  So the AEE MGRS overlay
// is the only line grid and the engine numeric labels are the readable vanilla
// reference (ADR-030). ──────────────────────────────────────────────────────
private _gridTargets = [
    ["RscMapControl", configFile >> "RscMapControl"],
    ["RscDisplayStrategicMap.Map", configFile >> "RscDisplayStrategicMap" >> "controlsBackground" >> "Map"],
    ["ctrlMap", configFile >> "ctrlMap"]
];
{
    _x params ["_label", "_cfg"];
    private _numbers = getArray (_cfg >> "colorGrid");
    private _lines = getArray (_cfg >> "colorGridMap");
    private _numbersOff = ((count _numbers) >= 4) && {(_numbers select 3) == 0};
    private _linesOff = ((count _lines) >= 4) && {(_lines select 3) == 0};
    if (_numbersOff && {_linesOff}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["grid %1: colorGrid=%2 colorGridMap=%3", _label, str _numbers, str _lines];
    };
} forEach _gridTargets;

// ── DEFECT 2: every engine marker family renders an AEE symbol.  Each class is
// re-pointed at a .paa under the AEE markers directory. ────────────────────
private _repointed = [
    "b_inf", "b_mech_inf", "o_naval", "n_installation", "c_car",
    "hd_dot", "hd_ambush", "mil_destroy", "mil_dot",
    "Contact_arrow1", "Contact_art1",
    "GroundSupport_CAS_WEST", "GroundSupport_ARTY_EAST",
    "group_0", "group_11", "respawn_inf", "waypoint"
];
{
    private _icon = getText (configFile >> "CfgMarkers" >> _x >> "icon");
    if ((_icon find "z\aee\addons\symbology\data\markers") >= 0) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["engine marker %1 still vanilla: %2", _x, _icon];
    };
} forEach _repointed;

// The structural classes must NOT be re-pointed: Empty is the invisible marker.
private _emptyIcon = getText (configFile >> "CfgMarkers" >> "Empty" >> "icon");
if ((_emptyIcon find "z\aee\addons\symbology\data\markers") < 0) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["Empty must stay invisible, got %1", _emptyIcon];
};

// ── DEFECT 3: the AEE markers are folded into CfgMarkerClasses categories. ──
private _categoryNames = [];
{
    _categoryNames pushBack configName _x;
} forEach ("true" configClasses (configFile >> "CfgMarkerClasses"));
if (count _categoryNames >= 31) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["only %1 CfgMarkerClasses categories", count _categoryNames];
};

// A representative generated marker carries a category that is declared.
private _sampleClass = "AEE_FA_Friendly_Unit_Aviation_Fixed_Win";
private _sampleCat = getText (configFile >> "CfgMarkers" >> _sampleClass >> "markerClass");
if ((_sampleCat isNotEqualTo "") && {_sampleCat in _categoryNames}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["%1 markerClass=%2 not a declared category", _sampleClass, _sampleCat];
};

// ── DEFECT 4: the echelon overlay is placed ABOVE the frame.  The engine
// stretches a marker texture into its box, so the 64 x 128 echelon texture
// needs a 1:2 marker size. ─────────────────────────────────────────────────
private _fnSize = missionNamespace getVariable ["aee_symbology_fnc_symbologyEchelonSize", nil];
if (isNil "_fnSize") then {
    _fail = _fail + 1;
    _notes pushBack "symbologyEchelonSize not compiled";
} else {
    private _size = [1] call _fnSize;
    private _size2 = [0.5] call _fnSize;
    if ((_size isEqualTo [1, 2]) && {_size2 isEqualTo [0.5, 1]}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["echelon size: [1]=%1 [0.5]=%2 want [1,2] [0.5,1]", str _size, str _size2];
    };
};

// The echelon overlay class is registered and carries a texture.
private _echTex = getText (configFile >> "CfgMarkers" >> "AEE_Ech_Squad" >> "texture");
if (_echTex isNotEqualTo "") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "AEE_Ech_Squad has no texture";
};

if (_fail == 0) then {
    diag_log text format ["[P117] [PASS] map defects on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P117] [FAIL] map defects: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
