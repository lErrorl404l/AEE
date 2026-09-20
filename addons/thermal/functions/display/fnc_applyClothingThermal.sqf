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
if (_mode == "EXIT") then {
    ["", "", "EXIT"] call FUNC(applySelectionThermal);
    0
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

// ─── Apply to ALL units (no radius: one-shot texture is cheap) ────────────
private _applied = 0;
{
    if (isNull _x || !alive _x) then { continue; };
    private _obj = _x;

    // Dynamic thermal-selection discovery (issue #204): Men = all
    // texture slots, cached per class.  No static name matching.
    private _selections = [_obj] call FUNC(getThermalSelections);
    if (count _selections == 0) then { continue; };

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
    {
        private _selIdx = _x;
        private _fGround = 0.5;
        // Selection NAME for the material detector (it keys on names).
        private _selName = if (_obj isKindOf "Man") then {
            private _names = selectionNames _obj;
            if (_selIdx < count _names) then { _names select _selIdx } else { "" }
        } else {
            private _hs = getArray (configOf _obj >> "hiddenSelections");
            if (_selIdx < count _hs) then { _hs select _selIdx } else { "" }
        };
        if (_selName == "") then { continue; };
        // Material-driven view factor: low-k (glass, plastic, goggles)
        // faces mostly sky; rubber/leather (boots) sees mostly ground.
        private _matClass = [_obj, _selName] call FUNC(getSelectionMaterials);
        private _matDef = _matClass call FUNC(getMaterialThermal);
        private _k = _matDef select 4;
        if !(_k isEqualType 0) then { _k = 0; };
        if (_k <= 1.5) then { _fGround = 0.2; };
        if (_k >= 0.2 && _k <= 2.0) then { _fGround = 0.7; };

        [_obj, _selName, "", 0, _fGround] call FUNC(applySelectionThermal);
        _applied = _applied + 1;
    } forEach _selections;
} forEach (allUnits);

_applied
