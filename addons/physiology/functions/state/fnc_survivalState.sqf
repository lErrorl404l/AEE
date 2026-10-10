#include "..\..\script_component.hpp"

/*
Survival state (will to live).

Reads the physiology family's published hazards and publishes the survival
pressure the AI layer consumes.  This function reads state another addon
already owns, so it adds no second model of the same state.

Reads (each with a safe default):
  EGVAR(strain,dehydrationRisk)   0..1, body-water deficit risk
  EGVAR(core,currentHypoxiaRisk)  0..1, hypoxia exposure over the TUC
  EGVAR(core,windChillTemp)       degC, wind chill
  EGVAR(core,currentWBGT)         degC, wet-bulb globe temperature
  QGVAR(fatigueFactor)            0.30..1.0, Borbely performance factor

The cold stress and the heat stress map from the raw temperature state
through FUNC(coldStress) and FUNC(heatStress).  The fatigue factor inverts
to a risk (1 - factor), so a rested soldier carries no fatigue pressure.

Sets:    QGVAR(survivalPressure)  0..1
Returns: Number - the survival pressure, 0..1
*/

if (!(missionNamespace getVariable [EGVAR(core,physiologyEnabled), true])) exitWith { 0 };

private _dehydration = missionNamespace getVariable [EGVAR(strain,dehydrationRisk), 0];
if !(_dehydration isEqualType 0) then { _dehydration = 0; };

private _hypoxia = missionNamespace getVariable [EGVAR(core,currentHypoxiaRisk), 0];
if !(_hypoxia isEqualType 0) then { _hypoxia = 0; };

private _windChill = missionNamespace getVariable [EGVAR(core,windChillTemp), 15];
if !(_windChill isEqualType 0) then { _windChill = 15; };
private _cold = [_windChill] call FUNC(coldStress);

private _wbgt = missionNamespace getVariable [EGVAR(core,currentWBGT), 15];
if !(_wbgt isEqualType 0) then { _wbgt = 15; };
private _heat = [_wbgt] call FUNC(heatStress);

private _fatigueFactor = missionNamespace getVariable [QGVAR(fatigueFactor), 1.0];
if !(_fatigueFactor isEqualType 0) then { _fatigueFactor = 1.0; };
private _fatigue = 1 - _fatigueFactor;

private _pressure = [_dehydration, _hypoxia, _cold, _heat, _fatigue] call FUNC(survivalPressure);

missionNamespace setVariable [QGVAR(survivalPressure), _pressure];

_pressure
