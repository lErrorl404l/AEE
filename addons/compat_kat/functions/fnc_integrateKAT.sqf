#include "..\script_component.hpp"

/*
    AEE — KAT Circulation Integration

    Drives KAT's blood-volume state from AEE's thermal/dehydration model.

    KAT API (verified against KAT source):
      kat_circulation_bodyFluid is an ARRAY of five mL compartments:
        [ECB, ECP, SRBC, ISP, total]  default [2700, 3300, 500, 10000, 6000]
      KAT's GET_BLOOD_VOLUME_LITERS reads (bodyFluid select 4) / 1000.
      Writing a scalar corrupts the array and breaks KAT vitals.
      KAT overwrites the array every ≥1 s from its own vitals loop, so AEE
      must re-apply the drain each tick.

    AEE dehydrates the extra-cellular compartments (ECP) and the
    intra-cellular space (ISP); blood (ECB) and stored red cells (SRBC)
    hold steady.  Drains are clamped ≥100 mL so KAT never reads nil.
    No return value.
*/

if (!isClass (configFile >> "CfgPatches" >> "kat_circulation")) exitWith {};

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
