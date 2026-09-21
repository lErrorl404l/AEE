#include "..\..\script_component.hpp"
/*
Road-LOD proxy-plane test (issue #204).

Bullet holes and footprints show in TI because the engine renders them
into the terrain SURFACE pass (r_decals).  Object decals (Land_DirtPatch)
and particles (drop) do NOT enter that pass.  Road decals DO - they have
a Roadway LOD that composites into the terrain render, and roads are
visible in vanilla thermals.

This spawns a runway concrete piece (runway_beton_F.p3d) as a simple
object, paints it with the mid heat tile, and scales it to a 5m tile.
If the heat colour reads in TI, the road-LOD proxy plane is the terrain
heat overlay mechanism.

Usage (debug console):
    [] call aee_thermal_fnc_debugRoadTest;
*/
private _pos = player modelToWorld [0, 3, 0];
_pos set [2, 0];
private _plane = createSimpleObject ["a3\roads_f\runway\runway_beton_F.p3d", _pos];
_plane setObjectScale 0.3;
_plane setObjectTexture [0, "\z\aee\addons\thermal\data\ground\ground_heat_04.paa"];
systemChat format ["AEE road test: spawned runway_beton at %1", _pos];

[]
