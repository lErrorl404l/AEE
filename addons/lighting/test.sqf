#include "script_component.hpp"

/*
lighting component test (aee_diagnostics_fnc_test).

Headless-safe: asserts the merged engine config and compile-time macros only.
It uses no camera, no display and no client-only gate, so a dedicated server
runs it.  Emits CBA-style TEST: OK/FAIL lines and publishes the failure count
to aee_test_failures_lighting.
*/

private _failures = 0;

private _check = {
    params ["_name", "_pass", "_detail"];
    private _line = [
        format ["TEST: OK - %1", _name],
        format ["TEST: FAIL - %1: %2", _name, _detail]
    ] select !_pass;
    diag_log text _line;
    [1, 0] select _pass
};

// ── The resolved world HDR values (config.cpp).  The engine reads HDRNewPars
// and Lighting through the world class chain, so the test reads the resolved
// world config by worldName, not a direct CfgWorlds child. ────────────────
private _world = configFile >> "CfgWorlds" >> worldName;
private _hdr = _world >> "HDRNewPars";
{
    _x params ["_key", "_want"];
    private _got = getNumber (_hdr >> _key);
    _failures = _failures + ([
        "hdr " + _key,
        abs (_got - _want) <= 1e-6,
        format ["%1 want %2", _got, _want]
    ] call _check);
} forEach [
    ["bloomScale", 0.09],
    ["tonemapLinearWhite", 11.2],
    ["nightShiftLuminanceScale", 600]
];

private _starEmissivity = getNumber ((_world >> "Lighting") >> "starEmissivity");
_failures = _failures + ([
    "Lighting starEmissivity",
    _starEmissivity == 25,
    str _starEmissivity
] call _check);

// ── The aurora colours match their cited oxygen emission lines (NOAA SWPC
// Aurora Tutorial): green is G-dominant (557.7 nm O I), red is R-dominant
// (630.0 nm O I).  The values are the AURORA_GREEN/AURORA_RED macros. ─────
private _green = AURORA_GREEN;
private _red = AURORA_RED;
_failures = _failures + ([
    "aurora green G-dominant",
    ((_green select 1) > (_green select 0)) && {(_green select 1) > (_green select 2)},
    str _green
] call _check);
_failures = _failures + ([
    "aurora red R-dominant",
    ((_red select 0) > (_red select 1)) && {(_red select 0) > (_red select 2)},
    str _red
] call _check);

missionNamespace setVariable ["aee_test_failures_lighting", _failures];
diag_log text "[AEE-TEST] lighting DONE";
