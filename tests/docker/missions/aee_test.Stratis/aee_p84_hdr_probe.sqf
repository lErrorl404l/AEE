// PHASE 84: the engine HDR and night-darkness ceiling.
//
// The engine reads CfgWorlds >> HDRNewPars, the world Lighting class and the
// CfgWorlds >> DayLighting* night-darkness endpoints at world load.  A script
// cannot change them at run time.  This probe reads the loaded config and
// asserts the exact values AEE ships.  It renders nothing.

private _hdr = configFile >> "CfgWorlds" >> "HDRNewPars";
private _worldLight = configFile >> "CfgWorlds" >> worldName >> "Lighting";
private _bright = configFile >> "CfgWorlds" >> "DayLightingBrightAlmost";
private _pass = 0;
private _fail = 0;
private _notes = [];

private _bloom = getNumber (_hdr >> "bloomScale");
if (_bloom == 0.09) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["bloomScale %1", _bloom];
};

private _linearWhite = getNumber (_hdr >> "tonemapLinearWhite");
if (_linearWhite == 11.2) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["tonemapLinearWhite %1", _linearWhite];
};

private _nightShift = getNumber (_hdr >> "nightShiftLuminanceScale");
if (_nightShift == 600) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["nightShiftLuminanceScale %1", _nightShift];
};

private _starEmissivity = getNumber (_worldLight >> "starEmissivity");
if (_starEmissivity == 40) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["world %1 starEmissivity %2", worldName, _starEmissivity];
};

private _fullNight = getArray (_bright >> "fullNight");
if ((count _fullNight) == 8) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["fullNight count %1", count _fullNight];
};

private _deepNight = getArray (_bright >> "deepNight");
private _deepFirst = "<empty>";
if ((count _deepNight) > 0) then {
    _deepFirst = _deepNight select 0;
};
if (_deepFirst == -15) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["deepNight first %1", _deepFirst];
};

if (_fail == 0) then {
    diag_log text format ["[P84] [PASS] engine hdr and night ceiling: %1 checks", _pass];
} else {
    diag_log text format ["[P84] [FAIL] engine hdr and night ceiling: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
