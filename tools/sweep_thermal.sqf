/*
 * Automated thermal sweep (DEV TOOL — not part of the mod).
 *
 * Steps the mission clock through a full 24 h cycle with skipTime and
 * logs the physics model at each step.  Verifies the day/night curve:
 * radiation peaks near midday and is 0 at night, brightness = rad * 13,
 * and air/ground temperatures follow with the expected lag.
 *
 * No screenshots: the physics is verified from the logged numbers, and
 * the engine's brightness response is already established (A3TI's proven
 * 13, scaled by our radiation).
 *
 * USAGE (debug console, LOCAL):
 *   aee_optics_nvgDebug = true;
 *   [] execVM "tools\sweep_thermal.sqf";
 *
 * Logs [AEE_SWEEP] lines; analyse with tools/analyze_thermal_sweep.py.
 */
if (!hasInterface) exitWith {};

private _stepHours = 1;      // 1 h per sample -> 24 samples
private _settle = 6.0;       // seconds — MUST exceed the env PFH interval
                             // (GVAR(updateInterval) = 5 s) or the logged
                             // values are a stale cache (the first sweep
                             // showed a flat 0.420 because 1 s < 5 s)

private _steps = 24 / _stepHours;
if !(isNil QGVAR(sweepPFH)) then {
    [GVAR(sweepPFH)] call CBA_fnc_removePerFrameHandler;
};

GVAR(sweepPFH) = [{
    params ["_args", "_handle"];
    _args params ["_idx", "_steps", "_stepHours", "_settle"];
    if (_idx >= _steps) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
        GVAR(sweepPFH) = nil;
        diag_log text "[AEE_SWEEP] DONE";
    };

    private _hour = _idx * _stepHours;
    skipTime ((_hour - dayTime + 24) % 24);

    [{
        params ["_hour"];
        private _rad = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), -1];
        private _air = missionNamespace getVariable [QEGVAR(core,currentTemperature), -1];
        private _ground = missionNamespace getVariable [QEGVAR(core,avgGroundTemp), -1];
        diag_log text format [
            "[AEE_SWEEP] h=%1 dayTime=%2 rad=%3 brightness=%4 air=%5 ground=%6",
            _hour, dayTime, _rad, (_rad * 13), _air, _ground
        ];
    }, [_hour], _settle] call CBA_fnc_waitAndExecute;

    _args set [0, _idx + 1];
}, 0, [0, _steps, _stepHours, _settle]] call CBA_fnc_addPerFrameHandler;

diag_log text "[AEE_SWEEP] started (24 h, 1 h steps)";