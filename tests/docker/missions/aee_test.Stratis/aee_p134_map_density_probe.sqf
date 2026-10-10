// PHASE 134: the map density constants, asserted on the live merged config.
//
// The 2D map is a live per-frame render: CStaticMap::OnDraw rebuilds the
// terrain composite every frame (DrawBackground -> DrawSea / DrawField /
// DrawCountlines / DrawForests / DrawRoads / DrawObjects).  The ptsPerSquare*
// constants stride those per-cell loops: iStep = ceil(pts * invPtsLand), and
// the loop advances by xStep = iStep * invLandRange * invScaleX, so a HIGHER
// value is a LARGER stride and FEWER per-frame draw calls.  (Source:
// BohemiaInteractive/CWR engine/Poseidon/UI/Map/UIMap.cpp, DrawBackground
// lines 743-998.)
//
// The shipped RscMapControl is declared twice: the Dta/bin.pbo core default
// (Sea 6 Txt 8 CLn 8 Exp 8 Cost 8 For 4 ForEdge 10 Road 2 Obj 10) and the
// Addons/ui_f.pbo re-declare, which loads later and WINS (last-loaded-wins,
// engine-config-surface.md section 2.4).  AEE re-declares the ui_f values, so
// AEE is at the shipped vanilla parity, not above it.  This probe reads the
// merged config and asserts that parity, and that the engine grid stays off.
// It renders nothing.
//
// Emits one [P134] PASS/FAIL line.

private _pass = 0;
private _fail = 0;
private _notes = [];

private _rsc = configFile >> "RscMapControl";

// The shipped ui_f.pbo RscMapControl values, the winning definition.
private _vanilla = [
    ["ptsPerSquareSea", 5],
    ["ptsPerSquareTxt", 20],
    ["ptsPerSquareCLn", 10],
    ["ptsPerSquareExp", 10],
    ["ptsPerSquareCost", 10],
    ["ptsPerSquareFor", 9],
    ["ptsPerSquareForEdge", 9],
    ["ptsPerSquareRoad", 6],
    ["ptsPerSquareObj", 9]
];
{
    _x params ["_key", "_want"];
    private _got = getNumber (_rsc >> _key);
    if (_got == _want) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["RscMapControl %1 = %2 (ui_f vanilla %3)", _key, _got, _want];
    };
} forEach _vanilla;

// The AEE zoom range and the density LOD and simple variants.  AEE sets
// these; the base ui_f RscMapControl leaves the density fields unset.
// scaleMax is AEE's own (double the vanilla 1); scaleDefault is the engine
// strategic-map scale; the density fields are the engine Eden ctrlMap and
// minimap values.
private _levers = [
    ["scaleMax", 2],
    ["scaleDefault", 0.3],
    ["ptsPerSquareForLod1", 4],
    ["ptsPerSquareForLod2", 1],
    ["ptsPerSquareMainRoad", 6],
    ["ptsPerSquareMainRoadSimple", 1],
    ["ptsPerSquareRoadSimple", 1],
    ["ptsPerSquareObjLod1", 2]
];
{
    _x params ["_key", "_want"];
    private _got = getNumber (_rsc >> _key);
    if (_got == _want) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["RscMapControl %1 = %2 (AEE %3)", _key, _got, _want];
    };
} forEach _levers;

// The engine grid is off: both colour fields carry alpha 0, which removes the
// whole DrawGrid pass (CStaticMap::DrawGrid, UIMap.cpp 1971-2042).
{
    private _a = (getArray (_rsc >> _x)) param [3, -1];
    if (_a == 0) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["RscMapControl %1 alpha = %2 (want 0)", _x, _a];
    };
} forEach ["colorGrid", "colorGridMap"];

// The object-layer gate.  drawObjects is an Arma 3 field (the token is present
// in arma3_x64.exe and arma3server_x64.exe; it is ABSENT from the CWR ancestor
// source, where the object layer is gated only by ptsLand >= ptsPerSquareObj).
// The shipped config sets it only on the strategic map (0) and AEE's thermal
// mask sets 0, both controls that must not draw scenery objects.  The base
// RscMapControl does not carry the field, so it keeps the engine default.
// Report the resolved values for the record; the gate itself is client-only.
private _drawObjects = if (isNumber (_rsc >> "drawObjects")) then {
    getNumber (_rsc >> "drawObjects")
} else {
    -1
};
private _strategicCfg = configFile >> "RscDisplayStrategicMap" >> "controlsBackground" >> "Map";
private _strategicDraw = if (isNumber (_strategicCfg >> "drawObjects")) then {
    getNumber (_strategicCfg >> "drawObjects")
} else {
    -1
};

diag_log text format ["[P134] map density: Txt=%1 CLn=%2 For=%3 ForEdge=%4 Road=%5 Obj=%6 Sea=%7 Exp=%8 Cost=%9 grid=%10/%11 drawObjects=%12 strategicDrawObjects=%13",
    getNumber (_rsc >> "ptsPerSquareTxt"),
    getNumber (_rsc >> "ptsPerSquareCLn"),
    getNumber (_rsc >> "ptsPerSquareFor"),
    getNumber (_rsc >> "ptsPerSquareForEdge"),
    getNumber (_rsc >> "ptsPerSquareRoad"),
    getNumber (_rsc >> "ptsPerSquareObj"),
    getNumber (_rsc >> "ptsPerSquareSea"),
    getNumber (_rsc >> "ptsPerSquareExp"),
    getNumber (_rsc >> "ptsPerSquareCost"),
    (getArray (_rsc >> "colorGrid")) param [3, -1],
    (getArray (_rsc >> "colorGridMap")) param [3, -1],
    _drawObjects,
    _strategicDraw
];

diag_log text format ["[P134] map levers: scaleMax=%1 scaleDefault=%2 ForLod1=%3 ForLod2=%4 MainRoad=%5 MainRoadSimple=%6 RoadSimple=%7 ObjLod1=%8",
    getNumber (_rsc >> "scaleMax"),
    getNumber (_rsc >> "scaleDefault"),
    getNumber (_rsc >> "ptsPerSquareForLod1"),
    getNumber (_rsc >> "ptsPerSquareForLod2"),
    getNumber (_rsc >> "ptsPerSquareMainRoad"),
    getNumber (_rsc >> "ptsPerSquareMainRoadSimple"),
    getNumber (_rsc >> "ptsPerSquareRoadSimple"),
    getNumber (_rsc >> "ptsPerSquareObjLod1")
];

if (_fail == 0) then {
    diag_log text format ["[P134] [PASS] map density constants match the shipped ui_f vanilla (%1 checks)", _pass];
} else {
    diag_log text format ["[P134] [FAIL] map density constants: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
