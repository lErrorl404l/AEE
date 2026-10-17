#include "script_component.hpp"

/*
thermal_display component test (aee_diagnostics_fnc_test).

Headless-safe: asserts the merged engine config and pure kernels only.  It uses
no camera, no display and no client-only gate, so a dedicated server runs it.
Emits CBA-style TEST: OK/FAIL lines and publishes the failure count to
aee_test_failures_thermal_display.
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

// ── The display classes AEE declares in RscTitles.hpp, read live. ─────────
private _titles = configFile >> "RscTitles";
{
    _x params ["_class", "_idd"];
    private _cfg = _titles >> _class;
    private _got = getNumber (_cfg >> "idd");
    _failures = _failures + ([
        "display " + _class,
        (isClass _cfg) && _got == _idd,
        format ["idd %1 want %2", _got, _idd]
    ] call _check);
} forEach [
    ["aee_thermal_display_fusionOutline", 10780],
    ["aee_thermal_display_fusionFrame", 10779],
    ["aee_thermal_display_fusionHud", 10782]
];

// The outline canvas is a Draw surface, not a panel: fully transparent.
private _canvas = _titles >> "aee_thermal_display_fusionOutline" >> "controls" >> "AEEOutlineCanvas";
private _bg = getArray (_canvas >> "colorBackground");
_failures = _failures + ([
    "outline canvas transparent",
    (isClass _canvas) && {(_bg isEqualType []) && {(count _bg) == 4} && {(_bg select 3) == 0}},
    str _bg
] call _check);

// ── The ember palette kernel (fnc_thermalPalette), driven at its documented
// control points. ─────────────────────────────────────────────────────────
private _fnPalette = missionNamespace getVariable ["aee_thermal_display_fnc_thermalPalette", nil];
_failures = _failures + ([
    "thermalPalette compiled",
    !isNil "_fnPalette",
    "aee_thermal_display_fnc_thermalPalette not compiled"
] call _check);
if (!isNil "_fnPalette") then {
    private _cold = [0] call _fnPalette;
    _failures = _failures + (["palette 0 black", _cold isEqualTo [0, 0, 0], str _cold] call _check);
    private _vehicle = [0.55] call _fnPalette;
    _failures = _failures + ([
        "palette 0.55 vehicle hue",
        (abs ((_vehicle select 0) - 0.5686) < 1e-3) && {(abs ((_vehicle select 1) - 0.1804) < 1e-3)} && {(_vehicle select 2) == 0},
        str _vehicle
    ] call _check);
    private _white = [1] call _fnPalette;
    _failures = _failures + (["palette 1 white", _white isEqualTo [1, 1, 1], str _white] call _check);
};

// ── The fusion band ladder (fnc_fusionMaterialPaths): 256 ordered paths,
// index 0 the darkest through 255 the brightest. ──────────────────────────
private _fnPaths = missionNamespace getVariable ["aee_thermal_display_fnc_fusionMaterialPaths", nil];
_failures = _failures + ([
    "fusionMaterialPaths compiled",
    !isNil "_fnPaths",
    "aee_thermal_display_fnc_fusionMaterialPaths not compiled"
] call _check);
if (!isNil "_fnPaths") then {
    private _paths = [] call _fnPaths;
    private _ok = (count _paths) == 256
        && {((_paths select 0) find "fusion_emissive_000") >= 0}
        && {((_paths select 255) find "fusion_emissive_255") >= 0};
    _failures = _failures + (["band ladder 256 ordered", _ok, format ["%1 paths", count _paths]] call _check);
};

missionNamespace setVariable ["aee_test_failures_thermal_display", _failures];
diag_log text "[AEE-TEST] thermal_display DONE";
