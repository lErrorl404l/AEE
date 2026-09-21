#include "..\..\script_component.hpp"
/*
Per-selection NIR reflectance (issue #119, the rvmat material split).

The uniform NIR (fnc_getClothingInsulation) covers the BODY.  But the
player model's selections have different materials - a plate carrier
has cloth pouches, metal magazine pouches, plastic buckles - and each
reflects NIR differently.  The NVG sees the AVERAGE of the visible
selections, not just the uniform.

This resolves the per-selection NIR by material class (the thermal
module's fnc_getSelectionMaterials classifies each selection from its
rvmat).  The NIR values are the researched material reflectances:

  cloth   0.40  (the uniform baseline - camo fabric)
  metal   0.55  (magazine pouches, buckles, zippers - bright under NVG)
  plastic 0.30  (buckles, snaps)
  rubber  0.10  (dark synthetic - the black-hole partial)
  glass   0.15  (goggle lenses)
  wood    0.35  (stock furniture)
  ground  0.45  (unknown selection - the vegetation baseline)

The area-weighted average across the unit's selections is the
signature the NVG tube actually sees.  This is the per-material split
the issue's "rvmats on mags vs rvmats on cloth" requires.

Arguments:
  0: unit (OBJECT, default player)

Returns the area-weighted NIR reflectance 0..1.
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { 0.40 };

private _nirByMat = createHashMapFromArray [
    ["cloth", 0.40], ["metal", 0.55], ["plastic", 0.30],
    ["rubber", 0.10], ["glass", 0.15], ["wood", 0.35],
    ["ground", 0.45]
];

// Walk the unit's visible selections, classify each, weight by the
// selection's bounding-box size (a big cloth torso dominates a small
// metal buckle).
private _total = 0;
private _weight = 0;
private _sels = selectionNames _unit;
private _nir = 0.45;   // fallback: the vegetation baseline
if (_sels isNotEqualTo []) then {
    {
        private _sel = _x;
        private _mat = [_unit, _sel] call EFUNC(thermal,getSelectionMaterials);
        private _selBB = _unit selectionPosition [_sel, "BoundingBox"];
        private _selSize = vectorMagnitude _selBB;
        // selections without a bounding box (hidden geometry) get a
        // small weight so they do not dominate the average
        private _w = [0.05, _selSize] select (_selSize > 0.01);
        _nir = _nir + (_nirByMat getOrDefault [_mat, 0.40]) * _w;
        _total = _total + _w;
        _weight = _weight + 1;
    } forEach _sels;
    if (_total > 0) then { _nir = _nir / _total; };
};
_nir max 0 min 1

