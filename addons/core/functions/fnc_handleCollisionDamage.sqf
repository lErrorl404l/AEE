#include "..\script_component.hpp"
/*
Collision-damage response scaler (issue #172).

The #159 complaint: "random explosions on light taps" - the engine's
collision-damage thresholds date from Operation Flashpoint and are a
binary explosion, not a physics response.  A gentle 5 km/h bump can
destroy a vehicle.  This is the fix: scale collision damage by the
REAL impact energy.

The physics:
  E = 0.5 * m * v_rel^2
  where m is the total mass of both objects (the colliding pair) and
  v_rel is the closing speed at impact (the relative velocity).

  A 5 km/h (1.4 m/s) bump on a 12 t vehicle:
    E = 0.5 * 24000 * 1.4^2 ~ 23 kJ  -> minor
  An 80 km/h (22 m/s) crash:
    E = 0.5 * 24000 * 22^2 ~ 5.8 MJ  -> major component damage

The response scales damage to the impact energy - NOT a binary
explosion.  The component-damage cascade (#126) is the follow-on: a
light tap damages the bumper hitpoint, a crash damages the engine.

Arguments:
  0: unit (OBJECT) - the vehicle hit
  1: selection (STRING) - "" for vehicle-body impacts
  2: damage (NUMBER) - the incoming collision damage
  3: source (OBJECT) - the colliding vehicle (not a projectile)
  4: projectile (OBJECT) - "" for collisions
  5: hitIndex (NUMBER)
  6: instigator (OBJECT)
  7: hitPoint (STRING) - e.g. "HitEngine"

Returns the SCALED damage to return from HandleDamage, or the original
value when this is not a vehicle-vehicle collision.
*/
params ["_unit", "_selection", "_damage", "_source", "_projectile",
        ["_hitIndex", -1, [0]], ["_instigator", objNull, [objNull]],
        ["_hitPoint", "", [""]]];

// Collision = the source is a vehicle (not a projectile) and there is
// no projectile.  Projectile impacts go through the ballistic model.
if (_projectile isEqualType "") exitWith { _damage };
if !(_unit isKindOf "LandVehicle" || {_unit isKindOf "Air"}) exitWith { _damage };
if (isNull _source || {!(_source isKindOf "LandVehicle") && {!(_source isKindOf "Air")}}) exitWith { _damage };

// The closing speed: relative velocity magnitude of the two objects.
private _velA = velocity _unit;
private _velB = velocity _source;
private _rel = (_velA vectorDiff _velB);
private _speed = vectorMagnitude _rel;   // m/s
if (_speed < 0.5) exitWith { _damage };  // stationary contact, no impact

// Mass: both objects contribute (the energy is shared).
private _mass = (getMass _unit) + (getMass _source);   // kg
private _energy = 0.5 * _mass * _speed * _speed;       // J

// Scale: map impact energy to a damage multiplier (0..~2).
//   ~20 kJ  (5 km/h bump)    -> 0.1  (minor - bumper scuff)
//   ~1 MJ   (40 km/h crash)  -> 0.7  (significant component damage)
//   ~5 MJ   (80 km/h crash)  -> 1.5  (major damage, NOT guaranteed boom)
private _scale = linearConversion [20000, 5000000, _energy, 0.1, 1.5, true];

// Hitpoint response: the selection/hitpoint determines WHAT takes the
// damage (the #126 component model).  The engine reports the hitpoint
// name; fall back to the selection for body impacts.
private _component = if (_hitPoint != "") then { _hitPoint } else {
    ["Hull", _selection] select (_selection != "")
};

// Return the scaled damage, clamped so the engine can still kill the
// vehicle on a genuine high-energy crash (a real collision CAN destroy
// - it is the light-tap explosion that is the bug).
private _out = (_damage * _scale) min 1.0;

// Log for the diagnostics channel (the bugfix settings pattern).
if (missionNamespace getVariable [QGVAR(collisionDebug), false]) then {
    private _logMsg = format [
        "Collision: %1 vs %2 v=%3 m/s E=%4 kJ scale=%5 hp=%6 -> dmg=%7",
        typeOf _unit, typeOf _source, _speed, _energy / 1000,
        _scale, _component, _out
    ];
    AEE_LOG_INFO(_logMsg);
};

_out
