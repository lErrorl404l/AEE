// ─── Thermal sweep — PASTE THIS INTO THE DEBUG CONSOLE (LOCAL) ───────────
// Steps the mission clock 0..23 h with skipTime and logs the physics at
// each hour.  Radiation is computed DIRECTLY from the model (instant, no
// cache) — the environment PFH only refreshes every 5 s, so reading its
// cached value with a short settle gives a stale, flat result.
//
// ~24 s to complete.  Aim at a building in thermal first.

aee_optics_nvgDebug = true;

if !(isNil "aee_optics_sweepPFH") then {
    [aee_optics_sweepPFH] call CBA_fnc_removePerFrameHandler;
};

aee_optics_sweepPFH = [{
    params ["_args", "_handle"];
    _args params ["_idx", "_steps"];
    if (_idx >= _steps) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
        aee_optics_sweepPFH = nil;
        diag_log text "[AEE_SWEEP] DONE";
    };
    private _hour = _idx;
    skipTime ((_hour - dayTime + 24) % 24);

    // Compute radiation DIRECTLY from the model at the new clock time —
    // no cache, no wait.
    private _rad = [overcast] call aee_core_fnc_calculateSolarRadiation;

    // Temps still come from the cached env state (they lag the PFH); the
    // calibration cares about radiation, which is now instant + accurate.
    private _air = missionNamespace getVariable ["aee_core_currentTemperature", -1];
    private _ground = missionNamespace getVariable ["aee_core_avgGroundTemp", -1];
    diag_log text format [
        "[AEE_SWEEP] h=%1 dayTime=%2 rad=%3 brightness=%4 air=%5 ground=%6",
        _hour, dayTime, _rad, (_rad * 13), _air, _ground
    ];

    _args set [0, _idx + 1];
}, 0, [0, 24]] call CBA_fnc_addPerFrameHandler;

diag_log text "[AEE_SWEEP] started (24 h)";
