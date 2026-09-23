#include "..\..\script_component.hpp"

/*
Rotor wash dust (helicopter in ground effect).

A helicopter close to the ground lifts the surface material into its
outwash: brownout over sand, whiteout over snow.  The engine throws no
dust for a rotor, so this drives it from the computed physics
(fnc_calculateDownwash) and the surface under the aircraft.

The cloud is not a puff under the rotor.  Real brownout surrounds the
aircraft: the flow spreads radially at the ground and then rolls up in the
blade-tip vortex, so the visible cloud is a ring that rises around the
fuselage.  The emitter reflects that: a wide ground ring, plus a vertical
lift component so the material rises around the aircraft rather than
settling straight back down.

Gate: enabled, a helicopter in ground effect, moving slowly or hovering,
   over a surface that lifts.

Argument:
  0: aircraft (OBJECT, default the player's vehicle)

Returns true when a source was started.
*/

params [["_aircraft", vehicle (call CBA_fnc_currentUnit), [objNull]]];
if (isNull _aircraft || !alive _aircraft) exitWith { false };
if (!(EGVAR(core,enabled))) exitWith { false };

// Helicopters only: a fixed-wing rotor wash is not this phenomenon.
if !(_aircraft isKindOf "Helicopter") exitWith { false };

// Ground effect is a low, slow condition.
private _speed = speed _aircraft;
if (_speed > 60) exitWith { false };

// One source per aircraft.
private _key = format [QGVAR(rotorWash_%1), netId _aircraft];
private _existing = missionNamespace getVariable [_key, objNull];
if (!isNull _existing && alive _existing) exitWith { false };
if !([] call FUNC(checkParticleBudget)) exitWith { false };

// ─── Surface under the rotor ──────────────────────────────────────────────
private _pos = getPosASL _aircraft;
private _ground = [_pos] call FUNC(surfaceSample);
_ground params ["_material", "_colour", "_lift"];

// Hardstanding and water do not raise a cloud.
if (_lift < 0.15) exitWith { false };

// ─── The physics: is the flow above the entrainment threshold? ────────────
private _wash = [_aircraft, _material] call FUNC(calculateDownwash);
_wash params ["_entrainment", "_threshold", "_outwash", "_flux"];
if (_entrainment <= 0) exitWith { false };

// Moisture holds the bed: a wet surface lifts far less.
private _suppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 0.6];
if !(_suppression isEqualType 0) then { _suppression = 0.6; };
_entrainment = _entrainment * _suppression;
if (_entrainment < 0.02) exitWith { false };

// ─── Particle parameters for this material ────────────────────────────────
private _params = [_material, _lift, _colour, _pos] call FUNC(kickupParams);
_params params ["_weight", "_volume", "_rubbing", "_bounce", "_pcolor"];

// ─── Geometry: the ground ring and the roll-up ────────────────────────────
// The ring radius follows the outwash: a stronger flow throws the material
// further out before it rises.
private _radius = 4 + (_outwash * 0.35);
private _alpha = (_entrainment * 0.55) min 0.6;

private _source = "#particlesource" createVehicleLocal _pos;
missionNamespace setVariable [_key, _source];
_source call FUNC(registerParticleSource);

_source setParticleCircle [_radius, [0, 0, 0]];
_source setParticleRandom [0.3, [_radius * 0.4, _radius * 0.4, 0], [1.5, 1.5, 0.8], 0, 0.2, [0, 0, 0, 0], 0, 0];
_source setParticleParams [
    ["\A3\data_f\ParticleEffects\Universal\Universal.p3d", 16, 12, 9, 0],
    "",
    "Billboard",
    1,
    1.6 + _entrainment * 1.4,
    [0, 0, 0],
    [0, 0, 0.6],                             // the roll-up lifts the cloud
    0,
    _weight,
    _volume,
    _rubbing,
    [1.5 + _entrainment * 2.0, 3.0 + _entrainment * 3.0],
    [[_pcolor select 0, _pcolor select 1, _pcolor select 2, _alpha],
     [_pcolor select 0, _pcolor select 1, _pcolor select 2, 0]],
    [0.6],
    1,
    0,
    "",
    "",
    _aircraft,
    0,
    true,
    _bounce
];

// Emission follows the entrainment: a stronger flow throws more material.
_source setDropInterval (0.25 / (_entrainment max 0.05));

// The source follows the aircraft while it is in the ground-effect band.
[_source, _aircraft, _key] spawn {
    params ["_source", "_aircraft", "_key"];
    waitUntil {
        sleep 0.5;
        !alive _source
        || {!alive _aircraft}
        || {(speed _aircraft) > 60}
        || {((getPosASL _aircraft) select 2) - (getTerrainHeightASL (getPos _aircraft)) > 40}
    };
    deleteVehicle _source;
    missionNamespace setVariable [_key, nil];
};

true
