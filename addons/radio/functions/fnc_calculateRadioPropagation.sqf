#include "..\script_component.hpp"

/*
VHF/UHF radio propagation quality (0.3 to the configured ceiling) —
physical link budget.

Models the received-signal quality from the Friis transmission equation
(P_r / P_t = G_t G_r (λ / 4πd)²) with atmospheric ducting and absorption
as dB corrections:

  Link budget:  _linkBudget_dB = P_t(dBm) − FSPL(dB) − _extraLoss + _ductBonus
  FSPL (Friis): 20·log10(d) + 20·log10(f) − 147.55   (d in m, f in Hz)
  Quality:      _quality = 0.3 + 1.7 · (_signalPct ^ 0.5)   clamped 0.3..ceiling

where _signalPct = 10^(_linkBudget_dB / 20).  The quality index is then
scaled to the 0.3–2.0 range the compat layers (ACRE2/TFAR) consume:
1.0 = nominal range, >1.0 = ducting extends range, <1.0 = absorption
shortens it.

Factors:
  • Ducting (temperature inversion, high humidity, high pressure) → dB bonus
  • Hot & dry (absorption) → dB penalty
  • Distance and frequency enter through FSPL directly.

Stored in QGVAR(radioPropagationIndex) for consumption by radio/TFAR
integration and AI communication-range modelling.
*/

private _T   = EGVAR(core,currentTemperature);
private _RH  = EGVAR(core,currentHumidity);
private _P   = EGVAR(core,currentPressure);
private _sun = sunOrMoon;

// The propagation index feeds only the ACRE2 and TFAR compat layers.
// Without either host mod there is no consumer, so exit early with the
// neutral index 1.0 rather than computing a dead value every tick.
if (!isClass (configFile >> "CfgPatches" >> "acre_sys_core")
    && !isClass (configFile >> "CfgPatches" >> "task_force_radio")) exitWith {
    missionNamespace setVariable [QGVAR(radioPropagationIndex), 1.0];
    1.0
};

if (isNil "_T")  exitWith { 1.0 };
if (isNil "_RH") exitWith { 1.0 };
if (isNil "_P")  then { _P = 1013 };

// ─── Link geometry ─────────────────────────────────────────────────────────
// Reference handheld link: configured transmit power, 100 MHz, 5 km
// nominal range. Frequency and range can be overridden via mission
// variables so a scenario can model specific radios.
private _freqHz = missionNamespace getVariable [QGVAR(radioFrequencyHz), 1e8];
private _distM  = missionNamespace getVariable [QGVAR(radioLinkRangeM), 5000];
private _txPowerDBm = missionNamespace getVariable [QGVAR(txPower), 37];
private _propRange  = missionNamespace getVariable [QGVAR(propagationRange), 2.0];

// ─── Free-space path loss (Friis) ──────────────────────────────────────────
// SQF's log command is base-10 (verified in-game: log 100 = 2).  Friis in
// SQF is therefore 20*log10(d) + 20*log10(f) - 147.55 with NO radix
// conversion.  (A previous version divided by 2.302585 assuming natural
// log, which double-converted and produced FSPL -46 dB — caught by the
// in-game RPT, invisible to the range-checked index.)
private _fspl = (20 * log _distM) + (20 * log _freqHz) - 147.55;

// ─── Atmospheric corrections (dB) ──────────────────────────────────────────
private _ductBonus = 0;

// Temperature inversion (warm night) — refracts signals over the horizon
if (_T > 25 && _sun == -1) then {
    _ductBonus = _ductBonus + (((_T - 25) / 20) min 0.5) * 6;   // up to +3 dB
};

// High humidity — water-vapour refraction gradient
if (_RH > 60) then {
    _ductBonus = _ductBonus + ((_RH - 50) / 10) * 0.05 * 6;     // up to +1.5 dB
};

// High pressure — denser lower atmosphere, stronger gradient
if (_P > 1020) then {
    _ductBonus = _ductBonus + ((_P - 1013) / 10) * 0.02 * 6;    // up to +1 dB
};

// Hot & dry — absorption penalty
private _absorptionPenalty = 0;
if (_T > 30 && _RH < 30) then {
    _absorptionPenalty = 2;                                     // −2 dB
};

// HF ionospheric absorption — D-layer non-deviative absorption (ITU-R
// P.531, computed by fnc_calculateIonosphericAbsorption) applies to HF
// skywave links (below 30 MHz).  VHF/UHF line-of-sight links (the Friis
// default) do not pass through the D-layer, so the penalty is gated on
// frequency.  This wires the ionospheric state into the link budget
// instead of leaving it write-only.
if (_freqHz < 30e6) then {
    private _ionoAbs = missionNamespace getVariable [QEGVAR(core,ionosphericAbsorption), 0];
    _absorptionPenalty = _absorptionPenalty + _ionoAbs;
};

// Terrain/obstruction excess loss (open 0, urban/forest higher)
private _biome = EGVAR(core,biome);
private _terrainLoss = 0;
if (!isNil "_biome") then {
    if (_biome in ["UMa", "Uhd", "Uhb", "Uhi", "Cfa", "Cfb", "Cfc", "Dfa", "Dfb"]) then {
        _terrainLoss = 3;                                       // forested/humid: foliage loss
    };
};

// ─── Link budget → quality index ───────────────────────────────────────────
private _linkBudget = _txPowerDBm - _fspl - _terrainLoss + _ductBonus - _absorptionPenalty;
private _signalPct = 10 ^ (_linkBudget / 20);
_signalPct = _signalPct max 0 min 1;

// Map signal fraction to the 0.3–2.0 index (√ compresses so mid-range
// signals land near 1.0 and the extremes reach 0.3 / 2.0).
private _index = 0.3 + 1.7 * (_signalPct ^ 0.5);
_index = _index max 0.3 min _propRange;

missionNamespace setVariable [QGVAR(radioPropagationIndex), _index];

if (EGVAR(core,diagnostic)) then {
    diag_log text format [
        "[AEE] RadioPropagation: %1 (FSPL %2 dB | duct %3 dB | terrain %4 dB | link %5 dBm)",
        [_index, 2] call CBA_fnc_formatNumber,
        [_fspl, 1] call CBA_fnc_formatNumber,
        [_ductBonus, 1] call CBA_fnc_formatNumber,
        [_terrainLoss, 1] call CBA_fnc_formatNumber,
        [_linkBudget, 1] call CBA_fnc_formatNumber
    ];
};

_index
