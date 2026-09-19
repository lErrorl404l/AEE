#include "..\script_component.hpp"
/*
Learn a surface's material class from a projectile HitPart event
(issue #96, layer 3 - HitPart learning).

Every projectile impact fires the HitPart event with the surface type
(the 9th parameter): a CfgSurfaces class or a bisurf path.  The surface
identifier classifies to an AEE material class, which is cached per
SURFACE (bisurf path) - not per object class, because objects are
multi-material: a vehicle hit on the window is glass, on the body is
metal, on a tyre is rubber.  The per-surface answer is the granularity
thermal/traction/acoustic consumers need, and it is exactly the
materialCache key.

The classifier (fnc_getSurfaceMaterial) already caches the surface->
material mapping, so this handler is just the wiring that feeds the
cache from real impacts: any surface from ANY mod is classified and
cached on FIRST impact - no per-mod config, no pre-ship knowledge.

The event is registered on every fired projectile in XEH_preInit.  The
handler is deliberately cheap: one function call; the classifier caches
internally, so the second hit on the same surface is a hashmap read.

Arguments:
  0: projectile (OBJECT, ignored)
  1: object hit (OBJECT)
  3: position (ignored)
  5: surface normal (ignored)
  8: surface type (STRING) - CfgSurfaces class or bisurf path

Return Value:
  None
*/

params ["_projectile", "_target", "", "_lastPos", "_lastVelocity", "_surfaceNorm", "", "", "_surfaceType"];

if (isNull _target || _surfaceType == "") exitWith {};

// Classify and cache per surface.  fnc_getSurfaceMaterial caches the
// result in GVAR(materialCache) - no separate class cache needed.
_surfaceType call FUNC(getSurfaceMaterial);
