#include "..\script_component.hpp"
/*
Classify an engine surfaceType result into an AEE material class
(issue #96, layer 1 - terrain taxonomy).

The engine `surfaceType` command returns a Gdt* class for terrain
(the map's own CfgSurfaces entries).  This is the fastest and most
complete source for GROUND material: it covers every map's terrain with
zero per-mod work, because every terrain surface class is engine-exposed
this way.  The biome scan (fnc_scanTerrainSignals) already uses these
classes for climate votes; this function maps them to the physical
material class for thermal/traction/acoustic consumers.

Arguments:
  0: surface type (STRING) - the surface class name, for example GdtAsphalt

Return Value:
  STRING - ground, rock, wood, concrete, asphalt, metal, glass, water,
  vegetation, or "ground" for unknown

Example:
  "GdtAsphalt" call aee_material_fnc_classifyBySurfaceType -> "asphalt"
  "GdtConcrete" call aee_material_fnc_classifyBySurfaceType -> "concrete"
*/

params [["_surface", "", [""]]];
_surface = toLower _surface;

// ─── Dynamic first (issue #204): the engine's own material keyword ───────
// A custom or modded surface (GdtCustomConcrete, GdtCustomAsphalt...)
// has a CfgSurfaces entry whose soundHit/soundEnviron field carries the
// PHYSICAL material keyword - the map maker's own classification, no
// static naming required.  Try the config lookup FIRST (it also reads
// the .bisurf file when the config class is absent), and only fall back
// to the static switch below for the known #gdt* primitives.  Without
// this, GdtCustomConcrete fell through to 'ground' and the concrete
// never warmed from muzzle flash or sun (the user's report).
private _dynamicMat = "";
if (_surface != "") then {
    // The surface may come as "#gdtconcrete" (with #) or the class
    // "gdtcustomconcrete" (lowercased).  The CfgSurfaces classes are
    // Gdt* WITH the prefix - keep it for the config lookup (the bare
    // stripped name misses the config class and the bisurf fallback
    // fires on a non-path, warning 'Script X not found').  Only the
    // leading # is removed; the Gdt prefix is kept.
    private _clean = _surface;
    if (_clean find "#gdt" == 0) then { _clean = _clean select [4, (count _clean) - 4]; };
    _dynamicMat = _clean call EFUNC(material,getSurfaceMaterial);
};
if (_dynamicMat != "" && _dynamicMat != "ground") exitWith { _dynamicMat };

// The static switch below compares the BARE surface token.  The engine
// returns "GdtAsphalt" (no '#'), and a caller may pass an already-stripped
// token ("asphalt") or the legacy "#gdtasphalt" form.  Normalise on read.
private _name = _surface;
if (_name find "#gdt" == 0) then { _name = _name select [4]; }
else { if (_name find "gdt" == 0) then { _name = _name select [3]; }; };

private _material = switch (true) do {
    // Snow/ice/glacier/tundra: frozen ground.
    case (_name in ["snow", "ice", "glacier"]): { "ground" };
    case (_name in ["tundra"]): { "ground" };
    // Rock/mountain: hard stone.
    case (_name in ["rock", "mountain", "gravel"]): { "rock" };
    // Desert/sand/dunes: loose ground.
    case (_name in ["desert", "dunes", "sand", "prairie"]): { "ground" };
    // Paved surfaces: asphalt roads, concrete/sidewalk.  The engine
    // CfgSurfaces defines GdtAsphalt and GdtConcrete (SurfRoadTarmac,
    // SurfRoadConcrete); tarmac absorbs far more solar than soil, so it
    // must NOT fall through to ground (issue #124 per-position ground).
    case (_name in ["asphalt", "tarmac", "road"]): { "asphalt" };
    case (_name in ["concrete", "sidewalk"]): { "concrete" };
    // Vegetation: grass, forest, jungle, crop, vineyard, orchard.
    case (_name in ["grass", "grassland", "forest", "jungle",
        "rainforest", "coniferous", "crop", "field",
        "vineyard", "orchard"]): { "vegetation" };
    // Wetland: swamp/marsh - waterlogged ground.
    case (_name in ["swamp", "marsh"]): { "water" };
    // Open water: the engine surface classes for sea/lake/river.  A
    // surfaceType at sea returns the water class, NOT land.
    case (_name in ["sea", "ocean", "lake", "river",
        "water"]): { "water" };
    // Custom / modded surfaces (issue #204): GdtCustomConcrete,
    // GdtCustomAsphalt, a modded concrete surface.  The map's own surface names
    // often embed the material keyword.  Match by CONTAINS - the
    // material class is in the name (GdtCustomCONCRETE = concrete,
    // GdtCustomDRYGRASS = grass).  This is the dynamic, no-static-
    // naming fallback for surfaces the CfgSurfaces soundHit lookup
    // could not resolve.
    case ("concrete" in _name): { "concrete" };
    case ("asphalt" in _name || {"tarmac" in _name} || {"road" in _name}): { "asphalt" };
    case ("gravel" in _name || {"pebble" in _name}): { "rock" };
    case ("rock" in _name || {"stone" in _name} || {"cliff" in _name}): { "rock" };
    case ("grass" in _name || {"meadow" in _name} || {"field" in _name}): { "vegetation" };
    case ("forest" in _name || {"wood" in _name} || {"jungle" in _name}): { "vegetation" };
    case ("sand" in _name || {"dune" in _name} || {"desert" in _name}): { "ground" };
    case ("mud" in _name || {"swamp" in _name} || {"marsh" in _name}): { "water" };
    case ("snow" in _name || {"ice" in _name} || {"glacier" in _name}): { "ground" };
    // Anything else: neutral ground.
    default { "ground" };
};

_material
