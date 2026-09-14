#include "script_component.hpp"

// Standalone access to the AEE actions. The same actions are exposed to the
// ACE3 interaction menu by compat_ace3; these keybinds work without ACE3.
["AEE", "WeatherReport", [LLSTRING(WeatherReport), "Show the AEE weather report"], {
    call FUNC(openWeatherReport);
}, {}] call CBA_fnc_addKeybind;

["AEE", "Altimeter", [LLSTRING(Altimeter), "Show the AEE altimeter"], {
    call FUNC(openAltimeter);
}, {}] call CBA_fnc_addKeybind;

// ─── NVG depth-of-field focus control ─────────────────────────────────────
// Real NVG objectives are MANUAL focus: the operator sets the ring once
// (~10-25 m for patrol) and leaves it, so objects pass through the focus
// plane as they move - the natural "blur gate".  Auto-focus is optional
// (the O3DE state machine in fnc_applyNVGTubeModel).  These keybinds
// toggle the mode and rack the ring in manual mode.
//
// The focus values live in missionNamespace so fnc_applyNVGTubeModel reads
// them on the sensor PFH tick regardless of which addon owns the keybind.
["AEE", "DoFModeToggle", [LLSTRING(DoFModeToggle), "Toggle NVG focus: auto or manual"], {
    private _mode = missionNamespace getVariable ["aee_optics_dofMode", 0];
    _mode = parseNumber (_mode != 1);   // 0 <-> 1
    missionNamespace setVariable ["aee_optics_dofMode", _mode];
    if (_mode == 0) then {
        AEE_LOG_INFO("DoF focus: AUTO");
    } else {
        AEE_LOG_INFO("DoF focus: MANUAL");
    };
}, {}] call CBA_fnc_addKeybind;

// Manual ring: hold the key to rack in or out.  Rack speed ~10 m/s,
// matching the ring-turn feel.  Stored distance is clamped to the
// objective's 0.25 m near limit and 300 m far limit.  The 6th arg is
// the default KEYBIND [key, [shift, ctrl, alt]] - [0, [false,false,false]]
// means unbound by default (the player assigns it in Configure Addons).
["AEE", "DoFFocusIn", [LLSTRING(DoFFocusIn), "NVG manual focus: rack nearer"], {
    private _d = missionNamespace getVariable ["aee_optics_dofManualDist", 15];
    _d = (_d - 1) max 0.25;
    missionNamespace setVariable ["aee_optics_dofManualDist", _d];
}, {}, [0, [false, false, false]]] call CBA_fnc_addKeybind;

["AEE", "DoFFocusOut", [LLSTRING(DoFFocusOut), "NVG manual focus: rack farther"], {
    private _d = missionNamespace getVariable ["aee_optics_dofManualDist", 15];
    _d = (_d + 1) min 300;
    missionNamespace setVariable ["aee_optics_dofManualDist", _d];
}, {}, [0, [false, false, false]]] call CBA_fnc_addKeybind;
