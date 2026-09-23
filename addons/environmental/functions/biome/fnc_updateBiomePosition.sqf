#include "..\..\script_component.hpp"

// ─── Per-position biome update ────────────────────────────────────────
// Samples the biome at the player's current position using surface type,
// latitude, and elevation. Updates aee_core_biome when position changes
// significantly (beyond transition radius).
//
// Called from fnc_updateEnvironment on each PFH tick.
// The biomeOverride CBA setting takes priority over auto-detection.
//
// Arguments: [_posASL]
//   0: Position ASL [x, y, z]

params ["_posASL"];

// ─── Check for global override ────────────────────────────────────────
// CBA settings are exposed as missionNamespace variables under the
// setting name. Read directly (CBA_fnc_getSetting is not in all CBA
// builds). Default "AUTO" = auto-detect.
private _override = missionNamespace getVariable [QEGVAR(core,biomeOverride), "AUTO"];
if (_override != "AUTO") exitWith {
    private _current = missionNamespace getVariable [QEGVAR(core,biome), ""];
    if (_current != _override) then {
        missionNamespace setVariable [QEGVAR(core,biome), _override];
        missionNamespace setVariable [QEGVAR(core,biomeName), [_override] call EFUNC(environmental,getBiomeName)];
    };
};

// ─── Sample biome at current position ─────────────────────────────────
// The smoothing sampler resolves the boundary: it samples the ring at
// the biomeTransitionRadius setting and returns the dominant biome, so a
// position near an edge reads as its neighbourhood rather than as the
// single tile it stands on.
private _newBiome = [_posASL] call EFUNC(environmental,getSmoothedBiome);

// ─── Update if changed ────────────────────────────────────────────────
private _current = missionNamespace getVariable [QEGVAR(core,biome), ""];
if (_newBiome != _current) then {
    missionNamespace setVariable [QEGVAR(core,biome), _newBiome];
    missionNamespace setVariable [QEGVAR(core,biomeName), [_newBiome] call EFUNC(environmental,getBiomeName)];
};
