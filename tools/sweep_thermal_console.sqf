aee_optics_nvgDebug = true;
if !(isNil "aee_optics_sweepPFH") then {
    [aee_optics_sweepPFH] call CBA_fnc_removePerFrameHandler;
};

// Pre-start delay: give the player time to exit the pause menu and get
// positioned before skipTime starts stepping the clock.  The probe vehicle
// is selected AFTER the delay so it sees the vehicle the player actually
// stands next to, not whatever was in range at paste time.
diag_log text "[AEE_SWEEP] starting in 5 s - exit the menu first";

[] spawn {
    sleep 5;
    private _probeVeh = (nearestObjects [player, ["AllVehicles"], 50] select {alive _x}) select 0;
    diag_log text format ["[AEE_SWEEP] probe vehicle: %1 (null=%2)", _probeVeh, isNull _probeVeh];

    aee_optics_sweepPFH = [{
    params ["_args", "_handle"];
    _args params ["_idx", "_steps", "_probeVeh"];
    if (_idx >= _steps) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
        aee_optics_sweepPFH = nil;
        diag_log text "[AEE_SWEEP] DONE";
    };
    private _hour = _idx;
    skipTime ((_hour - dayTime + 24) % 24);
    private _rad = [overcast] call aee_core_fnc_calculateSolarRadiation;
    private _sunElev = missionNamespace getVariable ["aee_core_currentSunElevation", -90];
    private _biome = missionNamespace getVariable ["aee_core_biome", "Cfa"];
    if !(_biome isEqualType "") then { _biome = "Cfa"; };
    private _month = (date select 1) max 1 min 12;
    private _posASL = getPosASL player;
    private _air = [_biome, _month, _posASL] call aee_thermal_fnc_updateTemperature;
    private _vehT = -999;
    if !(isNull _probeVeh) then {
        [] call aee_thermal_fnc_calculateObjectTemperature;
        private _state = missionNamespace getVariable ["aee_thermal_thermalState", createHashMap];
        private _key = str _probeVeh;
        diag_log text format ["[AEE_SWEEP] probe key=%1 stateKeys=%2", _key, count _state];
        private _entry = _state getOrDefault [_key, []];
        if (count _entry >= 1) then {
            _vehT = _entry select 0;
            if !(_vehT isEqualType 0) then { _vehT = -999; };
        };
    };
    diag_log text format [
        "[AEE_SWEEP] h=%1 sunElev=%2 rad=%3 bright=%4 air=%5 vehT=%6",
        _hour, _sunElev, _rad, (_rad * 13), _air, _vehT
    ];
    _args set [0, _idx + 1];
    }, 0, [0, 24, _probeVeh]] call CBA_fnc_addPerFrameHandler;
    diag_log text "[AEE_SWEEP] started v2 (24 h, full physics)";
};