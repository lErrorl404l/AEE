#include "..\..\script_component.hpp"
/*
Organic muzzle-blast ground stain (issue #204).

A real muzzle blast does NOT leave a perfect circular heat mark.  The
hot gas vents forward and sideways from the muzzle device, the shape is
irregular, and it depends on the weapon, the gas volume, the barrel, and
the muzzle brake - then it grows, fades, and dissipates.  A single
feathered circle tile would read as fake.

This spawns a BLOB of small overlapping feathered decals (3-5) with
random scatter and rotation, elongated along the firing axis - the
irregular shape of a real gas footprint.  Each decal is painted from
the feathered heat-tile set (ground_heat_XX.paa) at an intensity that
scales with the barrel heat, then the blob fades over time (paints
cooler tiles) and deletes itself.

The physics side (fnc_applyExhaustHeat -> addGroundStamp) is separate
and unchanged: it warms the ground temperature field.  This is the
VISUAL stain only, layered on top.

Arguments:
  0: position (ASL, the muzzle point)
  1: facing vector (projectile velocity direction, normalised)
  2: intensity (0..1, scales with weaponHeat)
  3: weapon gas scale (1 default; suppressors/bare muzzles vary)
*/
params [
    ["_pos", [0,0,0], [[]], [3]],
    ["_facing", [0,1,0], [[]], [3]],
    ["_intensity", 0.5, [0]],
    ["_gasScale", 1, [0]]
];
if (_intensity <= 0.01) exitWith { [] };
if !(hasInterface) exitWith { [] };

// The stain is client-local visual; the ground physics already ran.
// Normalise the facing and drop its vertical component (the stain is
// on the ground, elongated along the horizontal gas direction).
_facing set [2, 0];
private _fLen = vectorMagnitude _facing;
if (_fLen < 0.01) then {
    _facing = [0, 1, 0];
} else {
    _facing = _facing vectorMultiply (1 / _fLen);
};
private _perp = [-(_facing select 1), _facing select 0, 0];

// Blob size grows with intensity and gas scale: more gas = wider, longer
// footprint.  Real muzzle devices vent forward + sideways, so the stain
// is longer along the axis than across it.
private _lenScale = 0.6 + 1.4 * _intensity * _gasScale;
private _widthScale = 0.4 + 0.7 * _intensity;

// Heat band for this intensity (8 tile levels).
private _heatLevel = round ((1 - _intensity) * 7);
private _heatTiles = [];
for "_i" from 0 to 7 do {
    _heatTiles pushBack format ["\z\aee\addons\thermal\data\ground\ground_heat_%1.paa", _i];
};

// 3-5 decals, random scatter + rotation, elongated forward.
private _count = 3 + (floor random 3);
private _decals = [];
for "_i" from 0 to (_count - 1) do {
    // Scatter: forward-biased (gas vents forward), sideways spread.
    private _fwd = (random 0.8) * _lenScale;
    private _side = ((random 1.4) - 0.7) * _widthScale;
    private _offset = (_facing vectorMultiply _fwd) vectorAdd (_perp vectorMultiply _side);
    private _dPos = _pos vectorAdd _offset;
    _dPos set [2, 0];

    private _decal = createVehicle ["Land_DirtPatch_03_F", _dPos, [], 0, "CAN_COLLIDE"];
    _decal setDir (random 360);
    // Varying scale per decal -> the irregular blob edge.
    private _s = (0.5 + random 0.6) * (_lenScale min 2);
    _decal setObjectScale _s;
    // TI-readable material FIRST (issue #204): the decal's own material
    // has a StageTI that renders its cold grey in the TI pass, hiding
    // our painted tile.  Swap to the FPN rvmat (white Stage1 the tile
    // overrides + perlinNoise Stage2) - the same swap that made the
    // object FPN test work - THEN paint the heat tile.
    _decal setObjectMaterial [0, "\z\aee\addons\thermal\data\ti_fpn.rvmat"];
    _decal setObjectTexture [0, _heatTiles select _heatLevel];
    _decals pushBack _decal;
};

// Fade over time: cooler tiles as the gas dissipates, then delete.
// Total life scales with intensity (bigger blast = longer-lived mark).
private _life = 8 + 12 * _intensity;
private _steps = 8;
private _stepTime = _life / _steps;
for "_s" from 1 to _steps do {
    [
        {
            params ["_decals", "_tiles", "_level"];
            {
                if (!isNull _x) then {
                    _x setObjectTexture [0, _tiles select _level];
                };
            } forEach _decals;
        },
        [_decals, _heatTiles, (_heatLevel + _s) min 7],
        _stepTime * _s
    ] call CBA_fnc_waitAndExecute;
};

[
    {
        params ["_decals"];
        { if (!isNull _x) then { deleteVehicle _x }; } forEach _decals;
    },
    [_decals],
    _life + 1
] call CBA_fnc_waitAndExecute;

_decals
