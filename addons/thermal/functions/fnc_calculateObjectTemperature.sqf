#include "..\script_component.hpp"

/*
Object surface temperature model for thermal vision rendering.

Each nearby object gets a surface temperature from its material, solar
exposure, engine state, and convective cooling.  The results feed thermal
optics so vehicles, infantry, and terrain show realistic heat signatures.

Physics basis:
  - Solar absorption: metal ~0.7, fabric ~0.5, skin ~0.6.  Low thermal
    mass lets metal heat quickly in sun.
  - Engine heat: a running engine adds 20-40 °C to the engine bay and
    10-20 °C to body panels.
  - Wind cooling: convective cooling of ~2 °C per m/s of wind, toward
    air temperature.
  - Shade: objects in shade lose solar heating and approach air
    temperature.
  - Emissivity: metal ~0.9, paint ~0.92, fabric ~0.95, skin ~0.98.
    Lower emissivity radiates less, so the radiant temperature drops.
  - Infantry: core 37 °C, skin ~33 °C, clothing insulates the surface
    to roughly 30-35 °C regardless of air temperature.
  - Ground: desert sand heats ~15 °C above air, grass ~5 °C, snow
    stays ~2 °C below air.
  - Thermal crossover: when surface temperature approaches air
    temperature, thermal contrast falls toward zero.

Stored in GVAR(objectTemperatures) as [object, temperature] pairs, plus
GVAR(avgVehicleTemp), GVAR(avgInfantryTemp), and GVAR(avgGroundTemp).
*/

params [
    ["_center", objNull, [objNull]],
    ["_radius", 100, [0]],
    ["_maxObjects", 50, [0]]
];

// Defensive: nil center falls back to the current unit
if (isNull _center) then {
    _center = call CBA_fnc_currentUnit;
};

// No unit on a dedicated server: publish empty state and stop
if (isNull _center) exitWith {
    missionNamespace setVariable [QEGVAR(core,objectTemperatures), []];
    missionNamespace setVariable [QEGVAR(core,avgVehicleTemp), 0];
    missionNamespace setVariable [QEGVAR(core,avgInfantryTemp), 0];
    missionNamespace setVariable [QEGVAR(core,avgGroundTemp), 0];
    0
};

_radius = _radius max 10 min 500;
_maxObjects = _maxObjects max 1 min 100;

// ─── Shared inputs ────────────────────────────────────────────────────────
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if (isNil "_airTemp") then { _airTemp = 15; };
private _windSpeed = vectorMagnitude wind;
private _solar = [overcast] call EFUNC(core,calculateSolarRadiation);

// ─── Ground temperature from surface type ────────────────────────────────
private _groundType = toLower (surfaceType (getPos _center));
private _groundGain = switch (true) do {
    case (_groundType == "#gdtdesert"):     { 15 };
    case (_groundType == "#gdtsand"):       { 10 };
    case (_groundType == "#gdtice"):        { -2 };
    case (_groundType == "#gdtsnow"):       { -2 };
    case (_groundType == "#gdtconiferous"): {  2 };
    case (_groundType == "#gdtforest"):     {  3 };
    default                                 {  5 }; // grass
};
private _groundTemp = _airTemp + _groundGain * _solar;

// Shade at the centre position: cast a ray straight up
private _centerASL = getPosASL _center;
private _eyePos = _centerASL vectorAdd [0, 0, 1.5];
private _abovePos = _eyePos vectorAdd [0, 0, 6];
private _hits = lineIntersectsSurfaces [_eyePos, _abovePos, objNull, objNull, true, 1, "GEOM", "NONE"];
if (count _hits > 0) then { _groundTemp = _airTemp; };

// Convective cooling pulls the ground toward air temperature
_groundTemp = _groundTemp - _windSpeed * 2;
_groundTemp = _groundTemp max _airTemp;

// ─── Object scan ──────────────────────────────────────────────────────────
private _objects = nearestObjects [_center, ["LandVehicle", "Air", "Ship", "Man", "StaticWeapon"], _radius];
if (count _objects > _maxObjects) then { _objects resize _maxObjects; };

private _results = [];
private _vehicleSum = 0;
private _vehicleCount = 0;
private _infantrySum = 0;
private _infantryCount = 0;

{
    if (!isNull _x && {alive _x}) then {
        private _obj = _x;

        // Shade: ray from above the object's top, ignoring its own geometry
        private _top = ((boundingBox _obj) select 1) select 2;
        private _objEye = (getPosASL _obj) vectorAdd [0, 0, (_top max 1) + 1];
        private _objAbove = _objEye vectorAdd [0, 0, 6];
        private _objHits = lineIntersectsSurfaces [_objEye, _objAbove, _obj, objNull, true, 1, "GEOM", "NONE"];
        private _inShade = count _objHits > 0;

        private _temp = _airTemp;
        private _emissivity = 0.95;

        if (_obj isKindOf "Man") then {
            // Clothing insulates: the surface stays near skin temperature
            _temp = 32 + (_airTemp - 20) * 0.15;
            _temp = _temp max 28 min 37;
            if (_inShade) then { _temp = _temp - 1; };
            _emissivity = 0.98;
            _infantrySum = _infantrySum + _temp;
            _infantryCount = _infantryCount + 1;
        } else {
            // Metal body: strong solar absorption, low thermal mass
            _temp = _airTemp + _solar * 0.7 * 15;
            if (_inShade) then { _temp = _airTemp; };
            if (_obj isKindOf "LandVehicle" || _obj isKindOf "Air" || _obj isKindOf "Ship") then {
                // A running engine heats the body panels by 10-20 °C
                if (isEngineOn _obj) then { _temp = _temp + 15; };
                _emissivity = 0.9;
                _vehicleSum = _vehicleSum + _temp;
                _vehicleCount = _vehicleCount + 1;
            } else {
                _emissivity = 0.92; // painted static weapon
            };
            // Convective cooling pulls the surface toward air temperature
            _temp = _temp - _windSpeed * 2;
            _temp = _temp max _airTemp;
        };

        // Radiant temperature: lower emissivity radiates less heat
        _temp = _temp - (1 - _emissivity) * 2;

        _results pushBack [_obj, round (_temp * 10) / 10];
    };
} forEach _objects;

// ─── Summary averages ─────────────────────────────────────────────────────
private _avgVehicle = if (_vehicleCount > 0) then { _vehicleSum / _vehicleCount } else { _airTemp };
private _avgInfantry = if (_infantryCount > 0) then { _infantrySum / _infantryCount } else { _airTemp };

missionNamespace setVariable [QEGVAR(core,objectTemperatures), _results];
missionNamespace setVariable [QEGVAR(core,avgVehicleTemp), _avgVehicle];
missionNamespace setVariable [QEGVAR(core,avgInfantryTemp), _avgInfantry];
missionNamespace setVariable [QEGVAR(core,avgGroundTemp), _groundTemp];

_results
