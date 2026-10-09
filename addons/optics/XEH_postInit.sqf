#include "script_component.hpp"

AEE_MODULE_POST_INIT

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
    // NATO/OPFOR map symbols: applies the AEE symbols as real engine markers
    // while the map is open, client-local and reversible.
    [] call FUNC(symbologyMarkers);
    // NATO/OPFOR 3D world symbols: draws the real AEE marker texture in the 3D
    // view.  The engine's own unit icons remain; this worker does not remove
    // them.
    [] call FUNC(symbologyWorldDraw);
    [FUNC(hudUpdate), 0.1] call CBA_fnc_addPerFrameHandler;
    // MGRS GPS device readout: raised only while the player carries an
    // ItemGPS and the aee_optics_mgrsEnabled setting is on.
    [FUNC(gpsUpdate), 0.1] call CBA_fnc_addPerFrameHandler;
    // Signal-dependent tracker: the driver publishes the per-track state and
    // the draw layer renders it on the map and the HUD.  Both gate on the
    // aee_optics_trackerEnabled setting each tick.
    [] call FUNC(trackerDraw);
    [FUNC(trackerUpdate), 0.1] call CBA_fnc_addPerFrameHandler;
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
}, QGVAR(muzzleFlash)] call EFUNC(lib,installPlayerEngineHandler);

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

// Uniform per-module state dump (plan T3): one state line per second.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;
