// PHASE 84: the engine HDR and night-darkness anchor, resolved per world.
//
// A direct CfgWorlds child is an unreferenced sibling and inert.  The engine
// reads HDRNewPars, DOFPars, Lighting and the DayLighting keyframes through the
// world class chain (CfgWorlds >> DefaultWorld >> CAWorld >> <World>:CAWorld).
// This probe reads the RESOLVED world config via worldName, so it proves AEE's
// values reached the engine's class chain, not an inert sibling.  It renders
// nothing.

private _world = configFile >> "CfgWorlds" >> worldName;
private _hdr = _world >> "HDRNewPars";
private _lighting = _world >> "Lighting";
private _bright = _world >> "DayLightingBrightAlmost";
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

private _starEmissivity = getNumber (_lighting >> "starEmissivity");
if (_starEmissivity == 25) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["%1 Lighting starEmissivity %2", worldName, _starEmissivity];
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
    diag_log text format ["[P84] [PASS] %1 engine hdr and night ceiling: %2 checks", worldName, _pass];
} else {
    diag_log text format ["[P84] [FAIL] %1 engine hdr and night ceiling: %2 passed, %3 failed: %4", worldName, _pass, _fail, str _notes];
};
