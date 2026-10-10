// PHASE 128: the engine cursor tooltip is neutralised and the AEE edge ruler is
// complete at all four edges.  Both are measurable headless: the tooltip's Info
// colour is merged config, and the ruler is a pure kernel.  The engine's own
// edge ruler (CStaticMap::DrawGrid) clips its northing numbers at close zoom
// and AEE cannot change it, so the ruler completeness is asserted on the AEE
// plan.  It renders nothing.
//
// Emits [P128] PASS/FAIL lines.

private _pass = 0;
private _fail = 0;
private _notes = [];

// ── The engine cursor tooltip is neutralised: Info text and backdrop alpha 0. ─
private _tip = configFile >> "RscMapControlTooltip";
private _infoText = getArray (_tip >> "Controls" >> "Info" >> "colorText");
private _infoBg = getArray (_tip >> "Controls" >> "InfoBackground" >> "colorBackground");
private _textOff = ((count _infoText) >= 4) && {(_infoText select 3) == 0};
private _bgOff = ((count _infoBg) >= 4) && {(_infoBg select 3) == 0};
if (_textOff && {_bgOff}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["tooltip not neutralised: colorText=%1 colorBackground=%2", str _infoText, str _infoBg];
};

// ── The file-root forward declarations must not empty the engine UI classes. ──
private _rstColor = getArray (configFile >> "RscStructuredText" >> "colorText");
if ((count _rstColor) >= 4) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["RscStructuredText emptied: colorText=%1", str _rstColor];
};

// ── Both engine grid fields are off; AEE owns the single complete ruler. ──────
private _map = configFile >> "RscMapControl";
private _grid = getArray (_map >> "colorGrid");
private _gridMap = getArray (_map >> "colorGridMap");
if (((count _grid) >= 4) && {(_grid select 3) == 0} && {(count _gridMap) >= 4} && {(_gridMap select 3) == 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["engine grid: colorGrid=%1 colorGridMap=%2", str _grid, str _gridMap];
};

// ── The overlay kernels are compiled. ────────────────────────────────────────
{
    if (isNil _x) then {
        _fail = _fail + 1;
        _notes pushBack (_x + " not compiled");
    } else {
        _pass = _pass + 1;
    };
} forEach ["aee_cartography_fnc_mgrsMapDraw", "aee_cartography_fnc_mgrsGridLines"];

// ── The ruler is complete: every line is labelled at both ends. ──────────────
private _anchor = call aee_lib_fnc_getGeoAnchor;
if ((count _anchor) >= 9) then {
    private _c = (_anchor select 3) / 2;
    private _rect = [_c - 1000, _c - 1000, _c + 1000, _c + 1000];
    private _plan = [_anchor, _rect, 100] call aee_cartography_fnc_mgrsGridLines;
    _plan params ["_segments", "_labels", "_interval"];
    private _segCount = count _segments;
    private _labCount = count _labels;
    if ((_segCount > 4) && {_labCount == (2 * _segCount)}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["ruler labels=%1 segments=%2 interval=%3", _labCount, _segCount, _interval];
    };

    // Each line endpoint carries a label, so the easting reads top and bottom
    // and the northing left and right.
    private _ends = [];
    {
        private _p = _x select 0;
        _ends pushBack [round (_p select 0), round (_p select 1)];
    } forEach _labels;
    private _unlabelled = 0;
    {
        _x params ["_a", "_b"];
        {
            if !([round (_x select 0), round (_x select 1)] in _ends) then {
                _unlabelled = _unlabelled + 1;
            };
        } forEach [_a, _b];
    } forEach _segments;
    if (_unlabelled == 0) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["ruler: %1 line ends unlabelled", _unlabelled];
    };
} else {
    _fail = _fail + 1;
    _notes pushBack "no geo anchor";
};

if (_fail == 0) then {
    diag_log text format ["[P128] [PASS] map cursor tooltip neutralised and edge ruler complete on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P128] [FAIL] map cursor and ruler: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
