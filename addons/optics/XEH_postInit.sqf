#include "script_component.hpp"

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
        // Key the session to the unit it was opened for.  The "visionMode"
        // event cannot see a death, a respawn or a remote-control switch,
        // so the PFH below owns that part of the lifecycle: when the unit
        // changes or dies, it tears the session down itself (GAP-026).
        GVAR(sensorUnit) = _unit;
        GVAR(sensorPFH) = [{
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
            };
            // ─── The heat model runs whenever the THERMAL CHANNEL is live ──────
            // The heat model is physics; the display is a consumer of it, and a
            // consumer cannot be fed by a model that never runs.
            //
            // Ordering.  The AGC window is computed BEFORE the per-selection
            // solves that read it.  The DISPLAY calls then run after the solve,
            // so they read THIS tick's temperatures rather than the previous
            // tick's, which removes a frame of latency instead of adding it.
            if (_vm == 2) then {
                // Per-tick selection budget (lag fix).  The runtime
                // selectionNames fallback widened coverage, and the periodic
                // building rescan then solved every nearby structure's every
                // selection in ONE tick (the live RPT gate moved temps=15 to
                // temps=2897 across one rescan), and each selection runs the
                // Gagge two-node solve.  The budget is re-armed each tick and
                // spent per solved selection in fnc_applySelectionThermal, so
                // a wide scene converges over a few ticks instead of freezing
                // one frame.  The one-shot boot pass runs before any tick, so
                // it is not capped.
                // Budget SIZED FROM THE INPUT CLOCK, not picked.  The solve reads
                // air temperature, humidity, fog, rain and air density, and all
                // of those move on the updateInterval cadence (default 5 s).  The
                // solve is a relaxation toward that equilibrium, so its answer AT
                // equilibrium does not depend on how often it runs: a budget that
                // spreads ONE full pass across the ticks in one interval reaches
                // the same equilibrium, never lags the inputs, and costs a fifteenth
                // of the work.  The fixed 900 it replaces sat AT equilibrium 9000
                // times a second for no change, in both modes.
                //
                // selSolveTicks is the round-robin step for the object list.  The
                // consumer exits when the budget runs out, so a smaller budget
                // against a STABLE order would starve every object past the cut
                // permanently.  The step is sized so one cycle also completes
                // inside one interval.
                private _selCount = count (missionNamespace getVariable [QEGVAR(thermal,selTemperature), []]);
                private _atmos = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
                if !(_atmos isEqualType 0) then { _atmos = 5 };
                if (_atmos <= 0) then { _atmos = 1 };
                // 0.1 s is this handler's own period, so this is the tick count in
                // one atmosphere interval.
                private _ticks = ceil (_atmos / 0.1);
                missionNamespace setVariable [QEGVAR(thermal,selSolveTicks), _ticks];
                // A SINGLE shared budget is spent FIRST-COME, and clothing runs
                // first over allUnits at every unit's every selection.  With the
                // small clock-derived share that left buildings and vehicles
                // permanently unsolved, which is a worse fault than the lag it
                // fixed: thermal simply goes dark.  Each consumer therefore gets
                // its own share, re-armed immediately before its own call, and
                // the structure list is round-robin so a small share cannot
                // starve its tail (see fnc_applyBuildingThermal).
                private _clothingShare = 120 max 1;
                missionNamespace setVariable [QEGVAR(thermal,selSolveBudget), _clothingShare];
                [] call EFUNC(thermal,updateThermalAGC);
                [] call EFUNC(thermal,applyWeaponBarrelHeat);
                ["TICK"] call EFUNC(thermal,applyClothingThermal);
                missionNamespace setVariable [QEGVAR(thermal,selSolveBudget), ceil (_selCount / _ticks) max 1];
                ["TICK"] call EFUNC(thermal,applyBuildingThermal);
                // Contact conduction: heat exchange between the operator and
                // what they touch (vehicle interior, prone ground).  Runs after
                // the object solves so both sides have temperatures.
                [] call EFUNC(thermal,applyContactConduction);
                // Radiative exchange (issue #204): a hot object heats the
                // objects around it - Stefan-Boltzmann view-factor transfer.
                [] call EFUNC(thermal,applyRadiativeExchange);
                // Exhaust / emission heat (issue #204): a firing muzzle or a
                // running engine expels hot gas that warms ground and air.
                [] call EFUNC(thermal,applyExhaustHeat);
            };
            if (_vm == 2) then {
                // Thermal optics are parfocal: LWIR wavelength is ~10x
                // visible, so the depth of field is so deep that real FLIR
                // sights need NO focus mechanism (fixed at the factory).
                // Kill the NVG DoF effect so its last focus value (e.g.
                // PVS-31's 20 m ring) does not leak into the thermal view
                // as a fixed focus blur.
                // The NVG objective-focus handle belongs to nightvision.  Ask
                // that addon to release it rather than destroying another
                // module's handle from here, so ownership stays with the owner
                // and a scope release can never strand it.
                [] call EFUNC(nightvision,teardownNvgDoF);
                [] call EFUNC(thermal,applyThermalVision);
                [] call EFUNC(thermal,applyEngineThermal);
                ["TICK"] call EFUNC(thermal,applySecondSun);
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

