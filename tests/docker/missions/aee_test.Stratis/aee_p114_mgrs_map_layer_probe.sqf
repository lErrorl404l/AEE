// PHASE 114: the MGRS map-layer font fallback and the precision rule, live.
//
// The map control and the cursor exist only on a client, so this drives the
// REAL pure kernels with the live anchor: the font resolver, the precision
// kernel, the grid planner and the cursor formatter.  It also reads the live
// config, because the root cause was a CfgFontFamilies family whose glyph
// files are absent: the engine draws no text for it, so the config must not
// point an engine surface at it.
//
// Emits [P114] PASS/FAIL lines.

private _fnFont = missionNamespace getVariable ["aee_cartography_fnc_mgrsFontFamily", nil];
private _fnUsable = missionNamespace getVariable ["aee_cartography_fnc_fontFamilyUsable", nil];
private _fnPrec = missionNamespace getVariable ["aee_cartography_fnc_mgrsMapPrecision", nil];
private _fnGrid = missionNamespace getVariable ["aee_cartography_fnc_mgrsGridLines", nil];
private _fnCursor = missionNamespace getVariable ["aee_cartography_fnc_mgrsCursorText", nil];
private _fnMarker = missionNamespace getVariable ["aee_cartography_fnc_mgrsMarkerText", nil];
private _fnAnchor = missionNamespace getVariable ["aee_lib_fnc_getGeoAnchor", nil];
if (isNil "_fnFont" || {isNil "_fnUsable"} || {isNil "_fnPrec"} || {isNil "_fnGrid"}
    || {isNil "_fnCursor"} || {isNil "_fnMarker"} || {isNil "_fnAnchor"}) exitWith {
    diag_log text "[P114] [FAIL] MGRS map-layer kernels not compiled";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// 1. the AEE glyph files are absent, so the family is NOT usable.
private _aeeUsable = ["AEEFontMono"] call _fnUsable;
if (!_aeeUsable) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "AEEFontMono reports usable although its glyph files are absent";
};

// 2. the overlay font resolves to a family whose glyph files exist.
private _mono = [true] call _fnFont;
private _monoUsable = [_mono] call _fnUsable;
if (_monoUsable) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["overlay font %1 is not usable", _mono];
};

// 3. the engine map grid font is not the glyphless family.
private _cfgFont = getText (configFile >> "RscMapControl" >> "fontGrid");
if (_cfgFont != "AEEFont") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "RscMapControl fontGrid is still the glyphless AEEFont";
};

// 4. the precision follows the world size (no view) and the displayed scale.
private _small = [8192, 0] call _fnPrec;
private _large = [30720, 0] call _fnPrec;
private _zoomed = [30720, 2048] call _fnPrec;
private _wide = [30720, 8192] call _fnPrec;
if ((_small select 0) == 6 && {(_small select 1) == 100}
    && {(_large select 0) == 8} && {(_large select 1) == 10}
    && {(_zoomed select 0) == 8} && {(_wide select 0) == 6}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["precision rule: small=%1 large=%2 zoomed=%3 wide=%4",
        str _small, str _large, str _zoomed, str _wide];
};

// 5. the grid planner produces labels whose length matches the interval.
private _anchor = call _fnAnchor;
private _mapSize = _anchor select 3;
if (_mapSize <= 0) then { _mapSize = 8192; };
private _centre = [_mapSize / 2, _mapSize / 2, 0];
private _half = 500;
private _rect = [
    (_centre select 0) - _half,
    (_centre select 1) - _half,
    (_centre select 0) + _half,
    (_centre select 1) + _half
];
private _plan = [_anchor, _rect, 0] call _fnGrid;
_plan params ["_segments", "_labels", "_interval"];
private _perAxis = 0;
if (_interval > 0) then { _perAxis = round (5 - (log _interval)); };
private _labelsOk = ((count _labels) > 0) && {_interval > 0} && {_perAxis >= 1};
private _lenOk = _labelsOk;
{
    _x params ["_pos", "_text", "_major"];
    if (!(_text isEqualType "") || {_text == ""} || {(_text select [0, _perAxis]) != _text}) then {
        _lenOk = false;
    };
} forEach _labels;
if (_labelsOk && {_lenOk}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["grid labels: count=%1 interval=%2 perAxis=%3",
        count _labels, _interval, _perAxis];
};

// 6. the cursor readout carries the MGRS reference, not the engine grid.
private _written = ["", _centre, _anchor, (_small select 0)] call _fnMarker;
private _cursor = [_written, 123] call _fnCursor;
if ((_cursor find " m") >= 0 && {(_written == "") || {(_cursor find _written) >= 0}}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["cursor readout unexpected: %1", _cursor];
};

diag_log text format ["[P114] font: aeeUsable=%1 overlay=%2 gridFont=%3; precision small=%4 large=%5; grid interval=%6 labels=%7; cursor='%8'",
    _aeeUsable, _mono, _cfgFont, str _small, str _large, _interval, count _labels, _cursor];

if (_fail == 0) then {
    diag_log text format ["[P114] [PASS] MGRS map layer on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P114] [FAIL] MGRS map layer: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
