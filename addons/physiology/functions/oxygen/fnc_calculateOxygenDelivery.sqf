#include "..\..\script_component.hpp"
/*
Oxygen-delivery physiology for haemorrhagic hypovolaemia.

Returns the fraction of oxidative metabolism the circulation can still
supply, plus the volume-based skin perfusion index.  The thermal solvers
consume these instead of the former `min(1, bloodFrac / 0.70)` proxy, so
one blood model serves every consumer.

Relations, each sourced:
  CaO2 = 1.34*[Hb]*SaO2 + 0.003*PaO2            mL O2/dL
    1.34 mL/g = Hufner coefficient (Hufner 1894; Guyton & Hall Ch. 40).
    0.003 mL/dL/mmHg = O2 solubility in plasma (Guyton & Hall Ch. 40).
  DO2 = CO * CaO2 * 10                          mL O2/min
    x10 converts dL to L, CO in L/min (Guyton & Hall Ch. 40).
  VO2 = metabolicRate * 60 / 20.1               mL O2/min
    20.1 J/mL = oxycaloric equivalent, mixed substrate (Guyton & Hall;
    1 L O2 ~ 20.1 kJ).  Resting reference 3.5 mL/kg/min = 1 MET.
  CO = CO_rest * bloodFrac                      L/min
    CO_rest 5 L/min (Guyton & Hall Ch. 20).  Guyton: venous return sets
    CO, and venous return falls in proportion to circulating volume in
    haemorrhage, so CO is the immediate, dominant delivery loss.
  DO2crit = 330 * BSA                           mL O2/min
    330 mL O2/min/m2 critical delivery (Shibutani et al., Crit Care Med
    1983, PMID 6409505; the same paper gives 8.2 mL/kg/min in anaesthetised
    man).  It is the threshold below which VO2 becomes supply-dependent
    (definition: Schumacker & Cain 1987, PMID 3301969), and it is NOT
    settled to one number: conscious healthy humans sit near 284 mL/min/m2
    (Lieberman 2000, PMID 10691227) and the critically ill lower still
    (Ronco 1993, PMID 8411504).  The often-quoted 600 mL/min/m2 is NORMAL
    resting delivery, not a critical value, so the critical range is about
    280-330 mL/min/m2 at rest and rises with metabolic demand.  Below
    DO2crit VO2 is supply-dependent:
    VO2a = DO2 * ERcrit, ERcrit = VO2/DO2crit capped at the maximal
    extraction 0.75 (Guyton & Hall: mixed-venous saturation falls to
    about 25 percent at maximal extraction).
  metabolicFactor = VO2a / VO2 (oxidative fraction delivered)
  anaerobicDeficit = VO2 - VO2a (mL O2/min).  It closes the OPEN ITEM:
    the thermal solver now adds the non-oxidative heat this deficit
    produces.  The heat is DERIVED, not a published constant.  Take about
    1.0 J per mL O2 (range 0.9-1.1): 123.6 kJ per mol glucose to 2 lactate
    over 6 mol O2 = 134.4 L gives 0.92 kJ/L; Minakami & de Verdier 1976
    (PMID 7451), 71 kJ per mol lactate, gives 1.06 kJ/L.  That is about
    5 percent of the 20.1 J/mL oxidative equivalent, so it is small.

[Hb] is a persistent state and is deliberately NOT [Hb]ref * bloodFrac.
In acute haemorrhage red-cell mass and plasma are lost together, so the
concentration is initially normal and falls only as plasma refills
(transcapillary refill over hours; US Army Anesthesia and Perioperative
Care of the Combat Casualty Ch. 4).  Only the red-cell mass scales with
volume, so [Hb] relaxes toward [Hb]ref * bloodFrac with tau = 2 h.  CO
therefore carries the acute loss and [Hb] the late one.

ONE-WAY: the model never restores delivery because the tissue has been
hypoxic.  Perfusion and delivery recover only as blood volume is restored
or medical aid is applied.  The anaerobic branch reduces oxidative heat
and is not symmetrically reversed.

Arguments:
  0: unit (OBJECT) - Hb state key and ACE blood-volume source
  1: metabolic rate (NUMBER, W) - total current metabolic heat
  2: body surface area (NUMBER, m2) - DuBois 1.8258 default
  3: arterial O2 saturation (NUMBER, 0..1) - negative derives from hypoxia
  4: arterial O2 partial pressure (NUMBER, mmHg) - negative uses normal

Return: [caO2, co, do2, vo2Demand, vo2Actual, o2er, metabolicFactor,
         anaerobicDeficit, hb, do2crit, skinPerfusion]
Public: No
*/

params [
    ["_unit", objNull, [objNull]],
    ["_metabolicRate", 100, [0]],
    ["_bsa", 1.8258, [0]],
    ["_sao2", -1, [0]],
    ["_pao2", -1, [0]]
];

// ─── Blood volume (ACE state; 6.0 L full, vanilla fallback) ────────────────
private _bloodVol = 6.0;
if (!isNull _unit) then {
    _bloodVol = _unit getVariable ["ace_medical_bloodVolume", 6.0];
    if !(_bloodVol isEqualType 0) then { _bloodVol = 6.0; };
};
private _bloodFrac = (_bloodVol max 0 min 6.0) / 6.0;

// ─── Saturation: caller value, else the hypoxia risk already published ─────
// The 97 - risk*32 percent mapping is the one the KAT compat layer uses,
// so the two paths agree instead of double-counting altitude hypoxia.
private _sat = _sao2;
if (_sat < 0) then {
    private _risk = missionNamespace getVariable [QEGVAR(core,currentHypoxiaRisk), 0];
    if !(_risk isEqualType 0) then { _risk = 0; };
    _sat = 0.97 - ((_risk max 0 min 1) * 0.32);
};
_sat = _sat max 0 min 1;

// The dissolved term is under 1.5 percent of CaO2 at normal PaO2, so the
// normal 95 mmHg stands unless a caller supplies a measured value.
private _paO2mmHg = _pao2;
if (_paO2mmHg < 0) then { _paO2mmHg = 95; };
_paO2mmHg = _paO2mmHg max 0;

// ─── Haemoglobin: persistent, plasma-refill kinetics ───────────────────────
private _hbRef = 15.0;          // g/dL, Guyton & Hall normal
private _tauRefill = 7200;      // 2 h transcapillary refill
private _hbTarget = [_hbRef, _hbRef * _bloodFrac] select (_bloodFrac < 1);
private _now = diag_tickTime;
private _stateMap = missionNamespace getVariable [QGVAR(oxygenState), -1];
if (_stateMap isEqualType 0) then {
    _stateMap = createHashMap;
    missionNamespace setVariable [QGVAR(oxygenState), _stateMap];
};
private _key = if (isNull _unit) then { "" } else { str _unit };
private _entry = _stateMap getOrDefault [_key, [_hbRef, _now]];
private _hb = _entry select 0;
if !(_hb isEqualType 0) then { _hb = _hbRef; };
private _elapsed = (_now - (_entry select 1)) max 0;
if (_elapsed > 0) then {
    _hb = _hb + (_hbTarget - _hb) * (1 - exp (-(_elapsed min 60) / _tauRefill));
    _entry set [0, _hb];
    _entry set [1, _now];
    _stateMap set [_key, _entry];
    missionNamespace setVariable [QGVAR(oxygenState), _stateMap];
};

// ─── Content, delivery, consumption ────────────────────────────────────────
private _caO2 = 1.34 * _hb * _sat + 0.003 * _paO2mmHg;
private _co = 5.0 * _bloodFrac;
private _do2 = _co * _caO2 * 10;
private _vo2 = ((_metabolicRate max 0) * 60) / 20.1;

// ─── Critical delivery and the supply-dependent branch ─────────────────────
private _do2Crit = 330 * (_bsa max 0.1);
private _erMax = 0.75;
private _erCrit = ((_vo2 / _do2Crit) min _erMax) max 0;
private _vo2Actual = _vo2;
private _o2er = 0;
if (_do2 > 0) then {
    if (_do2 < _do2Crit) then { _vo2Actual = _do2 * _erCrit; };
    if ((_vo2Actual / _do2) > _erMax) then { _vo2Actual = _do2 * _erMax; };
    _o2er = (_vo2Actual / _do2) min 1;
} else {
    _vo2Actual = 0;
};
_vo2Actual = _vo2Actual max 0;
private _metabFactor = if (_vo2 > 0) then { (_vo2Actual / _vo2) min 1; } else { 1; };
private _deficit = (_vo2 - _vo2Actual) max 0;

// Skin vasoconstriction is a baroreflex response to reduced venous return,
// not an O2-delivery response, so it stays on the ATLS class III boundary
// (30 percent loss) that the thermal model already uses.
private _skinPerfusion = (_bloodFrac / 0.70) min 1;

[_caO2, _co, _do2, _vo2, _vo2Actual, _o2er, _metabFactor, _deficit, _hb, _do2Crit, _skinPerfusion]
