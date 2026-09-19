#include "..\script_component.hpp"
/*
Preload the vanilla bisurf material cache (issue #96, layer 2/3).

The engine resolves each object's material per-model: geometry LOD →
rvmat → surfaceInfo → bisurf.  The bisurf file is a shared,
path-addressed physical-property table (density, thickness, rough,
dust, bulletPenetrability, soundEnviron, isWater, friction,
restitution).  Most objects from ANY mod reference the vanilla
`A3\data_f\Penetration\*.bisurf` paths, so preloading them covers the
majority of objects with zero per-mod work.

The paths below are the 81 bisurfs verified present in the vanilla
data_f.pbo (2026-09-19, inspected with armake).  The cache maps each
path to its AEE material class.  A hit that references a path NOT in
this cache falls to the classifier (fnc_getSurfaceMaterial), which
reads the bisurf content and learns the class on first impact.

Classes: ground, rock, wood, concrete, metal, glass, water,
vegetation.  The engine-default unknown maps to "ground" (ACE3
convention - safest neutral default).

Output: none.  Populates GVAR(materialCache) and GVAR(classCache).
*/

GVAR(materialCache) = createHashMapFromArray [
    // Metal - armour, plate, engine, tank, vehicle interior, weapon.
    ["a3\data_f\penetration\armour.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_100mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_12mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_16mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_1mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_20mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_23mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_250mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_30mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_3mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_40mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_5mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_60mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_7mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_80mm.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_heavy.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_medium.bisurf", "metal"],
    ["a3\data_f\penetration\armour_plate_thin.bisurf", "metal"],
    ["a3\data_f\penetration\engine.bisurf", "metal"],
    ["a3\data_f\penetration\fueltank.bisurf", "metal"],
    ["a3\data_f\penetration\iron_cast.bisurf", "metal"],
    ["a3\data_f\penetration\iron_cast_plate.bisurf", "metal"],
    ["a3\data_f\penetration\metal.bisurf", "metal"],
    ["a3\data_f\penetration\metal_plate.bisurf", "metal"],
    ["a3\data_f\penetration\metal_plate_thin.bisurf", "metal"],
    ["a3\data_f\penetration\vehicle_interior.bisurf", "metal"],
    ["a3\data_f\penetration\weapon_plate.bisurf", "metal"],
    // Concrete - buildings, plates, dust particles.
    ["a3\data_f\penetration\building.bisurf", "concrete"],
    ["a3\data_f\penetration\building_dust_particle.bisurf", "concrete"],
    ["a3\data_f\penetration\building_dust_soft.bisurf", "concrete"],
    ["a3\data_f\penetration\building_plate.bisurf", "concrete"],
    ["a3\data_f\penetration\concrete.bisurf", "concrete"],
    ["a3\data_f\penetration\concrete_plate.bisurf", "concrete"],
    // Wood.
    ["a3\data_f\penetration\building_wood_particle.bisurf", "wood"],
    ["a3\data_f\penetration\wood.bisurf", "wood"],
    ["a3\data_f\penetration\wood_plate.bisurf", "wood"],
    // Glass - transparent, armoured, plexiglass.
    ["a3\data_f\penetration\glass.bisurf", "glass"],
    ["a3\data_f\penetration\glass_armored.bisurf", "glass"],
    ["a3\data_f\penetration\glass_armored_plate.bisurf", "glass"],
    ["a3\data_f\penetration\glass_plate.bisurf", "glass"],
    ["a3\data_f\penetration\plexiglass.bisurf", "glass"],
    ["a3\data_f\penetration\plexiglass_plate.bisurf", "glass"],
    // Rock - granite and coarse stone.
    ["a3\data_f\penetration\granite.bisurf", "rock"],
    ["a3\data_f\penetration\granite_plate.bisurf", "rock"],
    // Water.
    ["a3\data_f\penetration\water.bisurf", "water"],
    // Vegetation - foliage, palm, pine, hay, cactus.
    ["a3\data_f\penetration\cactus.bisurf", "vegetation"],
    ["a3\data_f\penetration\foliage.bisurf", "vegetation"],
    ["a3\data_f\penetration\foliage_dead.bisurf", "vegetation"],
    ["a3\data_f\penetration\foliage_dead_plate.bisurf", "vegetation"],
    ["a3\data_f\penetration\foliage_green.bisurf", "vegetation"],
    ["a3\data_f\penetration\foliage_green_big.bisurf", "vegetation"],
    ["a3\data_f\penetration\foliage_green_big_plate.bisurf", "vegetation"],
    ["a3\data_f\penetration\foliage_green_plate.bisurf", "vegetation"],
    ["a3\data_f\penetration\foliage_palm.bisurf", "vegetation"],
    ["a3\data_f\penetration\foliage_palm_plate.bisurf", "vegetation"],
    ["a3\data_f\penetration\foliage_pine.bisurf", "vegetation"],
    ["a3\data_f\penetration\foliage_pine_plate.bisurf", "vegetation"],
    ["a3\data_f\penetration\foliage_plate.bisurf", "vegetation"],
    ["a3\data_f\penetration\hay.bisurf", "vegetation"],
    // Ground - everything else: cloth, body, leather, meat, plastic,
    // rubber, tyre, soft/medium/hard ground, bell, void, default.
    ["a3\data_f\penetration\bell.bisurf", "ground"],
    ["a3\data_f\penetration\body.bisurf", "ground"],
    ["a3\data_f\penetration\cloth.bisurf", "ground"],
    ["a3\data_f\penetration\cloth_plate.bisurf", "ground"],
    ["a3\data_f\penetration\default.bisurf", "ground"],
    ["a3\data_f\penetration\hard_ground.bisurf", "ground"],
    ["a3\data_f\penetration\leather.bisurf", "ground"],
    ["a3\data_f\penetration\meat.bisurf", "ground"],
    ["a3\data_f\penetration\meatbones.bisurf", "ground"],
    ["a3\data_f\penetration\medium_ground.bisurf", "ground"],
    ["a3\data_f\penetration\plastic.bisurf", "ground"],
    ["a3\data_f\penetration\plastic_plate.bisurf", "ground"],
    ["a3\data_f\penetration\rubber.bisurf", "ground"],
    ["a3\data_f\penetration\soft_ground.bisurf", "ground"],
    ["a3\data_f\penetration\tyre.bisurf", "ground"],
    ["a3\data_f\penetration\tyre_armored.bisurf", "ground"],
    ["a3\data_f\penetration\void.bisurf", "ground"]
];

// Per-object-class cache: typeOf object -> material class, learned on
// first impact (layer 3).  Populated by fnc_handleHitPart.
GVAR(classCache) = createHashMap;
