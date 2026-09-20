#include "..\..\script_component.hpp"
/*
 * Position-based ground temperature (issue #204).
 *
 * The terrain cannot be re-textured at runtime (no setTerrainTexture in
 * the RV engine - the satellite layer is baked into the map).  The
 * closest physically-honest equivalent: read the SURFACE TYPE at a
 * position (surfaceType / surfaceTexture) and return a temperature for
 * that surface.  Different materials store and release heat at
 * different rates - asphalt and concrete have high thermal mass and
 * stay warmer through the night, soil and grass cool faster, water
 * tracks the air slowly.
 *
 * This is the "terrain painting" that is actually achievable: instead
 * of changing the ground's colour, we change its TEMPERATURE by
 * position, so a road renders warmer than the adjacent soil at night
 * and the boundary blends (the contact conduction between a vehicle's
 * tyres and the warmer tarmac then transfers that heat into the tyres).
 *
 * The engine's surfaceType returns an OMLET / CfgSurfaces entry name
 * (e.g. "grass_short", "asphalt", "concrete", "sand", "dirt",
 * "rock", "water").  The thermal mass factor comes from CfgSurfaces
 * >> surface >> dust (the material class).
 *
 * Params:
 *   0: _pos (ARRAY, PositionASL or PositionAGL) - the world position.
 *   1: _airTemp (SCALAR, optional) - the ambient air temperature.  The
 *      ground deviates from the air by the surface's thermal mass.
 *
 * Returns: SCALAR - the ground temperature (C) at that position.
 */
params ["_pos", ["_airTemp", -999, [0]]];

if (_airTemp < -900) then {
    _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
    if !(_airTemp isEqualType 0) then { _airTemp = 15; };
};

// The surface type at the position (returns the CfgSurfaces entry).
private _surf = surfaceType _pos;
if (_surf == "") then { _surf = "grass_short"; };

// Thermal-mass factor per surface class: how much the surface deviates
// from the air temperature at night.  Positive = stays warmer than air
// (high thermal mass: asphalt, concrete, rock), negative = cooler
// (evaporative cooling: water, wet ground), near zero = tracks air
// (soil, grass).
private _deviation = switch (toLower _surf) do {
    // Roads / hard surfaces: high thermal mass, stay warm at night.
    case "asphalt": { 4.0 };
    case "concrete": { 4.0 };
    case "pavement": { 3.5 };
    // Rock: slow to cool.
    case "rock": { 2.5 };
    case "rock_light": { 2.0 };
    // Bare soil / dirt: moderate.
    case "dirt": { 1.0 };
    case "soil": { 1.0 };
    case "sand": { 1.5 };    // dry sand holds some daytime heat
    case "gravel": { 2.0 };
    // Vegetation / grass: tracks air, slight evaporative cooling.
    case "grass_short": { 0.0 };
    case "grass_tall": { -0.5 };
    case "reed": { -0.5 };
    case "wood": { -0.5 };
    case "forest": { -0.5 };
    case "bush": { -0.5 };
    // Water / wet: high specific heat, tracks air slowly but surface
    // evaporates - reads cool relative to a warm air mass, warm
    // relative to a cold one.  Keep it near air (the water model in
    // core handles the bulk).
    case "water": { 0.0 };
    case "water_shallow": { 0.0 };
    default { 0.0 };
};

// Day/night weighting: the deviation is a NIGHT effect (stored heat).
// In full daylight the sun term dominates and the ground converges to
// the air + solar loading; the deviation fades with solar radiation.
private _radiation = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), 0];
if !(_radiation isEqualType 0) then { _radiation = 0; };
_radiation = _radiation max 0 min 1;
private _nightWeight = 1 - _radiation;

(_airTemp + (_deviation * _nightWeight))
