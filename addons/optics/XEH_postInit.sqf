#include "script_component.hpp"
#include "\z\aee\addons\main\script_debug.hpp"

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

// ── ECOTI environment HUD ─────────────────────────────────────────────────
// Two Draw3D workers (rangefinder, map markers) and one update PFH.  Every
// worker gates on the aee_optics_hudEnabled setting each tick, so the HUD
// toggles live and an operator who leaves it OFF pays one getVariable read
// per tick.  Ported from workshop 3759527903 FPANO_ECOTI.  hasInterface
// only: the display and the raycasts are client-side.
if (hasInterface) then {
    [] call FUNC(hudRangefinder);
    [] call FUNC(hudMarkers);
    // MGRS map overlay: attaches a Draw handler to the engine map control
    // when the map opens.  Read-only, no marker is created or edited.
    [] call FUNC(mgrsMapDraw);
    [FUNC(hudUpdate), 0.1] call CBA_fnc_addPerFrameHandler;
    // MGRS GPS device readout: raised only while the player carries an
    // ItemGPS and the aee_optics_mgrsEnabled setting is on.
    [FUNC(gpsUpdate), 0.1] call CBA_fnc_addPerFrameHandler;
    // Signal-dependent tracker: the driver publishes the per-track state and
    // the draw layer renders it on the map and the HUD.  Both gate on the
    // aee_optics_trackerEnabled setting each tick.
    [] call FUNC(trackerDraw);
    [FUNC(trackerUpdate), 0.1] call CBA_fnc_addPerFrameHandler;
    // Eye adaptation: AEE owns the camera aperture and its rate (issue #141).
    [] call FUNC(initEyeAdaptation);
    // Normal-vision base grade and acuity pass (image realism).
    [] call FUNC(initBaseGrade);
    // Rain-scaled film grain (aee-workshop-copy item 5).
    [] call FUNC(initWeatherGrain);
    // Player-perception monitor: reconstruct and publish the view state.
    // It self-gates on a living local player, so a server pays one tick.
    [FUNC(perceptionUpdate), 0.5] call CBA_fnc_addPerFrameHandler;
};


// Muzzle flash / explosive flash response for NVG.
// A fired round with a high visibleFire value blooms or gates the tube.
// Follows the ACE3 pattern (nightvision/fnc_onFiredPlayer): read the
// ammo's visibleFire from CfgAmmo, discount suppressed weapons, and stamp
// a short window that fnc_applyNVGTubeModel reads as a blowout source.
// The event is local — only the shooter's own view is affected.
["Fired", {
    params ["_unit", "_weapon", "_muzzle", "_mode", "_ammo", "_magazine", "_projectile"];
    if (_unit != call CBA_fnc_currentUnit) exitWith {};
    if (_weapon == "throw" || _weapon == "put") exitWith {};

    // Barrel heat accumulates on every shot regardless of vision mode —
    // the barrel warms whether or not the shooter is watching through a
    // tube.  The thermal PFH swaps the weapon material while hot.
    [_weapon, _ammo] call EFUNC(thermal,applyWeaponBarrelHeat);

    // HitPart fires on the PROJECTILE, not on a man, so no class event
    // handler can carry it. The fired event is the only place that holds
    // the projectile, so the per-projectile handler is attached from here.
    // Attached before the NVG gate below, because impact heat is a physical
    // effect and not an NVG effect.
    if (!isNull _projectile) then {
        _projectile addEventHandler ["HitPart", {
            _this call EFUNC(thermal,handleImpactHeat);
        }];
    };

    // The emission POINT (issue #204): the projectile's position at
    // firing IS the muzzle - where the round and the hot gas come from.
    // Store it so the exhaust heat warms the ground exactly at the
    // barrel end, not a hardcoded offset.  Decays with the barrel heat.
    if (!isNull _projectile) then {
        private _muzzlePos = getPosASL _projectile;
        missionNamespace setVariable [QEGVAR(thermal,muzzlePos), _muzzlePos];
        missionNamespace setVariable [QEGVAR(thermal,muzzleTime), diag_tickTime];
    };

    if (currentVisionMode _unit != 1) exitWith {};

    private _visibleFire = getNumber (configFile >> "CfgAmmo" >> _ammo >> "visibleFire");
    if (_visibleFire <= 0) exitWith {};

    // Suppressor reduces the visible flash.
    private _silencer = (_unit weaponAccessories _weapon) select 0;
    if (_silencer != "") then {
        _visibleFire = _visibleFire * (getNumber (configFile >> "CfgWeapons" >> _silencer >> "ItemInfo" >> "AmmoCoef" >> "visibleFire"));
    };

    // Cap so sustained automatic fire does not keep the tube permanently
    // blinded; a single large flash (AT, grenade) can still fully blow it.
    _visibleFire = _visibleFire min 5;
    if (_visibleFire < 1.5) exitWith {};

    // Duration scales with flash intensity: brighter = longer window.
    private _duration = 0.15 + _visibleFire * 0.1;
    missionNamespace setVariable [QEGVAR(nightvision,nvgFlashUntil), CBA_missionTime + _duration];
}, QGVAR(muzzleFlash)] call EFUNC(core,installPlayerEngineHandler);

// Eye muzzle-flash response (issue #141). Normal vision has no tube to bloom,
// but the flash still raises the scene luminance for a moment. The eye model
// runs in normal vision only, so this is independent of the NVG handler above.
["Fired", {
    params ["_unit", "_weapon", "_muzzle", "_mode", "_ammo", "_magazine", "_projectile"];
    if (_unit != call CBA_fnc_currentUnit) exitWith {};
    if (_weapon == "throw" || _weapon == "put") exitWith {};

    private _visibleFire = getNumber (configFile >> "CfgAmmo" >> _ammo >> "visibleFire");
    if (_visibleFire <= 0) exitWith {};

    private _silencer = (_unit weaponAccessories _weapon) select 0;
    private _flashLux = [_visibleFire, _silencer != ""] call FUNC(eyeFlash);

    missionNamespace setVariable [QGVAR(eyeFlashLux), _flashLux];
    missionNamespace setVariable [QGVAR(eyeFlashUntil), CBA_missionTime + (0.15 + _visibleFire * 0.1)];
}, QGVAR(eyeFlash)] call EFUNC(core,installPlayerEngineHandler);

// ─── Map-wide thermal boot pass ───────────────────────────────────────────
// Pull EVERYTHING at mission start: one scan of all objects with material
// selections, swapping them to the cold baseline immediately.  This covers
// the whole map in one pass — no per-frame near-player LOD, no object
// left at baked engine defaults.  The config-level caps (class All:
// afMax 70, htMax 300) handle objects WITHOUT selections (map-embedded
// geometry) at load; this pass handles objects WITH selections (placed
// buildings, vehicles, statics) up front.
//
// Cost: one-time, at boot.  The near-player TICK in the thermal PFH still
// exists for objects spawned later (dynamic spawns) — this is the eager
// complement, not a replacement.
["ENTER"] call EFUNC(thermal,applyBuildingThermal);


// ─── Projectile impact residual heat (issue #204) ─────────────────────────
// The HitPart global event fires on EVERY projectile impact with
// [projectile, shooter, instigator, selection, ammo, vector, radius,
// surface, direct].  Each impact lays a warm stamp at the bullet hole -
// the round arrives hot (friction + the barrel it passed through) and
// transfers that heat into the surface.  Listener is cheap: one event
// per impact, stamps only.

// Uniform per-module state dump (plan T3): one state line per second.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;

