#include "..\script_component.hpp"

/*
Core body temperature from the physiology heat balance.

Physiology heat balance.  A BODY_TEMP_C (37 C) baseline plus a heat gain from the wet
bulb globe temperature above a threshold, minus a cold loss from the wind
chill temperature and the hypothermia risk:

    T_core = BODY_TEMP_C + 0.05 * max(0, WBGT - 28)
                - 0.10 * max(0, 10 - windChill)
                - 4.0  * hypothermiaRisk

Source grading:

  baseline BODY_TEMP_C  sourced.  Normal resting human core temperature (37 C).
  heat threshold 28 C  UNSOURCED.  A WBGT threshold in the heat-stress
                       band (28 is the common worker-exposure limit), not a
                       measured physiological set point.
  heat gain 0.05       UNSOURCED.  C of core rise per C of WBGT above the
                       threshold.  A bounded modelling choice.
  cold threshold 10 C  UNSOURCED.  The wind chill below which the core
                       loses heat.  A bounded modelling choice.
  cold gain 0.10       UNSOURCED.  C of core loss per C of wind chill below
                       the threshold.  A bounded modelling choice.
  hypothermia loss 4.0 UNSOURCED.  C of core loss at full hypothermia risk
                       (risk is 0..1).  A bounded modelling choice.

The result is clamped to [28, 42] C, the survivable band, so a missing or
stale input cannot publish a non-physical value.

This function fixes the orphan read at
addons/compat_kat/functions/fnc_integrateKAT.sqf:BODY_TEMP_C, which read
aee_core_coreBodyTemp with a BODY_TEMP_C fallback while nothing produced it.

Sets:   aee_core_coreBodyTemp (C)
Returns: Number - the core body temperature in C.
*/

private _wbgt = missionNamespace getVariable [QEGVAR(core,currentWBGT), 15];
if !(_wbgt isEqualType 0) then { _wbgt = 15; };
private _windChill = missionNamespace getVariable [QEGVAR(core,windChillTemp), 15];
if !(_windChill isEqualType 0) then { _windChill = 15; };
private _hypoRisk = missionNamespace getVariable [QEGVAR(core,currentHypothermiaRisk), 0];
if !(_hypoRisk isEqualType 0) then { _hypoRisk = 0; };

private _heatGain = ((_wbgt - 28) max 0) * 0.05;
private _coldLoss = (((10 - _windChill) max 0) * 0.10) + (_hypoRisk * 4.0);
private _tBody = ((BODY_TEMP_C + _heatGain - _coldLoss) max 28) min 42;

missionNamespace setVariable [QGVAR(coreBodyTemp), _tBody];

_tBody
