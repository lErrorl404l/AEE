#include "..\script_component.hpp"

/*
Atmospheric dust particles — airborne dust driven by wind speed and
surface dryness.

Pattern adapted from TPW MODS dust storm (tpw_fog.sqf) and ANZACSAS
Helicopter Dust (CfgSurfaces). Creates #particlesource billboards in
a volume around the player when wind exceeds a threshold and the
surface is dry/dusty.

Gate:    GVAR(enabled) && hasInterface
Reads:   wind, surfaceType, EGVAR(core,dustSuppression), overcast
Emits:   Billboard particles coloured by biome dust type
*/

if (!EGVAR(core,enabled)) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

private _windSpeed = vectorMagnitude wind;
if (_windSpeed < 5) exitWith {};

// Guard: skip if an existing dust source is still alive (prevents stacking)
private _existing = missionNamespace getVariable [QGVAR(atmosphericDust), objNull];
if (!isNull _existing && alive _existing) exitWith {};

// Dust suppression from AEE core (1 = full dust, 0 = suppressed)
private _dustSuppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 0.5];
if (_dustSuppression < 0.05) exitWith {};

// Rain suppresses airborne dust
private _rain = rain;
if (_rain > 0.3) exitWith {};

// Ground state affects dust availability
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _surfaceMultiplier = 1;
switch (_groundState) do {
    case "Dusty":   { _surfaceMultiplier = 2.0; };
    case "Mud":     { _surfaceMultiplier = 0.2; };
    case "Snow":    { _surfaceMultiplier = 0.1; };
    case "Dry":     { _surfaceMultiplier = 1.5; };
};

// Wind speed → density factor (0 at 5 m/s, 1 at 20 m/s)
private _windFactor = ((_windSpeed - 5) / 15) min 1;

// Combined density
private _density = _windFactor * _dustSuppression * _surfaceMultiplier;
if (_density < 0.05) exitWith {};

// Colour palette — warm tan for desert, grey-brown for temperate
private _biome = missionNamespace getVariable [QEGVAR(core,biome), "Cfb"];
private _dustColor = [0.7, 0.6, 0.4]; // default: warm tan
switch (true) do {
    case (_biome in ["BWh", "BSh", "BWk"]): { _dustColor = [0.8, 0.7, 0.5]; };
    case (_biome in ["Dfb", "Dfc"]):        { _dustColor = [0.5, 0.45, 0.35]; };
    case (_biome in ["ET", "EF"]):           { _dustColor = [0.85, 0.85, 0.8]; };
};

// Spawn atmospheric dust volume around player
private _dust = "#particlesource" createVehicleLocal getPosASL _player;
_dust attachTo [_player, [0, 0, 0]];
missionNamespace setVariable [QGVAR(atmosphericDust), _dust];

private _lifetime = 8 + random 4;
private _size = 30 + _windSpeed * 2;
private _alpha = 0.08 * _density;

_dust setParticleParams [
    ["\A3\data_f\ParticleEffects\Universal\Universal.p3d", 0, 2],
    "",
    "billboard",
    1,                          // sort
    _lifetime,                  // lifeTime
    [0, 0, 0],                 // position
    [0, 0, 0],                 // rotationVelocity
    1,                          // weight (1.275 = sinks slowly)
    1.0,                        // volume
    0.05,                       // rubbing (wind interaction)
    [_size, _size * 1.5],       // size progression
    [_dustColor + [0], _dustColor + [_alpha], _dustColor + [0]], // colour progression
    [1000],                     // animSpeed
    1,                          // angle
    0,                          // random dir
    "", "",                     // on surface, before destroy
    _player,                    // attach to
    0, true                     // bounce, imprecise
];

_dust setParticleRandom [
    1,                          // randomness type
    [100, 100, 30],             // position randomisation
    [0, 0, 0],                  // velocity randomisation
    0,                          // rotation randomisation
    0,                          // size randomisation
    [0, 0, 0, 0.1],            // colour randomisation
    0, 0
];

_dust setDropInterval (0.1 / _density); // denser = more drops

// Clean up after lifetime + buffer
[_dust, _lifetime + 2] spawn {
    params ["_source", "_delay"];
    sleep _delay;
    deleteVehicle _source;
};
