#include "script_component.hpp"

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
    if (_visionMode == 0 && !isNil QGVAR(sensorPFH)) then {
        setAperture -1;
        [] call EFUNC(nightvision,applyNVGTubeModel);
        [] call EFUNC(thermal,applyThermalVision);
        ["EXIT"] call EFUNC(thermal,applySecondSun);
        ["EXIT"] call EFUNC(thermal,applyClothingThermal);
        ["EXIT"] call EFUNC(thermal,applyBuildingThermal);
        ["EXIT"] call EFUNC(thermal,applyRainDroplets);
        // Fusion teardown: destroy the fusion PP handles and the diet
        // sun so the overlay does not leak into normal vision.
        [0] call EFUNC(thermal,cycleFusionMode);
        ["EXIT"] call EFUNC(thermal,applyFusionSun);
        [GVAR(sensorPFH)] call CBA_fnc_removePerFrameHandler;
        GVAR(sensorPFH) = nil;
        AEE_LOG_INFO("sensor PFH stopped (returned to normal vision)");
    };
    // Fade normal-vision optical effects immediately (managePostProcess
    // gates on vision mode internally).
    [] call FUNC(managePostProcess);
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
        // Rain droplets on the objective: particle source, engine assets.
        // Mode-INDEPENDENT: rain lands on the lens whether NVG or thermal,
        // so the source is created on ANY vision-mode entry (not just
        // thermal).  The TICK below drives the drop interval for both.
        ["ENTER"] call EFUNC(thermal,applyRainDroplets);
        // Second sun: create the physics-driven fake sun for the engine's
        // thermal sun term (buildings/terrain can only be sun-heated, not
        // driven per-object).  Cleaned up on mode 0 below.
        ["ENTER"] call EFUNC(thermal,applySecondSun);
        // Clothing thermal: apply per-item TI overrides to nearby units.
        ["ENTER"] call EFUNC(thermal,applyClothingThermal);
        // Building thermal: swap building materials to a cold TI rvmat so
        // buildings read cold at night (they bake red=128 in vanilla).
        ["ENTER"] call EFUNC(thermal,applyBuildingThermal);
    };
    // Start the fast sensor PFH when entering NVG/thermal.  The visionMode
    // event below is the SOLE owner of its lifecycle: it starts on mode > 0
    // and stops on mode == 0.  Inside the PFH, a transient vision-mode 0
    // (weapon raise, ADS, ENVG-II mode cycling) just skips the tick — it
    // must NOT destroy handles or stop the PFH, or the effects die on the
    // next frame and never recover.  AGC lag and gating need this
    // sub-second tick; the environment PFH only runs every 5 s.
    if (_visionMode > 0 && isNil QGVAR(sensorPFH)) then {
        GVAR(sensorPFH) = [{
            private _player = call CBA_fnc_currentUnit;
            private _veh = vehicle _player;
            // Run in the player's own view: on foot (cameraOn == player)
            // or in the player's vehicle (pilot/passenger/gunner).  Skip
            // spectator/UAV-terminal/external cameras.
            if (isNil "_player" || !alive _player) exitWith {};
            if (cameraOn != _player && {cameraOn != _veh}) exitWith {};
            private _vm = currentVisionMode _player;
            // Transient 0: skip, do not clean up or stop.  The visionMode
            // event handles real exits.
            if (_vm == 0) exitWith {};
            // Rain droplets on the objective: mode-independent physics (rain
            // lands on the lens whether it is NVG or thermal).  Run before
            // the mode-specific branches so both get the source.
            ["TICK"] call EFUNC(thermal,applyRainDroplets);
            if (_vm == 1) then {
                [] call EFUNC(nightvision,applyNVGTubeModel);
                // Fusion (Track B ENVG-B): when the headset is
                // fusion-capable (TI in visionMode, or the CBA
                // aee_thermal_fusionAlwaysOn override) and the operator
                // has fusion mode on, overlay the physics-driven emissive
                // thermal on the NVG base.  The overlay runs AFTER the
                // tube model so it composites on top of the I2 image.
                if ([] call EFUNC(thermal,isFusionCapable)) then {
                    if (missionNamespace getVariable [QEGVAR(thermal,fusionMode), 1] == 1) then {
                        [] call EFUNC(thermal,applyFusionPP);
                        ["ON"] call EFUNC(thermal,applyFusionSun);
                        [] call EFUNC(thermal,applyFusionOverlay);
                    };
                };
            };
            if (_vm == 2) then {
                // Thermal optics are parfocal: LWIR wavelength is ~10x
                // visible, so the depth of field is so deep that real FLIR
                // sights need NO focus mechanism (fixed at the factory).
                // Kill the NVG DoF effect so its last focus value (e.g.
                // PVS-31's 20 m ring) does not leak into the thermal view
                // as a fixed focus blur.
                private _hDof = missionNamespace getVariable [QEGVAR(nightvision,ppHandle_NVG_DoF), -1];
                if (_hDof >= 0) then {
                    ppEffectDestroy _hDof;
                    missionNamespace setVariable [QEGVAR(nightvision,ppHandle_NVG_DoF), -1];
                };
                // Scene-adaptive AGC (issue #196): compute the scene's
                // radiance window from the physics state BEFORE the
                // per-selection passes read it.  A real FLIR re-evaluates
                // its gain continuously from the scene histogram; this is
                // the same per-frame evaluation.
                [] call EFUNC(thermal,updateThermalAGC);
                [] call EFUNC(thermal,applyThermalVision);
                [] call EFUNC(thermal,applyEngineThermal);
                [] call EFUNC(thermal,applyWeaponBarrelHeat);
                ["TICK"] call EFUNC(thermal,applySecondSun);
                ["TICK"] call EFUNC(thermal,applyClothingThermal);
                ["TICK"] call EFUNC(thermal,applyBuildingThermal);
                // Contact conduction: heat exchange between the operator
                // and what they touch (vehicle interior, prone ground).
                // Runs after the object solves so both sides have temps.
                [] call EFUNC(thermal,applyContactConduction);
                // Radiative exchange (issue #204): a hot object heats the
                // objects around it (a hot barrel heats the weapon from
                // inside out, a burning wreck heats everything nearby) -
                // Stefan-Boltzmann view-factor transfer.
                [] call EFUNC(thermal,applyRadiativeExchange);
                // Exhaust / emission heat (issue #204): a firing muzzle
                // or running engine expels hot gas that warms the ground
                // and air around it (muzzle blast over a prone shooter's
                // floor, jet afterburner heating the tarmac).
                [] call EFUNC(thermal,applyExhaustHeat);
            };
        }, 0.1] call CBA_fnc_addPerFrameHandler;
        private _logMsg = format ["sensor PFH started (vision mode %1)", _visionMode];
        AEE_LOG_INFO(_logMsg);
    };
}, false] call CBA_fnc_addPlayerEventHandler;

// Muzzle flash / explosive flash response for NVG.
// A fired round with a high visibleFire value blooms or gates the tube.
// Follows the ACE3 pattern (nightvision/fnc_onFiredPlayer): read the
// ammo's visibleFire from CfgAmmo, discount suppressed weapons, and stamp
// a short window that fnc_applyNVGTubeModel reads as a blowout source.
// The event is local — only the shooter's own view is affected.
["fired", {
    params ["_unit", "_weapon", "_muzzle", "_mode", "_ammo", "_magazine", "_projectile"];
    if (_unit != call CBA_fnc_currentUnit) exitWith {};
    if (_weapon == "throw" || _weapon == "put") exitWith {};

    // Barrel heat accumulates on every shot regardless of vision mode —
    // the barrel warms whether or not the shooter is watching through a
    // tube.  The thermal PFH swaps the weapon material while hot.
    [_weapon, _ammo] call EFUNC(thermal,applyWeaponBarrelHeat);

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
}, false] call CBA_fnc_addPlayerEventHandler;

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

