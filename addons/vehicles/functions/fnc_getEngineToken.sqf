#include "..\script_component.hpp"
/*
Vehicle coarse engine token (issue #117).

Function: aee_vehicles_fnc_getEngineToken.

The single engine-token ladder. It maps a live vehicle to the coarse AEE
class token by the engine families the class is kindOf, most specific
first. It reads no config text and no catalogue entry: the token is the
coarse class identity, not a catalogue id.

The ladder is shared. aee_vehicles_fnc_classifyVehicle returns the token on
its token route, and aee_vehicles_fnc_estimateVehicleMass keys the
mass-class rows on it. "MRAP", "Wheeled_APC" and "Tracked_APC" are AEE
tokens, not CfgVehicles classes, so they are the value of a row and never
an isKindOf selector. A mass-class row keyed on the token resolves the
specific class, which an isKindOf test on the row key could not do: every
MRAP and every wheeled APC is kindOf Car, so Car answered for all of them.

The ground order follows the aee_mobility_fnc_calculateSSF track table. The
chains come from the shipped PBO configs (hemtt derapify, 2026-10-18):

  MRAP_01_base_F : Car_F : Car
  MRAP_02_base_F : Car_F : Car
  MRAP_03_base_F : Car_F : Car
  Wheeled_APC_F  : Car_F : Car
  APC_Tracked_01_base_F : Tank_F : Tank
  APC_Tracked_02_base_F : Tank_F : Tank
  APC_Tracked_03_base_F : Tank_F : Tank
  Truck_F : Car_F : Car
  Truck : Car

Every MRAP and Wheeled_APC_F is kindOf Car, and every APC_Tracked is kindOf
Tank, so those rows precede Car and Tank. Truck_F and Truck are kindOf Car,
so they precede Car too. A class reaches one engine family only, so the
family order does not change a land match.

Return Value: STRING, the coarse token, or "" when no row matches.

Arguments:
  0: vehicle (OBJECT) a vehicle, default objNull

Example: [cursorObject] call aee_vehicles_fnc_getEngineToken
Public: No
*/

params [["_vehicle", objNull, [objNull]]];

if (isNull _vehicle) exitWith { "" };
if ((typeOf _vehicle) == "") exitWith { "" };

private _vehicleTokens = [
    ["MRAP_01_base_F", "MRAP"],
    ["MRAP_02_base_F", "MRAP"],
    ["MRAP_03_base_F", "MRAP"],
    ["Wheeled_APC_F", "Wheeled_APC"],
    ["APC_Tracked_01_base_F", "Tracked_APC"],
    ["APC_Tracked_02_base_F", "Tracked_APC"],
    ["APC_Tracked_03_base_F", "Tracked_APC"],
    ["Truck_F", "Truck"],
    ["Truck", "Truck"],
    ["Tank", "Tank"],
    ["Car", "Car"],
    ["Helicopter", "Helicopter"],
    ["Plane", "Plane"],
    ["Ship", "Ship"]
];

private _token = "";
{
    _x params ["_familyClass", "_familyToken"];
    if (_vehicle isKindOf _familyClass) exitWith { _token = _familyToken; };
} forEach _vehicleTokens;

_token
