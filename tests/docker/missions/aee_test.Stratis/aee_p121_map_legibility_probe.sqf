// PHASE 121: the map legibility fixes, asserted on the live merged config.
//
// The location-class inheritance, the object-icon class names and the grid
// fields are all engine config, so this probe reads the merged config live.
// The MGRS line contrast is locked in source by tools/tests/test_terrain.py
// (TestTerrainMgrsContrast); this probe proves the config half.  It renders
// nothing.
//
// Emits [P121] PASS/FAIL lines.

private _pass = 0;
private _fail = 0;
private _notes = [];

// ── DEFECT A: every re-declared CfgLocationTypes class restates its vanilla
// parent, so drawStyle survives.  The parents come from the engine core
// (Dta/bin.pbo) and ui_f.  A bare reopen loses drawStyle, texture, size and
// the rest, and the engine logs "No entry .../drawStyle" and
// "Wrong location draw style". ─────────────────────────────────────────────
private _parents = [
    ["Strategic", "Name"],
    ["StrongpointArea", "Strategic"],
    ["FlatArea", "Strategic"],
    ["FlatAreaCity", "FlatArea"],
    ["FlatAreaCitySmall", "FlatAreaCity"],
    ["CityCenter", "Strategic"],
    ["Airport", "Strategic"],
    ["NameMarine", "Name"],
    ["NameCityCapital", "Name"],
    ["NameCity", "Name"],
    ["NameVillage", "Name"],
    ["NameLocal", "Name"],
    ["Hill", "Name"],
    ["ViewPoint", "Hill"],
    ["RockArea", "Hill"],
    ["BorderCrossing", "Hill"],
    ["VegetationBroadleaf", "Hill"],
    ["VegetationFir", "Hill"],
    ["VegetationPalm", "Hill"],
    ["VegetationVineyard", "Hill"],
    ["fakeTown", "Name"],
    ["Flag", "Hill"]
];
{
    _x params ["_cls", "_parent"];
    private _cfg = configFile >> "CfgLocationTypes" >> _cls;
    private _style = getText (_cfg >> "drawStyle");
    private _base = getText (_cfg >> "texture");
    if ((_style isNotEqualTo "") && {!isNil "_base"}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["%1 lost its parent %2 (drawStyle=%3)", _cls, _parent, _style];
    };
} forEach _parents;

// The three parentless roots carry a drawStyle of their own.
{
    private _style = getText (configFile >> "CfgLocationTypes" >> _x >> "drawStyle");
    if (_style isNotEqualTo "") then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["root %1 lost its own drawStyle", _x];
    };
} forEach ["Mount", "Name", "Area"];

// ── DEFECT B: the water-tower and radio-mast map objects.  The engine declares
// the RscMapControl object icon classes in two case-distinct name sets, the
// core Dta/bin.pbo set (Church, Transmitter, Watertower ...) and the ui_f set
// (church, transmitter, watertower ...).  AEE must re-texture BOTH. ─────────
private _objects = [
    // engine core set
    "Church", "Lighthouse", "Quay", "Fuelstation", "Hospital", "BusStop",
    "Transmitter", "Watertower",
    // ui_f set
    "church", "lighthouse", "quay", "fuelstation", "hospital", "busstop",
    "transmitter", "watertower",
    // shared-case set
    "Bush", "Rock", "SmallTree", "Tree", "Cross", "Chapel", "Shipwreck",
    "Bunker", "Fortress", "Fountain", "Ruin", "Stack", "Tourism", "ViewTower"
];
{
    private _icon = getText (configFile >> "RscMapControl" >> _x >> "icon");
    if ((_icon find "z\aee\addons\optics\data\terrain") >= 0) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["object %1 not AEE-textured: %2", _x, _icon];
    };
} forEach _objects;

// ── DEFECT C: the readable grid reference.  The engine grid colours are SPLIT:
// colorGrid is the edge-number colour and colorGridMap the in-map line colour
// (engine source: the open-sourced Poseidon engine, UIMap.cpp,
// CStaticMap::DrawGrid).  The engine NUMBERS return (colorGrid alpha > 0, the
// engine default sizeExGrid 0.04) and the engine LINES stay off (colorGridMap
// alpha 0), so exactly one line grid is drawn (the AEE MGRS overlay). ───────
private _gridTargets = [
    ["RscMapControl", configFile >> "RscMapControl"],
    ["RscDisplayStrategicMap.Map", configFile >> "RscDisplayStrategicMap" >> "controlsBackground" >> "Map"],
    ["ctrlMap", configFile >> "ctrlMap"]
];
{
    _x params ["_label", "_cfg"];
    private _numbers = getArray (_cfg >> "colorGrid");
    private _lines = getArray (_cfg >> "colorGridMap");
    private _size = getNumber (_cfg >> "sizeExGrid");
    private _numbersOn = ((count _numbers) >= 4) && {(_numbers select 3) > 0.5};
    private _linesOff = ((count _lines) >= 4) && {(_lines select 3) == 0};
    if (_numbersOn && {_linesOff} && {_size >= 0.04}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["grid %1: colorGrid=%2 colorGridMap=%3 sizeExGrid=%4", _label, str _numbers, str _lines, _size];
    };
} forEach _gridTargets;

// ── DEFECT D: the adopted map-surface levers.  maxSatelliteAlpha (Map Contour
// idea) and drawShaded (Enhanced Map idea) reach the RscMapControl surface. ──
private _alpha = getNumber (configFile >> "RscMapControl" >> "maxSatelliteAlpha");
if ((_alpha > 0.35) && {_alpha <= 1}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["maxSatelliteAlpha=%1", _alpha];
};
private _shaded = getNumber (configFile >> "RscMapControl" >> "drawShaded");
if (_shaded > 0) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["drawShaded=%1", _shaded];
};

// ── DEFECT E: the full topographic render surface is set.  Water, relief
// bands, contours, vegetation and rock tints, and the densities. ───────────
private _renderColours = [
    "colorBackground", "colorOutside", "colorInactive", "colorSea",
    "colorMainCountlinesWater", "colorCountlinesWater", "colorLevels",
    "colorMainCountlines", "colorCountlines", "colorForest",
    "colorForestBorder", "colorForestTextured", "colorRocks",
    "colorRocksBorder", "colorNames"
];
{
    if ((count (getArray (configFile >> "RscMapControl" >> _x))) >= 4) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["render colour %1 missing", _x];
    };
} forEach _renderColours;
{
    private _v = getNumber (configFile >> "RscMapControl" >> _x);
    if (_v > 0) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["render scalar %1=%2", _x, _v];
    };
} forEach [
    "ptsPerSquareSea", "ptsPerSquareCLn", "ptsPerSquareFor",
    "ptsPerSquareRoad", "ptsPerSquareTxt", "ptsPerSquareObj",
    "sizeExLevel", "widthRailWay", "shadedSea", "drawShaded"
];
if ((getText (configFile >> "RscMapControl" >> "fontLevel")) isNotEqualTo "") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "fontLevel is empty";
};

// ── DEFECT F: the object classes keep the vanilla visibility coefficients,
// which the parentless classes cannot inherit. ─────────────────────────────
{
    private _min = getNumber (configFile >> "RscMapControl" >> _x >> "coefMin");
    private _max = getNumber (configFile >> "RscMapControl" >> _x >> "coefMax");
    if ((_min > 0) && {_max > 0} && {_max >= _min}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["coef %1=%2/%3", _x, _min, _max];
    };
} forEach ["watertower", "transmitter", "church", "lighthouse", "hospital"];

// The AEE MGRS overlay is compiled, so the single line grid is present.
if (!isNil "aee_optics_fnc_mgrsMapDraw") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "aee_optics_fnc_mgrsMapDraw not compiled";
};

if (_fail == 0) then {
    diag_log text format ["[P121] [PASS] map legibility on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P121] [FAIL] map legibility: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
