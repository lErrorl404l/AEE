#include "script_component.hpp"

/*
nightvision component test (aee_diagnostics_fnc_test).

Headless-safe: asserts the merged engine config only.  It uses no camera, no
display and no client-only gate, so a dedicated server runs it.  Emits
CBA-style TEST: OK/FAIL lines and publishes the failure count to
aee_test_failures_nightvision.
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

// ── The NVG display classes AEE declares in RscTitles.hpp, read live. ─────
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
    ["aee_nightvision_nvgTitle", 10778],
    ["aee_nightvision_nvgImperfections", 10780]
];

// ── The imperfection overlays point at the addon's own textures. ──────────
private _controls = _titles >> "aee_nightvision_nvgImperfections" >> "controls";
{
    _x params ["_control", "_idc", "_file"];
    private _cfg = _controls >> _control;
    private _text = getText (_cfg >> "text");
    private _ok = (isClass _cfg)
        && {(getNumber (_cfg >> "idc")) == _idc}
        && {(_text find "z\aee\addons\nightvision\data") >= 0}
        && {(_text find _file) >= 0};
    _failures = _failures + (["texture " + _control, _ok, _text] call _check);
} forEach [
    ["NVGBlemishes", 1010, "nvg_blemishes.paa"],
    ["NVGReticulation", 1011, "nvg_reticulation.paa"]
];

// ── The tube-face indicators the display drives by idc. ───────────────────
private _nvgControls = _titles >> "aee_nightvision_nvgTitle" >> "controls";
{
    _x params ["_control", "_idc"];
    private _cfg = _nvgControls >> _control;
    private _got = getNumber (_cfg >> "idc");
    _failures = _failures + (["indicator " + _control, (isClass _cfg) && _got == _idc, str _got] call _check);
} forEach [
    ["NVGFocusText", 1002],
    ["NVGFocusBar", 1003],
    ["NVGBatteryWarning", 1004],
    ["NVGBatteryBlink", 1005]
];

missionNamespace setVariable ["aee_test_failures_nightvision", _failures];
diag_log text "[AEE-TEST] nightvision DONE";
