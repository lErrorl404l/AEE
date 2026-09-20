#include "..\script_component.hpp"
/*
Classify an engine surfaceType result into an AEE material class
(issue #96, layer 1 - terrain taxonomy).

The engine `surfaceType` command returns a `#gdt*` class for terrain
(the map's own CfgSurfaces entries).  This is the fastest and most
complete source for GROUND material: it covers every map's terrain with
zero per-mod work, because every terrain surface class is engine-exposed
this way.  The biome scan (fnc_scanTerrainSignals) already uses these
classes for climate votes; this function maps them to the physical
material class for thermal/traction/acoustic consumers.

Arguments:
  0: surface type (STRING) - the `#gdt...` engine value, lower-cased

Return Value:
  STRING - ground, rock, wood, concrete, asphalt, metal, glass, water,
  vegetation, or "ground" for unknown

Example:
  "#gdtasphalt" call aee_material_fnc_classifyBySurfaceType -> "asphalt"
  "#gdtconcrete" call aee_material_fnc_classifyBySurfaceType -> "concrete"
*/

params [["_surface", "", [""]]];
_surface = toLower _surface;

// ─── Dynamic first (issue #204): the engine's own material keyword ───────
// A custom or modded surface (GdtStratisConcrete, GdtCustomAsphalt...)
// has a CfgSurfaces entry whose soundHit/soundEnviron field carries the
// PHYSICAL material keyword - the map maker's own classification, no
// static naming required.  Try the config lookup FIRST (it also reads
// the .bisurf file when the config class is absent), and only fall back
// to the static switch below for the known #gdt* primitives.  Without
// this, GdtStratisConcrete fell through to 'ground' and the concrete
// never warmed from muzzle flash or sun (the user's report).
private _dynamicMat = "";
if (_surface != "") then {
    // The surface may come as "#gdtconcrete" (with #) or the bare class
    // "GdtStratisConcrete" (surfaceType returns the bare name at runtime
    // in some builds).  Try both forms.
    private _clean = _surface;
    if (_clean find "#gdt" == 0) then { _clean = _clean select [4, (count _clean) - 4]; };
    _dynamicMat = _clean call EFUNC(material,getSurfaceMaterial);
};
if (_dynamicMat != "" && _dynamicMat != "ground") exitWith { _dynamicMat };

private _material = switch (true) do {
    // Snow/ice/glacier/tundra: frozen ground.
    case (_surface in ["#gdtsnow", "#gdtice", "#gdtglacier"]): { "ground" };
    case (_surface in ["#gdttundra"]): { "ground" };
    // Rock/mountain: hard stone.
    case (_surface in ["#gdtrock", "#gdtmountain", "#gdtgravel"]): { "rock" };
    // Desert/sand/dunes: loose ground.
    case (_surface in ["#gdtdesert", "#gdtdunes", "#gdtsand", "#gdtprairie"]): { "ground" };
    // Paved surfaces: asphalt roads, concrete/sidewalk.  The engine
    // CfgSurfaces defines GdtAsphalt and GdtConcrete (SurfRoadTarmac,
    // SurfRoadConcrete); tarmac absorbs far more solar than soil, so it
    // must NOT fall through to ground (issue #124 per-position ground).
    case (_surface in ["#gdtasphalt", "#gdttarmac", "#gdtroad"]): { "asphalt" };
    case (_surface in ["#gdtconcrete", "#gdtsidewalk"]): { "concrete" };
    // Vegetation: grass, forest, jungle, crop, vineyard, orchard.
    case (_surface in ["#gdtgrass", "#gdtgrassland", "#gdtforest", "#gdtjungle",
        "#gdtrainforest", "#gdtconiferous", "#gdtcrop", "#gdtfield",
        "#gdtvineyard", "#gdtorchard"]): { "vegetation" };
    // Wetland: swamp/marsh - waterlogged ground.
    case (_surface in ["#gdtswamp", "#gdtmarsh"]): { "water" };
    // Open water: the engine surface classes for sea/lake/river.  A
    // surfaceType at sea returns the water class, NOT land.
    case (_surface in ["#gdtsea", "#gdtocean", "#gdtlake", "#gdtriver",
        "#gdtwater"]): { "water" };
    // Anything else: neutral ground.
    default { "ground" };
};

_material
