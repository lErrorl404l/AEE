#include "..\script_component.hpp"

/*
Apply the scripted per-system damage model to one local aircraft.

WHY THIS FUNCTION EXISTS.  The engine owns the damage model.  CfgVehicles
HitPoints define the components, getHitPointDamage and setHitPointDamage read
and write one component, and allowDamage gates every write.  The engine maps a
component to a visual and a config effect.  It does NOT map a component to an
AEE system, and it does NOT degrade a system progressively.  This kernel adds
that scripted layer.

WHAT IT DOES.
  - It reads the vehicle hit points with getAllHitPointsDamage and reads each
    mapped component with getHitPointDamage.
  - It maps each game hit point name to one AEE system role through the role
    map held in data/aircraft/damage_roles.json.  A test pins this file and the
    map below equal, so the JSON is the authority and this is its SQF copy.
  - It applies the effect of the worst damage in each role:
      engine  the delivered power fraction falls from one as the damage rises
              above the threshold, written to the existing per-vehicle variable
              aee_enginePowerFraction, which the exhaust layer reads
      fuel    the tank leaks the sourced rate
      rotor   the rotor carries an imbalance
  - It advances each damaged system by a small scripted increment through
    setHitPointDamage, so the failure is progressive and not a step.

THE ROLE MAP.  getAllHitPointsDamage returns LOWERCASE hit point names.  The
map keys carry the mixed case of damage_roles.json, so the kernel normalises
the game name to the map case before the lookup.

THE CEILING.  The damage model is CONFIG-DRIVEN.  A mod can EXTEND it with new
HitPoints and cannot REPLACE it.  The per-system progressive behaviour is
SCRIPTED, not engine-owned: the engine has no system role and no progression.
This kernel never edits the engine's HitPoints config.

ALLOWDAMAGE.  setHitPointDamage has no effect when allowDamage is false, and a
vehicle that refuses damage must not show a scripted effect either, so the
kernel refuses the whole update when damage is not allowed.

Guards, each explicit:
  - A null or dead vehicle is refused.
  - A non-Air vehicle is refused.  A parachute is an Air object with no engine,
    tank or rotor, so it is refused.
  - A non-local vehicle is refused, so only the owning machine writes.
  - A vehicle that refuses damage is refused.
  - An unknown class has no systems row, so it is refused.

Arguments:
  0:  _veh        (OBJECT) the aircraft to update
  1:  _deltaTimeS (NUMBER) elapsed interval, s, default 0

Return Value: BOOL - true when the damage state was applied
Example: [cursorObject, 1] call aee_flight_fnc_updateDamageSystem
Public: No
*/

params [["_veh", objNull, [objNull]], ["_deltaTimeS", 0, [0]]];

if (isNull _veh || {!alive _veh}) exitWith { false };
if !(_veh isKindOf "Air") exitWith { false };
if (_veh isKindOf "ParachuteBase") exitWith { false };

// Deterministic and local, INCLUDING the server. The owning machine is the
// only writer.
if (!local _veh) exitWith { false };

if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { false };

// A vehicle that refuses damage shows no scripted effect either.
if !(isDamageAllowed _veh) exitWith { false };

private _systems = [typeOf _veh] call FUNC(getAircraftSystems);
if (_systems isEqualTo []) exitWith { false };

private _hpData = getAllHitPointsDamage _veh;
if (count _hpData < 3) exitWith { false };
private _hpNames = _hpData select 0;

// Declared scripted bounds, not sourced. A system shows an effect only above
// the threshold, and a damaged system advances by the increment each second.
private _threshold = 0.1;
private _progressPerS = 0.001;

// The role map, in the case of data/aircraft/damage_roles.json. A test pins
// the two equal, so the JSON is the authority and this is its SQF copy.
private _roleNames = [
    "HitEngine", "HitEngine1", "HitEngine2", "HitMotor",
    "HitMainRotor", "HitTailRotor", "HitHRotor", "HitVRotor", "HitMainRotorHub",
    "HitFuel", "HitFuelTank",
    "HitHydraulic",
    "HitAvionics", "HitBattery", "HitGenerator",
    "HitGearbox", "HitMainRotorGearBox", "HitTailGearBox", "HitIntermediateGearBox",
    "HitPilot", "HitCrew"
];
private _roleTokens = [
    "engine", "engine", "engine", "engine",
    "rotor", "rotor", "rotor", "rotor", "rotor",
    "fuel", "fuel",
    "hydraulic",
    "electrical", "electrical", "electrical",
    "gearbox", "gearbox", "gearbox", "gearbox",
    "pilot", "pilot"
];

// The worst damage in each role drives the effect. A role with no damaged hit
// point stays at zero.
private _engineDamage = 0;
private _fuelDamage = 0;
private _rotorDamage = 0;

private _hpCount = count _hpNames;
private _roleCount = count _roleNames;

for "_i" from 0 to (_hpCount - 1) do {
    private _lower = toLower (_hpNames select _i);
    private _canonical = "";
    private _role = "";
    // Normalise the lowercase game name to the map case before the lookup.
    for "_j" from 0 to (_roleCount - 1) do {
        if (toLower (_roleNames select _j) == _lower) then {
            _canonical = _roleNames select _j;
            _role = _roleTokens select _j;
        };
    };
    if (_role != "") then {
        private _damage = _veh getHitPointDamage _canonical;
        if (_damage isEqualType 0) then {
            if (_damage > 0) then {
                if (_role == "engine" && _damage > _engineDamage) then { _engineDamage = _damage; };
                if (_role == "fuel" && _damage > _fuelDamage) then { _fuelDamage = _damage; };
                if (_role == "rotor" && _damage > _rotorDamage) then { _rotorDamage = _damage; };
            };
            if (_damage > _threshold) then {
                // Advance the failure. The increment is scripted and small.
                private _next = (_damage + (_progressPerS * _deltaTimeS)) min 1;
                _veh setHitPointDamage [_canonical, _next];
            };
        };
    };
};

// Engine: the delivered power fraction falls from one above the threshold.
// The variable name is the one the exhaust layer reads.
private _powerFraction = 1;
if (_engineDamage > _threshold) then {
    _powerFraction = 1 - ((_engineDamage - _threshold) / (1 - _threshold));
};
_veh setVariable ["aee_enginePowerFraction", _powerFraction];

// Fuel: the tank leaks the sourced rate, scaled by the damage severity.
private _fuelCapacityL = _systems select 0;
private _sourcedRate = _systems select 1;
private _density = _systems select 2;
private _fullMassKg = _fuelCapacityL * _density;
if (_fuelDamage > _threshold && _fullMassKg > 0) then {
    private _severity = (_fuelDamage - _threshold) / (1 - _threshold);
    private _leakKg = _sourcedRate * _severity * _deltaTimeS;
    private _fuelKg = (fuel _veh) * _fullMassKg;
    private _remainingKg = (_fuelKg - _leakKg) max 0;
    _veh setFuel ((_remainingKg / _fullMassKg) min 1 max 0);
};

// Rotor: the rotor carries an imbalance, a fraction of the damage severity.
private _imbalance = 0;
if (_rotorDamage > _threshold) then {
    _imbalance = (_rotorDamage - _threshold) / (1 - _threshold);
};
_veh setVariable [QGVAR(rotorImbalance), _imbalance];

true
