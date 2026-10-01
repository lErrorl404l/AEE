#include "..\..\script_component.hpp"
/*
 * Per-clothing thermal for infantry (issue #124 migration).
 *
 * The engine composites each equipped clothing item's TI texture onto the
 * wearer: the ghillie suit hides the wearer because ghillie.p3d references
 * ghillie_ti.paa (a cold TI map).  This is the per-item thermal mechanism.
 *
 * The OLD version swapped clothing materials to ti_cloth_hot/cold.rvmat
 * (the #123 bug class - keyword-matched rvmats that broke on third-party
 * uniform paths like ZuluCustomG3\data\g2\g2_pants.rvmat).  This version
 * drives the per-selection thermal substrate: each unit's selections get
 * their temperature solved from physics (solar absorptance read from the
 * worn garment's own colour, McAdams convection, Stefan-Boltzmann
 * radiation to MRT, real body mass) and painted with the FLIR white-hot
 * procedural colour.
 *
 * The substrate reads the selection's OWN texture for solar absorptance
 * (a unit's textures ARE its worn clothing: uniform/vest/helmet/goggles,
 * each with its own colour and therefore its own solar loading), so the
 * helmet reads different from the uniform - the real per-item look,
 * physics-driven, no keyword matching.
 *
 * Multiplayer: setObjectTexture is LOCAL, correct here.  Each client
 * renders its own thermal pass and computes identical physics, so each
 * client applies the same colour locally and every player sees the same
 * thermal appearance.  No network traffic.
 *
 * Cost: one setObjectTexture per thermal selection per throttle tick
 * (0.05 s), NOT per frame.  All units are scanned because there is no
 * reason for a range limit.
 *
 * Restored on EXIT (mode "EXIT") to the saved originals.
 */
params ["_mode"];

if (!hasInterface) exitWith { 0 };

// ─── EXIT: restore every saved texture ───────────────────────────────────
// Restore, then STOP.  Without exitWith the run falls through into the
// apply path below and re-commits the selection textures it just undid, so
// a worn uniform stayed flat-shaded in normal vision.
if (_mode == "EXIT") exitWith {
    ["", "", "EXIT"] call FUNC(applySelectionThermal)
};

private _player = call CBA_fnc_currentUnit;
// Run in the player's own view: on foot (cameraOn == player) or in
// the player's vehicle (pilot/passenger/gunner - cameraOn is the
// vehicle).  Skip spectator/UAV-terminal/external cameras.
private _veh = vehicle _player;
if (isNil "_player" || !alive _player) exitWith { 0 };
if (cameraOn != _player && {cameraOn != _veh}) exitWith { 0 };

// ─── Physics inputs ────────────────────────────────────────────────────────
// Thermal state: insulation + ambient drive the solve's convection term
// through the ambient temperature.  The substrate reads the real air
// temperature, wind, and solar flux from the core environment state.
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };

// Bound the unit sweep by the player's own view distance.  `allUnits` is
// world-wide, and this path runs at 10 Hz from the sensor tick, so an
// unbounded list meant a per-selection solve and texture write for every
// unit in the mission ten times a second.  The substrate is local to the
// eye, so a unit the player cannot see does not need painting.
private _viewDist = (getObjectViewDistance select 0) max 50;
private _refPos = getPosATL _player;
private _applied = 0;
// Fetched ONCE for the whole sweep.  This read was INSIDE the per-unit loop,
// so it cost a missionNamespace lookup per unit per 10 Hz tick.
private _loadout = missionNamespace getVariable [QGVAR(loadoutThermalCache), -1];
if (_loadout isEqualType 0) then {
    _loadout = createHashMap;
    missionNamespace setVariable [QGVAR(loadoutThermalCache), _loadout];
};
{
    if (isNull _x || {!alive _x}) then { continue; };
    if ((_x distance _refPos) > _viewDist) then { continue; };
    private _obj = _x;

    // Dynamic thermal-selection discovery (issue #204): Men = all
    // texture slots, cached per class.  No static name matching.
    private _selections = [_obj] call FUNC(getThermalSelections);
    if (count _selections == 0) then { continue; };

    // Loadout thermal (issue #204): every carried item - uniform, vest,
    // helmet, goggles, backpack and contents (mags, grenades, radios) -
    // has its own mass and material, so its temperature delta from the
    // body scales with the item's thermal inertia.  A FULL backpack
    // (more mass) warms and cools SLOWER than an empty one.  The map is
    // selection-name -> flux multiplier; cached per unit.
    // The absent-key default is -1, NOT createHashMap: SQF evaluates an
    // argument eagerly, so the old form allocated a throwaway hashmap for
    // EVERY unit on EVERY 10 Hz tick.  -1 is a number, so it cannot be
    // mistaken for a cached map, and it also stops an empty map from being
    // recomputed every tick (the old `count == 0` test did that).
    private _loadoutKey = str _obj;
    private _loadoutMap = _loadout getOrDefault [_loadoutKey, -1];
    if (_loadoutMap isEqualType 0) then {
        _loadoutMap = [_obj] call FUNC(calculateUnitLoadoutThermal);
        _loadout set [_loadoutKey, _loadoutMap];
    };

    // ─── Per-selection substrate solve + FLIR paint ────────────────────
    // Each selection: the substrate reads the material via the #96
    // detector chain (hiddenSelectionsMaterials -> rvmat surfaceInfo ->
    // bisurf class, selection-name conventions, then object fallback),
    // reads the selection's own texture for solar absorptance (NASA
    // TP-2005-212792), and solves the lumped-capacity energy balance
    // with the unit's real mass.  q_internal = 0 (no engine heat on a
    // person); the ground view factor comes from the MATERIAL (metal on
    // the feet sees ground, glass/plastic on the head sees sky) - the
    // dynamic equivalent of the old name-based fGround.
    // HOISTED out of the per-selection loop.  selectionNames is an ENGINE call
    // and getArray a config read, and both were re-fetched for EVERY selection
    // of EVERY unit on EVERY tick.  They depend only on the object, so they are
    // read once per unit here.
    private _names = if (_obj isKindOf "Man") then {
        selectionNames _obj
    } else {
        getArray (configOf _obj >> "hiddenSelections")
    };
    {
        private _selIdx = _x;
        private _fGround = 0.5;
        private _selName = if (_selIdx < count _names) then { _names select _selIdx } else { "" };
        if (_selName == "") then { continue; };
        // View factor from the MATERIAL CLASS, not k.  The old conductivity
        // bands overlapped: glass (k 1.1) passed `k <= 1.5` (sky) and was then
        // overwritten by `0.2 <= k <= 2.0` (ground), and rubber 0.22 and
        // plastic 0.17 share a k with opposite intent, so k could not separate
        // goggles (sky) from boots (ground).  The class decides.
        private _matClass = [_obj, _selName] call FUNC(getSelectionMaterials);
        if (_matClass == "glass" || _matClass == "plastic") then { _fGround = 0.2; };
        if (_matClass == "leather" || _matClass == "rubber") then { _fGround = 0.7; };

        // Loadout flux: the carried item's thermal inertia scales the
        // body's heat reaching this selection.  A heavy backpack warms
        // slower (lower flux); metal gear (mags, radios) warms fast.
        // Key is the selection NAME alone; the map is already per unit, so the
        // old "obj|name" format converted an OBJECT to a string every tick.
        private _loadoutFlux = _loadoutMap getOrDefault [_selName, 1];
        if !(_loadoutFlux isEqualType 0) then { _loadoutFlux = 1; };

        [_obj, _selName, "", 0, _fGround, _loadoutFlux] call FUNC(applySelectionThermal);
        _applied = _applied + 1;
    } forEach _selections;
} forEach (allUnits);

_applied
