#include "script_component.hpp"

/*
symbology component test (aee_diagnostics_fnc_test).

Headless-safe: asserts the merged engine config only.  It uses no camera, no
display and no client-only gate, so a dedicated server runs it.  Emits
CBA-style TEST: OK/FAIL lines and publishes the failure count to
aee_test_failures_symbology.
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

private _markerRoot = configFile >> "CfgMarkers";
private _classRoot = configFile >> "CfgMarkerClasses";

// ── The declared CfgMarkerClasses categories (config.cpp). ────────────────
private _categories = [];
{
    _categories pushBack configName _x;
} forEach ("true" configClasses _classRoot);

// ── A representative AEE marker entry resolves, and its markerClass names a
// declared category. ──────────────────────────────────────────────────────
private _aeeMarkers = [
    "AEE_FA_Friendly_Unit_Aviation_Fixed_Win",
    "AEE_Ech_Squad"
];
{
    private _cfg = _markerRoot >> _x;
    private _class = getText (_cfg >> "markerClass");
    private _icon = getText (_cfg >> "icon");
    private _ok = (isClass _cfg)
        && {(_class isNotEqualTo "") && {_class in _categories}}
        && {(_icon find "z\aee\addons\symbology\data\markers") >= 0};
    _failures = _failures + (["marker " + _x, _ok, format ["markerClass=%1 icon=%2", _class, _icon]] call _check);
} forEach _aeeMarkers;

// ── Every engine marker family AEE re-points draws an AEE .paa. ───────────
private _repointed = [
    "b_inf", "b_mech_inf", "o_naval", "n_installation", "c_car",
    "hd_dot", "hd_ambush", "mil_destroy", "mil_dot",
    "Contact_arrow1", "Contact_art1",
    "GroundSupport_CAS_WEST", "GroundSupport_ARTY_EAST",
    "group_0", "group_11", "respawn_inf", "waypoint"
];
{
    private _icon = getText (_markerRoot >> _x >> "icon");
    _failures = _failures + ([
        "repointed " + _x,
        (_icon find "z\aee\addons\symbology\data\markers") >= 0,
        _icon
    ] call _check);
} forEach _repointed;

// The invisible marker must stay vanilla.
private _emptyIcon = getText (_markerRoot >> "Empty" >> "icon");
_failures = _failures + ([
    "Empty stays invisible",
    (_emptyIcon find "z\aee\addons\symbology\data\markers") < 0,
    _emptyIcon
] call _check);

// ── The CfgMarkerColors classes reach a scope. ────────────────────────────
private _colourRoot = configFile >> "CfgMarkerColors";
{
    private _cfg = _colourRoot >> _x;
    private _rgba = getArray (_cfg >> "color");
    private _ok = (isClass _cfg)
        && {(_rgba isEqualType []) && {(count _rgba) == 4}}
        && {(getNumber (_cfg >> "scope")) >= 0};
    _failures = _failures + (["marker colour " + _x, _ok, format ["scope=%1 color=%2", getNumber (_cfg >> "scope"), _rgba]] call _check);
} forEach ["ColorAEE", "ColorWEST", "ColorEAST", "ColorGUER", "ColorCIV", "ColorUNKNOWN"];

// ColorAEE carries an explicit scope and is white (the texture owns the colour).
private _aeeColour = _colourRoot >> "ColorAEE";
_failures = _failures + ([
    "ColorAEE neutral and scoped",
    ((getNumber (_aeeColour >> "scope")) == 1) && {(getArray (_aeeColour >> "color")) isEqualTo [1, 1, 1, 1]},
    format ["scope=%1 color=%2", getNumber (_aeeColour >> "scope"), getArray (_aeeColour >> "color")]
] call _check);

missionNamespace setVariable ["aee_test_failures_symbology", _failures];
diag_log text "[AEE-TEST] symbology DONE";
