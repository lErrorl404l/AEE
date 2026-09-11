#include "..\script_component.hpp"

params [["_unit", player, [objNull]]];

if (isNil "ace_medical_fnc_addDamageToUnit") exitWith {};
if (isNull _unit) exitWith {};

private _temp = (missionNamespace getVariable ["aee_core_currentTemperature", 0]);
private _humidity = (missionNamespace getVariable ["aee_core_currentHumidity", 0]);

// Heat damage to legs
// ace_medical_fnc_addDamageToUnit signature:
//   [unit, damage, bodyPart, typeOfDamage, instigator, unused, overrideInvuln]
if (_temp > 10) then {
    private _damage = (_temp - 10) * 0.0005 * 1.5;
    [_unit, _damage, "LeftLeg", "environment"] call ace_medical_fnc_addDamageToUnit;
};

// Humidity damage to arms
if (_humidity > 20) then {
    private _damage = (_humidity - 20) * 0.0003 * 1.0;
    [_unit, _damage, "RightArm", "environment"] call ace_medical_fnc_addDamageToUnit;
};
