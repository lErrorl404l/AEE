#include "..\..\script_component.hpp"
/*
Organic muzzle-blast ground stain (issue #204) - WORKING mechanism.

The terrain paint is Land_DirtPatch_03_F decals + setObjectTexture
["usertexture", tile] - the decal's engine-projected texture hook,
verified in-game to read differently in thermals from the ground.

A real muzzle blast does NOT leave a perfect circular heat mark.  The
hot gas vents forward and sideways from the muzzle device, the shape is
irregular, and it depends on the weapon, the gas volume, the barrel, and
the muzzle brake - then it grows, fades, and dissipates.

Each stain is 3-5 DirtPatch decals, randomly scattered and rotated,
elongated along the firing axis (the gas vent direction), painted with
the feathered heat tile.  The blob fades through the tile levels over
its lifetime, then deletes itself.

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

// Blob size in METRES: more gas = wider, longer footprint.  Muzzle
// devices vent forward + sideways, so the stain is longer along the
// axis than across it.
private _lenScale = 0.8 + 1.6 * _intensity * _gasScale;
private _widthScale = 0.5 + 0.8 * _intensity;

// Heat band for this intensity (8 tile levels).
private _heatLevel = round ((1 - _intensity) * 7);

// 3-5 DirtPatch decals, random scatter + rotation, elongated forward.
// Scale ~0.25..0.5 (2.5..5m pieces at the 10m natural size).
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
    private _s = (0.25 + random 0.25) * (0.6 + _lenScale * 0.3);
    _decal setObjectScale _s;
    _decal setObjectTexture ["usertexture", format ["\z\aee\addons\thermal\data\ground\ground_heat_%1.paa", _heatLevel]];
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
            params ["_decals", "_level"];
            {
                if (!isNull _x) then {
                    _x setObjectTexture ["usertexture", format ["\z\aee\addons\thermal\data\ground\ground_heat_%1.paa", _level]];
                };
            } forEach _decals;
        },
        [_decals, (_heatLevel + _s) min 7],
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
