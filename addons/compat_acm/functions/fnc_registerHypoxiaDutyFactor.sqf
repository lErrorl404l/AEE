#include "..\script_component.hpp"

/*
Registers the AEE hypoxia duty factor with ACM's oxygen model.

ACM (v1.4.8.0) has no thermal or dehydration subsystem, so CBRN is the
only mandatory integration.  ACM DOES own SpO2: its fnc_updateOxygen
overwrite of ace_medical_spo2 every vitals tick makes direct SpO2 writes
futile (the same lesson as KAT bodyFluid).

The one safe, ACE-native extension point ACM respects is
ace_medical_vitals_spo2DutyList, read every tick as a multiplier on
breathing effectiveness.  AEE registers a duty factor that engages ONLY
when its TUC-based hypoxia risk exceeds what ACM's own altitude model
produces (risk > 0.8 — the near-unconsciousness band).  Below that band
the factor is 1.0, so the two models do not double-count altitude hypoxia.

The factor is registered once (postInit) and persists; it reads AEE state
live each tick.  It is OPTIONAL by design — the research report
(/tmp/opencode/acm_expansion_research.md) recommends no expansion beyond
CBRN, and this is the single technically-viable, low-risk addition.

Requires: ACM (Workshop 3235483358) + ACE3 medical.
*/

if (isNil "ace_medical_vitals_fnc_addSpO2DutyFactor") exitWith {};

// Scaled duty factor: 1.0 below risk 0.8, down to 0.65 at risk 1.0
// (matching the KAT compat's SpO2 floor of 65 at full risk).
private _dutyFactor = {
    private _risk = missionNamespace getVariable [QEGVAR(physiology,hypoxiaRisk), 0];
    if (_risk <= 0.8) then { 1.0 } else { 1 - ((_risk - 0.8) / 0.2) * 0.35 }
};

[QGVAR(hypoxiaDutyFactor), _dutyFactor] call ace_medical_vitals_fnc_addSpO2DutyFactor;

diag_log "[AEE][ACM] Hypoxia duty factor registered (engages above risk 0.8)";
