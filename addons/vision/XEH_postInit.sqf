#include "script_component.hpp"
#include "\z\aee\addons\lib\script_debug.hpp"

AEE_MODULE_POST_INIT

// Apply post-process effects immediately when the player's vision mode
// changes (putting on / removing NVGs or thermal).
//
// The environment PFH in core (fnc_updateEnvironment) drives
// managePostProcess but only every `updateInterval` seconds (default 5).
// Without this handler there is a visible delay between putting on NVGs
// and the filter appearing.  ACE3 uses the same "visionMode" player
// event (addons/nightvision/XEH_postInit.sqf) to start its NVG PFH the
// instant the mode flips.
//
// The handler only runs on the local machine: effects are client-side.
["visionMode", {
    params ["_unit", "_visionMode"];
    if (_unit != call CBA_fnc_currentUnit) exitWith {};
    if (isNil QGVAR(isReady)) exitWith {};
    // Real exit to normal vision: the visionMode event is the only place
    // that knows the exit is genuine (not a transient 0 from weapon raise
    // or ENVG-II cycling).  Run each sensor's exit block once to destroy
    // handles and tear down the overlay, then stop the PFH.  Also restore
    // the engine's default aperture (DoF off) so normal vision is sharp.
    if (_visionMode == 0) then {
        [] call FUNC(teardownSensors);
    };
    // Fade normal-vision optical effects immediately (managePostProcess
    // gates on vision mode internally).
    [] call FUNC(managePostProcess);
    // Apply or stand down the normal-vision base grade at once, so a mode
    // change does not wait for the 1 s PFH tick.
    [] call FUNC(applyBaseGrade);
    // Reset sensor handles to -1 on entry.  The engine can kill ppEffects
    // (alt-tab, resize) leaving stale positive handle numbers that fail
    // every call with "Invalid post effect handle".  Forcing -1 makes the
    // first sensor tick recreate them cleanly.
    if (_visionMode == 1) then {
        {
            missionNamespace setVariable [_x, -1];
        } forEach [
            QEGVAR(nightvision,ppHandle_NVG_CC),
            QEGVAR(nightvision,ppHandle_NVG_Bloom),
            QEGVAR(nightvision,ppHandle_NVG_Vignette),
            QEGVAR(nightvision,ppHandle_NVG_Grain)
        ];
    };
    if (_visionMode == 2) then {
        {
            missionNamespace setVariable [_x, -1];
        } forEach [
            QEGVAR(thermal,ppHandle_Thermal_Vignette),
            QEGVAR(thermal,ppHandle_Thermal_CC),
            QEGVAR(thermal,ppHandle_Thermal_Grain),
            QEGVAR(thermal,ppHandle_Thermal_Blur)
        ];
        [] call FUNC(enterThermalSensors);
    };
    // Start the fast sensor PFH when entering NVG/thermal.  The visionMode
    // event below is the SOLE owner of its lifecycle: it starts on mode > 0
    // and stops on mode == 0.  Inside the PFH, a transient vision-mode 0
    // (weapon raise, ADS, ENVG-II mode cycling) just skips the tick — it
    // must NOT destroy handles or stop the PFH, or the effects die on the
    // next frame and never recover.  AGC lag and gating need this
    // sub-second tick; the environment PFH only runs every 5 s.
    if (_visionMode > 0 && isNil QGVAR(sensorPFH)) then {
        // Key the session to the unit it was opened for.  The "visionMode"
        // event cannot see a death, a respawn or a remote-control switch,
        // so the PFH below owns that part of the lifecycle: when the unit
        // changes or dies, it tears the session down itself (GAP-026).
        GVAR(sensorUnit) = _unit;
        GVAR(sensorPFH) = [{
            private _perfT0 = diag_tickTime;
            private _player = call CBA_fnc_currentUnit;
            // Death, respawn or a remote-control switch is NOT a vision
            // mode change, so the event never fires for it.  Without this
            // the handler outlives the session: the handle, the flags and
            // the overlays stay live into the respawn (GAP-026).  Tear
            // down here instead of exiting, because nothing else will.
            if (isNil "_player"
                || {!alive _player}
                || {!isNil QGVAR(sensorUnit) && _player isNotEqualTo GVAR(sensorUnit)}) exitWith {
                [] call FUNC(teardownSensors);
            };
            private _veh = vehicle _player;
            // Run in the player's own view: on foot (cameraOn == player)
            // or in the player's vehicle (pilot/passenger/gunner).  Skip
            // spectator/UAV-terminal/external cameras.
            if (cameraOn != _player && {cameraOn != _veh}) exitWith {};
            private _vm = currentVisionMode _player;
            // Transient 0: skip, do not clean up or stop.  The visionMode
            // event handles real exits.
            if (_vm == 0) exitWith {};
            // ── Fusion gate-off restore ───────────────────────────────────
            // The source restores its painted bodies on EVERY Draw3D frame:
            // fn_postInit.sqf:19 calls fn_thermalFill, whose pass 1 restores
            // every registered body once _want is false (fn_thermalFill.sqf:76-96).
            // aee drives the overlay from this PFH instead, so this PFH must
            // run the same restore whenever the gate is off: a switch to
            // thermal (vision mode 2), a device that stops being
            // fusion-capable, or the operator switching fusion off.  A genuine
            // return to normal vision is handled by teardownSensors, and death
            // or a unit change by the guard above.  Two namespace reads when
            // nothing is painted; EXIT is idempotent.
            private _fusionDirty =
                (missionNamespace getVariable [QEGVAR(thermal,fusionFillReg), []]) isNotEqualTo []
                || {(missionNamespace getVariable [QEGVAR(thermal,fusionOverlaySaved), []]) isNotEqualTo []};
            if ((_vm != 1) && _fusionDirty) then {
                [_player, "EXIT"] call EFUNC(thermal,applyFusionOverlay);
            };
            // Rain droplets on the objective: mode-independent physics (rain
            // lands on the lens whether it is NVG or thermal).  Run before
            // the mode-specific branches so both get the source.
            BEGIN_COUNTER(applyRainDroplets);
            ["TICK"] call EFUNC(thermal,applyRainDroplets);
            END_COUNTER(applyRainDroplets);
            if (_vm == 1) then {
                BEGIN_COUNTER(applyNVGTubeModel);
                [] call EFUNC(nightvision,applyNVGTubeModel);
                END_COUNTER(applyNVGTubeModel);
                // Fusion (Track B ENVG-B): the OPERATOR decides, never an
                // automatic response.  isFusionCapable asks whether this
                // device MAY fuse.  The mode asks whether the operator HAS
                // asked for it, and its default is I2-only, so nothing
                // renders fused until the operator presses the keybind or
                // the fusionAlwaysOn setting forces it.  The overlay runs
                // AFTER the tube model so it composites on top.
                if ([] call EFUNC(thermal,isFusionCapable)) then {
                    if (missionNamespace getVariable [QEGVAR(thermal,fusionAlwaysOn), false]) then {
                        [1] call EFUNC(thermal,cycleFusionMode);
                    };
                    if (missionNamespace getVariable [QEGVAR(thermal,fusionMode), 0] == 1) then {
                        [] call EFUNC(thermal,applyFusionPP);
                        ["ON"] call EFUNC(thermal,applyFusionSun);
                        [] call EFUNC(thermal,applyFusionOverlay);
                        [true] call EFUNC(thermal,outlineToggle);
                    } else {
                        // Capable but the operator has not asked for fusion:
                        // restore anything a previous fused tick painted, then
                        // tear the outline down rather than leave it stale.
                        if (_fusionDirty) then {
                            [_player, "EXIT"] call EFUNC(thermal,applyFusionOverlay);
                        } else {
                            [false] call EFUNC(thermal,outlineToggle);
                        };
                    };
                } else {
                    // The device stopped being fusion-capable while the mode
                    // stayed 1.  Restore the painted bodies and lower the
                    // outline, or both survive into the next device.
                    if (_fusionDirty) then {
                        [_player, "EXIT"] call EFUNC(thermal,applyFusionOverlay);
                    };
                };
            };
            if (_vm == 2) then {
                [] call FUNC(runThermalPass);
            };
            private _perfMsg = format ["sensorPFH %1 ms", round ((diag_tickTime - _perfT0) * 1000)];
            AEE_LOG_DEBUG(_perfMsg);
        }, 0.1] call CBA_fnc_addPerFrameHandler;
        private _logMsg = format ["sensor PFH started (vision mode %1)", _visionMode];
        AEE_LOG_INFO(_logMsg);
    };
}, false] call CBA_fnc_addPlayerEventHandler;

// DTV base channel (prototype): start the host driver when the
// AEE Thermal > Display > base channel setting is DTV.  With the default
// (Vanilla TI) this is a no-op.  The setting's change callback reconciles it
// on a later change without a mission restart.
[] call FUNC(updateThermalHostSetting);

if (hasInterface) then {
    // Normal-vision base grade and acuity pass (image realism).
    [] call FUNC(initBaseGrade);
    // Rain-scaled film grain (aee-workshop-copy item 5).
    [] call FUNC(initWeatherGrain);
    // Player-perception monitor: reconstruct and publish the view state.
    // It self-gates on a living local player, so a server pays one tick.
    [FUNC(perceptionUpdate), 0.5] call CBA_fnc_addPerFrameHandler;
};
