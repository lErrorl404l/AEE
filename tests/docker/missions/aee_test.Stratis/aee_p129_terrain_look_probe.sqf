// PHASE 129: the map terrain look on the live world.
//
// The palette, the height label size and the icon sizes are load-time config
// re-declares, so the probe reads the MERGED config (configFile) and confirms
// the operator's four terrain-look defects reached it: the contours are
// darker, the vegetation reads, the height label is larger, and the icon
// sizes are expressed in the user's interface scale.  It renders nothing.
//
// The icon `size` is "<base> / (safezoneH * 0.7)": the base at the Normal
// interface size (safeZoneH 1.42857) and linearly larger with the interface
// size, because safeZoneH = 1/uiScale (BIKI Pixel Grid System).  The probe
// recomputes the expected value from the live safeZoneH, so it holds at any
// interface size the server reports.
//
// Emits one [P129] PASS/FAIL line.

private _pass = 0;
private _fail = 0;
private _notes = [];

private _rsc = configFile >> "RscMapControl";

// 1-4. the darkened contours and the readable vegetation fills
private _palette = [
    ["colorMainCountlines", [0.45, 0.26, 0.12, 1]],
    ["colorCountlines", [0.62, 0.42, 0.22, 1]],
    ["colorForest", [0.55, 0.74, 0.44, 1]],
    ["colorForestTextured", [0.45, 0.66, 0.34, 0.3]]
];
{
    _x params ["_field", "_want"];
    private _got = getArray (_rsc >> _field);
    private _ok = ((count _got) == 4);
    if (_ok) then {
        {
            if (abs ((_got select _forEachIndex) - _x) > 0.001) then { _ok = false; };
        } forEach _want;
    };
    if (_ok) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["%1=%2 want %3", _field, str _got, str _want];
    };
} forEach _palette;

// 5. the contour height (level) label size is raised above the vanilla 0.02
private _level = getNumber (_rsc >> "sizeExLevel");
if (_level >= 0.03) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["sizeExLevel=%1", _level];
};

// 6. the icon sizes scale with the interface size.  safeZoneH = 1/uiScale, so
// the base is the size at safeZoneH * 0.7 == 1 (the Normal interface size).
private _scale = safeZoneH * 0.7;
private _icons = [
    [configFile >> "CfgLocationTypes", "Hill", 14],
    [configFile >> "CfgLocationTypes", "ViewPoint", 16],
    [configFile >> "CfgLocationTypes", "RockArea", 12],
    [configFile >> "CfgLocationTypes", "VegetationBroadleaf", 18],
    [configFile >> "RscMapControl", "church", 24],
    [configFile >> "RscMapControl", "Bush", 7],
    [configFile >> "RscMapControl", "Rock", 12]
];
{
    _x params ["_cfg", "_cls", "_base"];
    private _got = getNumber (_cfg >> _cls >> "size");
    private _want = _base / _scale;
    if (abs (_got - _want) < 0.01) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["%1.size=%2 want %3 (base %4 scale %5)", _cls, _got, _want, _base, _scale];
    };
} forEach _icons;

diag_log text format ["[P129] DIAG safeZoneH=%1 uiScale=%2 sizeExNames=%3", safeZoneH, (getResolution select 5), getNumber (_rsc >> "sizeExNames")];

if (_fail == 0) then {
    diag_log text format ["[P129] [PASS] terrain look on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P129] [FAIL] terrain look: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
