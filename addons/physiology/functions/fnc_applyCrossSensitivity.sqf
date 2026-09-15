#include "..\script_component.hpp"

/*
Cross-sensitivity between the dehydration and hypoxia risk accumulators.

Dehydration reduces blood plasma volume, which impairs oxygen transport and
lowers the effective altitude threshold for AMS: the FAA TUC table assumes
euhydration.  Military altitude-medicine studies (Butterfield 1999; Sawka
2000) show dehydrated personnel have 30-50% faster AMS onset, and a 2% body
mass fluid loss alone reduces cognitive function 10-15%.  The two effects
are multiplicative, not additive.

Hypoxia also amplifies dehydration: at altitude, reduced renal function and
increased respiratory water loss accelerate fluid deficit.

The coupling runs AFTER both accumulators compute their raw risks, so it
reads the current-tick values and writes the amplified results back to the
same variables the consumers read (HUD, ACE3, KAT).  Neither accumulator
reads its own output risk, so writing the amplified value back does not
create a feedback loop.

Settings:
  crossSensitivityEnabled  - toggle the coupling entirely
  crossSensitivityScale    - 0..2 global strength (1 = full literature values)

Amplifiers (from the issue spec, calibrated to the references):
  hypoxia amplifier     = 1.0 at 0% dehydration .. 1.6 at 100%
  dehydration amplifier = 1.0 at 0% hypoxia .. 1.4 at 100%
*/

private _enabled = missionNamespace getVariable [QGVAR(crossSensitivityEnabled), true];
if !(_enabled isEqualType true) then { _enabled = true; };
if !(_enabled) exitWith { 0 };

private _scale = missionNamespace getVariable [QGVAR(crossSensitivityScale), 1.0];
if !(_scale isEqualType 0) then { _scale = 1.0; };
if (_scale <= 0) exitWith { 0 };

private _dehydration = missionNamespace getVariable [QGVAR(dehydrationRisk), 0];
if !(_dehydration isEqualType 0) then { _dehydration = 0; };
private _hypoxia = missionNamespace getVariable [QEGVAR(core,currentHypoxiaRisk), 0];
if !(_hypoxia isEqualType 0) then { _hypoxia = 0; };
_dehydration = _dehydration max 0 min 1;
_hypoxia = _hypoxia max 0 min 1;

// Amplifier at full scale: linear from 1.0 (no risk) to the literature cap.
// Interpolate between 1.0 and the cap by the scale setting, so scale 0.5
// gives half the coupling strength.
private _hypAmpFull = linearConversion [0, 1, _dehydration, 1.0, 1.6, true];
private _hypAmp = 1 + (_hypAmpFull - 1) * _scale;

private _dehAmpFull = linearConversion [0, 1, _hypoxia, 1.0, 1.4, true];
private _dehAmp = 1 + (_dehAmpFull - 1) * _scale;

private _effectiveHypoxia = (_hypoxia * _hypAmp) min 1;
private _effectiveDehydration = (_dehydration * _dehAmp) min 1;

missionNamespace setVariable [QGVAR(dehydrationRisk), _effectiveDehydration];
missionNamespace setVariable [QEGVAR(core,currentHypoxiaRisk), _effectiveHypoxia];

[_effectiveDehydration, _effectiveHypoxia]
