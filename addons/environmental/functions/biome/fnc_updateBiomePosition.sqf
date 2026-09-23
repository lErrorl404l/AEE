#include "..\..\script_component.hpp"

// ─── Per-position biome detail ────────────────────────────────────────
// Samples the SURFACE at the player's position and publishes it as
// detail, never as the map's climate.
//
// aee_core_biome is the map-wide Koppen class, owned by fnc_getBiome.
// Fourteen consumers read it for a map-scoped purpose (fog normals, river
// level, crop state, radio loss, flood risk), so overwriting it per tick
// with a single tile's surface answer broke all of them. On Stratis the
// map-wide classifier correctly resolved Csa and this function replaced
// it with Cfb, because a man-made surface carries no climate signal.
//
// The map-wide verdict already fuses six factual terrain signals at far
// higher weight than one tile can: latitude, water fraction, model-path
// species, surface grid, structures and elevation. This function reports
// the local surface so a consumer that genuinely wants it can read it
// without disturbing the climate class.
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

// ─── Sample the surface at this position ──────────────────────────────
// The smoothing sampler resolves the boundary: it samples the ring at
// the biomeTransitionRadius setting and returns the dominant biome, so a
// position near an edge reads as its neighbourhood rather than as the
// single tile it stands on.
private _newBiome = [_posASL] call EFUNC(environmental,getSmoothedBiome);

// ─── Publish as local detail, not as the map climate ──────────────────
private _current = missionNamespace getVariable [QGVAR(localBiome), ""];
if (_newBiome != _current) then {
    missionNamespace setVariable [QGVAR(localBiome), _newBiome];
    missionNamespace setVariable [QGVAR(localBiomeName), [_newBiome] call EFUNC(environmental,getBiomeName)];
};
