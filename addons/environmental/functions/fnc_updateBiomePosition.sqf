#include "..\script_component.hpp"

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
private _override = QGVAR(biomeOverride) call CBA_fnc_getSetting;
if (_override != "AUTO") exitWith {
    private _current = GVAR(biome);
    if (_current != _override) then {
        GVAR(biome) = _override;
        GVAR(biomeName) = [_override] call EFUNC(environmental,getBiomeName);
    };
};

// ─── Sample biome at current position ─────────────────────────────────
private _newBiome = [_posASL] call EFUNC(environmental,getBiomeAtPosition);

// ─── Update if changed ────────────────────────────────────────────────
private _current = GVAR(biome);
if (_newBiome != _current) then {
    GVAR(biome) = _newBiome;
    GVAR(biomeName) = [_newBiome] call EFUNC(environmental,getBiomeName);
};
