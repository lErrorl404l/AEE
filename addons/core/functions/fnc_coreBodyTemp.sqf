#include "..\script_component.hpp"

/*
Core body temperature of the local player, integrated in time.

The Gagge two-node model (aee_thermal_fnc_gaggeTwoNode: Gagge, Fobelets &
Berglund 1986 in the ASHRAE 55-2020 reference form, validated against
pythermalcomfort to 0.01 C), stepped in time from the persistent state, with:
  - metabolism from what the player is doing (aee_lib_fnc_unitMetabolicRate:
    Pandolf 1977 load carriage with the real carried mass, speed, grade and
    terrain), scaled by the oxygen-delivery fraction;
  - the worn clothing insulation (aee_clothing_fnc_getUniformProperties);
  - the air temperature, humidity, pressure, wind, the MRT
    (aee_thermal_fnc_calculateMRT) raised by the sun per ASHRAE 55 SolarCal
    with the sun exposure at the eye, and water immersion.
The core temperature therefore rises with exertion in heat and falls with
exposure in cold at the model's own physiological rates, instead of being
set instantaneously from the WBGT.

Sets:   aee_core_coreBodyTemp (C), aee_core_skinTemp (C),
        aee_core_metabolicRate (W)
Returns: Number - the core body temperature in C.
*/

if (!hasInterface) exitWith { BODY_TEMP_C };
private _unit = call CBA_fnc_currentUnit;
if (isNull _unit || {!alive _unit}) exitWith { BODY_TEMP_C };

private _state = missionNamespace getVariable [QGVAR(coreBodyState), []];
private _now = time;
if !((_state isEqualType []) && {(count _state) == 3} && {(_state select 2) isEqualTo _unit}) then {
    // Start four hours into the present conditions, so the body arrives
    // adapted to the mission's weather rather than at a thermoneutral seed.
    _state = [[], _now - 4 * 3600, _unit];
};
_state params ["_gagge", "_last"];
private _dt = ((_now - _last) max 0) min (4 * 3600);
if (_dt <= 0) exitWith { missionNamespace getVariable [QGVAR(coreBodyTemp), BODY_TEMP_C] };

private _tAir = missionNamespace getVariable [QGVAR(currentTemperature), 15];
if !(_tAir isEqualType 0) then { _tAir = 15; };
private _rh = missionNamespace getVariable [QGVAR(currentHumidity), 50];
if !(_rh isEqualType 0) then { _rh = 50; };
private _wind = vectorMagnitude (missionNamespace getVariable [QGVAR(currentWind), [0, 0, 0]]);
private _solar = missionNamespace getVariable [QGVAR(currentSolarFlux), 0];
if !(_solar isEqualType 0) then { _solar = 0; };

// Sun exposure at the eye: the line toward the light is clear.
private _eye = eyePos _unit;
private _lightDir = missionNamespace getVariable [QGVAR(lightDirection), [0, 0, -1]];
private _toSun = (_lightDir vectorMultiply -1) vectorMultiply 300;
private _exposure = [_unit, "VIEW"] checkVisibility [_eye, _eye vectorAdd _toSun];

private _mrt = [getPosASL _unit, 0.5] call EFUNC(thermal,calculateMRT);
private _clo = ([_unit] call EFUNC(clothing,getUniformProperties)) param [3, 0.75];
if !(_clo isEqualType 0) then { _clo = 0.75; };

private _met = [_unit] call EFUNC(lib,unitMetabolicRate);
private _ox = [_unit, _met, 1.8258] call EFUNC(altitude,calculateOxygenDelivery);
private _qMet = _met * (_ox param [6, 1]);

private _tWater = -273;
if ((eyePos _unit select 2) < 0 && {surfaceIsWater (getPosASL _unit)}) then {
    _tWater = missionNamespace getVariable [QGVAR(currentWaterTemperature), _tAir];
    if !(_tWater isEqualType 0) then { _tWater = _tAir; };
};

private _paMmHg = (6.112 * exp (17.62 * _tAir / (243.12 + _tAir))) * (_rh / 100) * 0.750062;
private _sunAlt = missionNamespace getVariable [QGVAR(currentSunElevation), -90];
if !(_sunAlt isEqualType 0) then { _sunAlt = -90; };
private _pressure = missionNamespace getVariable [QGVAR(currentPressure), 1013.25];
if !(_pressure isEqualType 0) then { _pressure = 1013.25; };
private _new = [
    _gagge, _dt, _tAir, _mrt, _wind, _qMet / 1.8258, _clo, _paMmHg, _pressure * 100,
    _solar, _sunAlt, _exposure, 0.7, _tWater, 0, (_ox param [10, 1]),
    (_tWater > -100) && {(vectorMagnitude velocity _unit) > 0.2}
] call EFUNC(thermal,gaggeTwoNode);
private _tCoreNew = _new select 0;
private _tSkinNew = _new select 1;

missionNamespace setVariable [QGVAR(coreBodyState), [_new, _now, _unit]];
missionNamespace setVariable [QGVAR(coreBodyTemp), _tCoreNew];
missionNamespace setVariable [QGVAR(skinTemp), _tSkinNew];
missionNamespace setVariable [QGVAR(metabolicRate), _met];

_tCoreNew
