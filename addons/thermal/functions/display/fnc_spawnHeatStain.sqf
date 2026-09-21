#include "..\..\script_component.hpp"
/*
Organic muzzle-blast ground stain (issue #204) - TI-visible version.

A real muzzle blast does NOT leave a perfect circular heat mark.  The
hot gas vents forward and sideways from the muzzle device, the shape is
irregular, and it depends on the weapon, the gas volume, the barrel, and
the muzzle brake - then it grows, fades, and dissipates.

The object-decal route (Land_DirtPatch_03_F) FAILED: those decals
render as terrain-surface projections that the TI pass ignores, so the
heat paint never reached the thermal image (bullet holes and footprints
show because the engine draws them through its OWN decal renderer,
which TI reads).

This version uses the SAME renderer the engine uses for persistent
ground marks: a `drop` billboard with onSurface, rendered flat on the
terrain via the UniversalOnSurface particle family.  Painted with our
feathered heat tile + WHOT-red colour, it enters the TI pass like a
bullet hole.

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

// Blob size grows with intensity and gas scale: more gas = wider,
// longer footprint.  Muzzle devices vent forward + sideways, so the
// stain is longer along the axis than across it.
private _lenScale = 0.6 + 1.4 * _intensity * _gasScale;

// 3-5 decals, random scatter + rotation, elongated forward.  Each is a
// drop-billboard laid flat on the surface - the TI-visible renderer.
private _count = 3 + (floor random 3);
private _tile = format ["\z\aee\addons\thermal\data\ground\ground_heat_%1.paa", round ((1 - _intensity) * 7)];
for "_i" from 0 to (_count - 1) do {
    // Scatter: forward-biased (gas vents forward), sideways spread.
    private _fwd = (random 0.8) * _lenScale;
    private _side = ((random 1.4) - 0.7) * _lenScale;
    private _perp = [-(_facing select 1), _facing select 0, 0];
    private _offset = (_facing vectorMultiply _fwd) vectorAdd (_perp vectorMultiply _side);
    private _dPos = _pos vectorAdd _offset;
    _dPos set [2, 0];

    // drop (ParticleArray): the color element carries the WHOT red
    // fading out; onSurface lays it flat on the terrain like the
    // engine's own ground decals (bullet holes, mine waves).
    private _life = 8 + 12 * _intensity;
    private _size = (0.5 + random 0.6) * (_lenScale min 2);
    drop [
        [_tile, 1, 0, 1, 0],           // texture, ntieth, index, count, loop
        "",                            // animationName
        "Billboard",                   // particleType
        0.5,                           // timerPeriod
        _life,                         // lifetime
        _dPos,                         // position
        [0, 0, 0],                     // moveVelocity
        0,                             // rotationVelocity
        1,                             // weight
        1,                             // volume
        0.5,                           // rubbing
        [_size, _size],                // size over life
        [[1, 0.10, 0.20, 0.9], [1, 0.10, 0.20, 0]],  // color: WHOT-red fade
        [1000, 0],                     // animationSpeed
        0,                             // randomDirectionPeriod
        0,                             // randomDirectionIntensity
        "",                            // onTimerScript
        "",                            // beforeDestroyScript
        objNull,                       // object
        0,                             // angle
        true,                          // onSurface: lay flat on terrain
        0                              // bounceOnSurface: no bounce
    ];
};

[]
