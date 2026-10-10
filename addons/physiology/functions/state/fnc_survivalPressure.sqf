#include "..\..\script_component.hpp"

/*
Survival pressure kernel (will to live).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The
survival pressure is the strongest of the five physiological hazards.  Each
hazard is a 0..1 risk the physiology family already publishes, so this
kernel only aggregates them and adds no second model of the same state.

The five inputs and their sources:
  dehydrationRisk  EGVAR(strain,dehydrationRisk).  Body-water deficit over
                   the ISO 7243 sweat band (TB MED 507; StatPearls:
                   2% loss = 0.3, 4% = 0.6, 6% = 1.0).
  hypoxiaRisk      EGVAR(core,currentHypoxiaRisk).  Exposure over the Time
                   of Useful Consciousness (FAA AIM 8-1-1 TUC table).
  coldStress       FUNC(coldStress).  Wind chill over the TB MED 508
                   bands (-28 C = 0.3, -40 = 0.6, -48 = 0.8, -55 = 1.0).
  heatStress       FUNC(heatStress).  WBGT over the TB MED 507 / ISO 7243
                   bands (29 C = 0.3, 34 = 0.6, 38 = 0.8).
  fatigueRisk      1 - EGVAR(physiology,fatigueFactor).  The Borbely sleep
                   pressure (strain/calculateFatigueFactor: rested = 0.0,
                   under 5 h sleep = 0.7).

Arguments:
  0: Number - dehydration risk, 0 to 1
  1: Number - hypoxia risk, 0 to 1
  2: Number - cold stress, 0 to 1
  3: Number - heat stress, 0 to 1
  4: Number - fatigue risk, 0 to 1

Returns:
  Number - the survival pressure, 0 to 1
*/

params [
    ["_dehydrationRisk", 0, [0]],
    ["_hypoxiaRisk", 0, [0]],
    ["_coldStress", 0, [0]],
    ["_heatStress", 0, [0]],
    ["_fatigueRisk", 0, [0]]
];

private _max = ((_dehydrationRisk max _hypoxiaRisk) max (_coldStress max _heatStress)) max _fatigueRisk;

((_max max 0) min 1)
