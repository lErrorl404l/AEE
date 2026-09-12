#include "..\script_component.hpp"

/*
    AEE — KAT Circulation + Hypoxia Integration

    Drives KAT's blood-volume and oxygen-saturation state from AEE's
    thermal/dehydration and hypoxia models.

    KAT API (verified against KAT source, v3.2.1):
      kat_circulation_bodyFluid is an ARRAY of five mL compartments:
        [ECB, ECP, SRBC, ISP, total]  default [2700, 3300, 500, 10000, 6000]
      KAT's GET_BLOOD_VOLUME_LITERS reads (bodyFluid select 4) / 1000.
      Writing a scalar corrupts the array and breaks KAT vitals.
      KAT overwrites the array every ≥1 s from its own vitals loop, so AEE
      must re-apply the drain each tick.

    AEE dehydrates the extra-cellular compartments (ECP) and the
    intra-cellular space (ISP); blood (ECB) and stored red cells (SRBC)
    hold steady.  Drains are clamped ≥100 mL so KAT never reads nil.

    Hypoxia: kat_circulation_bloodGas is an ARRAY of six values
      [PaCO2, PaO2, SpO2, HCO3, pH, EtCO2]  default [40, 90, 0.96, 24, 7.4, 37]
      SpO2 is element 2 as a 0..1 fraction (macro GET_KAT_SPO2 ×100).
    AEE maps its hypoxia risk to a target SpO2 (97 − risk×32, clamped
    60..97) and a consistent PaO2 (33..40 mmHg) so KAT's dissociation
    curve does not pull the value back.  KAT overwrites bloodGas every
    ~1 s vitals tick, so the re-apply runs on the ace_medical_handleUnitVitals
    event, which fires after every KAT write.  This function is called
    from that event handler (see XEH_preInit).
    No return value.
*/

if (!isClass (configFile >> "CfgPatches" >> "kat_circulation")) exitWith {};

// ─── Circulation: body-fluid compartments from dehydration ────────────────
private _coreAETemp   = missionNamespace getVariable ["aee_core_currentTemperature", 15];
private _coreBodyTemp = missionNamespace getVariable ["aee_core_coreBodyTemp", 37];
private _dehydrationRisk = missionNamespace getVariable ["aee_physiology_dehydrationRisk", 0];

private _dehyd = 0;
if (_coreAETemp > 15 || _coreBodyTemp > 37.5 || _dehydrationRisk > 0.2) then {
    _dehyd = 0.05
        + ((_coreAETemp - 15) max 0) * 0.002
        + ((_coreBodyTemp - 37.5) max 0) * 0.01
        + _dehydrationRisk * 0.03;
};

private _bodyFluid = player getVariable ["kat_circulation_bodyFluid", [2700, 3300, 500, 10000, 6000]];
if (_bodyFluid isEqualType 0) then { _bodyFluid = [2700, 3300, 500, 10000, 6000]; };

// Drain ECP and ISP compartments; recompute the total
private _ecb  = _bodyFluid param [0, 2700];
private _ecp  = _bodyFluid param [1, 3300];
private _srbc = _bodyFluid param [2, 500];
private _isp  = _bodyFluid param [3, 10000];

private _ecpNew = (_ecp - _dehyd) max 100;
private _ispNew = (_isp - (_dehyd * 0.5)) max 100;
private _total  = _ecb + _ecpNew + _srbc + _ispNew;

player setVariable ["kat_circulation_bodyFluid", [_ecb, _ecpNew, _srbc, _ispNew, _total]];

// ─── Hypoxia: drive KAT SpO2/PaO2 from AEE risk ───────────────────────────
private _risk = missionNamespace getVariable ["aee_core_currentHypoxiaRisk", 0];

if (_risk > 0.01) then {
    private _spo2 = (97 - (_risk * 32)) max 60;            // percent
    private _pao2 = 33 + ((_spo2 - 60) / 15) * 7;          // 33..40 mmHg
    private _bloodGas = player getVariable ["kat_circulation_bloodGas", [40, 90, 0.96, 24, 7.4, 37]];
    if (_bloodGas isEqualType 0) then { _bloodGas = [40, 90, 0.96, 24, 7.4, 37]; };

    _bloodGas set [1, _pao2];
    _bloodGas set [2, _spo2 / 100];

    player setVariable ["kat_circulation_bloodGas", _bloodGas];
};
