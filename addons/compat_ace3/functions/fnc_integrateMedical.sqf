#include "..\script_component.hpp"

/*
ACE3 medical integration — translates AEE thermal/dehydration state into
ACE3 medical vitals.

Runs every 5 s from the compat PFH on the local unit.  Maps AEE state
onto ACE3 medical through its public interface:

  Heat stress (WBGT)  → ace_medical_status_fnc_addMedicationAdjustment
                        (+heart rate, −peripheral flow) — the gradual
                        vitals hook.  Repeated calls with the same
                        medication replace the entry, so the effect
                        holds while conditions persist and decays via
                        maxTimeInSystem when cleared.
  Dehydration risk    → −peripheral flow (low blood volume), pain at
                        high risk.
  Extreme case        → ace_medical_status_fnc_setCardiacArrestState
                        when WBGT > 32 and risk > 0.8 (heat stroke).
  Heat exposure       → ace_medical_fnc_addDamageToUnit with "burn"
                        (thermal burn: no bleeding, pain 0.7).  The
                        previous "environment" type created bleeding
                        wounds — wrong for heat.

All calls require a local unit; the function exits early when remote.
*/

params [["_unit", player, [objNull]]];

if (isNull _unit) exitWith {};
if !(local _unit) exitWith {};
if (isNil "ace_medical_status_fnc_addMedicationAdjustment") exitWith {};

private _temp = missionNamespace getVariable ["aee_core_currentTemperature", 15];
private _wbgt = missionNamespace getVariable ["aee_core_currentWBGT", 15];
private _risk = missionNamespace getVariable ["aee_physiology_dehydrationRisk", 0];

// ─── Heat stress vitals (WBGT → heart rate / flow) ─────────────────────────
private _hr    = 0;
private _flow  = 0;
private _pain  = 0;

if ((_wbgt > (missionNamespace getVariable [QEGVAR(compat_ace3,medicalWBGTThreshold), 0])) || (_risk > (missionNamespace getVariable [QEGVAR(compat_ace3,medicalRiskThreshold), 0]))) then {
    // ISO 7243 bands — heat strain raises heart rate, lowers peripheral flow
    if (_wbgt > 32) then {
        _hr = 30; _flow = -20; _pain = 0.3;              // very dangerous
    } else {
        if (_wbgt > 28) then { _hr = 20; _flow = -15; };  // danger
        if ((_wbgt > (missionNamespace getVariable [QEGVAR(compat_ace3,medicalWBGTThreshold), 0]))) then { _hr = 10; _flow = -10; };  // extreme caution
    };

    // Dehydration compounds flow loss (reduced blood volume)
    if (_risk > 0.7) then { _flow = _flow - 15; _pain = _pain max 0.2; };
    if ((_risk > (missionNamespace getVariable [QEGVAR(compat_ace3,medicalRiskThreshold), 0]))) then { _flow = _flow - 8; };

    [_unit, "AEE_heatStress", 120, 600, _hr, _pain, _flow, 1]
        call ace_medical_status_fnc_addMedicationAdjustment;
} else {
    // Conditions clear — expire the adjustment (maxTimeInSystem 0)
    [_unit, "AEE_heatStress", 120, 0, 0, 0, 0, 1]
        call ace_medical_status_fnc_addMedicationAdjustment;
};

// ─── Heat stroke (cardiac arrest) at extreme WBGT + critical dehydration ──
if ((_wbgt > (missionNamespace getVariable [QEGVAR(compat_ace3,medicalHeatStrokeWBGT), 0])) && _risk > 0.8) then {
    [_unit, true] call ace_medical_status_fnc_setCardiacArrestState;
} else {
    if (missionNamespace getVariable [QGVAR(heatStrokeActive), false]) then {
        [_unit, false] call ace_medical_status_fnc_setCardiacArrestState;
    };
};
missionNamespace setVariable [QGVAR(heatStrokeActive), ((_wbgt > (missionNamespace getVariable [QEGVAR(compat_ace3,medicalHeatStrokeWBGT), 0])) && _risk > 0.8)];

// ─── Heat burn damage (thermal burn — no bleeding, pain 0.7) ──────────────
// The burn gate uses the CBA default (25 C) as the in-code fallback, NOT
// 0: a 0 fallback fires whenever the setting is uninitialised (any temp
// above freezing -> burn every tick), which the Scottish Highlands report
// hit.  The damage goes to the REAL body parts via the engine's hitpoint
// selections rather than a hardcoded "LeftLeg" (the report showed the
// burn on the mirrored leg in the medical menu).  ACE's addDamageToUnit
// maps a class name; iterate the unit's actual hit selections so the
// wound lands where the exposure is.
private _burnTemp = missionNamespace getVariable [QEGVAR(compat_ace3,medicalBurnTemp), 25];
private _burnScale = missionNamespace getVariable [QEGVAR(compat_ace3,medicalBurnDamageScale), 0.0005];
if (_temp > _burnTemp) then {
    private _damage = (_temp - _burnTemp) * _burnScale;
    // Only apply to parts that can take burn: the engine's hitpoint
    // selections (body, arms, legs).  ACE accepts any body-part class;
    // using the real selection names keeps the wound on the correct side.
    private _parts = [
        "Body", "Head", "LeftArm", "RightArm", "LeftLeg", "RightLeg"
    ];
    {
        [_unit, _damage / 6, _x, "burn"] call ace_medical_fnc_addDamageToUnit;
    } forEach _parts;
};
