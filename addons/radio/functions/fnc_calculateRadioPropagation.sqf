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

// ─── Battery temperature derating (issue #36) ──────────────────────────────
// Cold Li-ion cells deliver less power: the physiology model publishes a
// capacity multiplier 0.3-1.0 (aee_physiology_batteryTemperatureDerating).
// A derated battery cuts effective transmit power: in dBm the loss is
// 10*log10(derating).  At 0.7 (about -20 C) that is -1.55 dB; at 0.3
// (severe cold) -5.2 dB.  The signal fraction follows as sqrt of the
// linear power ratio, so a 0.7 battery transmits at ~84% of nominal range.
private _batteryDerate = missionNamespace getVariable [QEGVAR(physiology,batteryTemperatureDerating), 1.0];
if !(_batteryDerate isEqualType 0) then { _batteryDerate = 1.0; };
_batteryDerate = _batteryDerate max 0.3 min 1.0;
if (_batteryDerate < 1.0 && (missionNamespace getVariable [QGVAR(batteryDeratingEnabled), true])) then {
    _txPowerDBm = _txPowerDBm + (10 * log _batteryDerate);
};

// ─── Free-space path loss (Friis) ──────────────────────────────────────────
// SQF's log command is base-10 (verified in-game: log 100 = 2).  Friis in
// SQF is therefore 20*log10(d) + 20*log10(f) - 147.55 with NO radix
// conversion.  (A previous version divided by 2.302585 assuming natural
// log, which double-converted and produced FSPL -46 dB — caught by the
// in-game RPT, invisible to the range-checked index.)
private _fspl = (20 * log _distM) + (20 * log _freqHz) - 147.55;

// ─── Evaporation duct (issue #37) ─────────────────────────────────────────
// The evaporation duct is an SHF phenomenon (1-40 GHz, best 10-18 GHz):
// a strong humidity gradient just above the sea traps radar/satcom links
// and extends range 3-10x.  VHF/UHF tactical radios (30-300 MHz) are
// largely UNAFFECTED - links below the duct's cutoff frequency get NO
// bonus.  This replaces the old flat temperature/humidity/pressure
// heuristic, which applied a dB bonus to every band regardless of the
// physics.
//
// Modified refractivity deficit (N-units): the duct is driven by the
// sea-air water-vapour deficit.  The sea surface is saturated (RH 100%);
// the air above carries less vapour.  From the definition
//   N = 77.6 p/T + 3.73e5 e/T^2,
// the deficit is dN = 3.73e5 * (esat(SST) - e_air) / T^2.  Verified
// anchors: tropics dN~14 (tall duct, low cutoff), Gulf dN~8, North Sea
// dN~2 (weak duct, high cutoff).
//
// Duct height (Paulus-Jeske): a stable air-sea gradient (warm air over
// cold sea) raises the duct; delta = clamp(1.5 + (T - SST) * 2.5, 3, 25)
// metres (world mean ~13 m, tropics to 40 m, North Sea 5-6 m).
//
// Hall cutoff: lambda_max = 2.5e-3 * sqrt(dN/H - 0.157) * H^1.5,
// f_min = c / lambda_max.  Below f_min the duct is too small for the
// wavelength: no trapping.  (Verified: H=13, dN=10 -> 3.27 GHz.)
private _ductBonus = 0;
private _sst = missionNamespace getVariable [QEGVAR(core,seaSurfaceTemperature), nil];
if (!isNil "_sst" && _sst isEqualType 0) then {
    private _delta = 1.5 + ((_T - _sst) * 2.5);
    _delta = _delta max 3 min 25;

    // Saturated vapour pressure at the sea surface (Buck), and ambient
    // vapour pressure from RH.  Convert the deficit to N-units.
    private _esatSea = 6.1121 * exp ((18.678 - (_sst / 234.5)) * (_sst / (257.14 + _sst)));
    private _esatAir = 6.1121 * exp ((18.678 - (_T / 234.5)) * (_T / (257.14 + _T)));
    private _eAir = (_RH / 100) * _esatAir;
    private _dn = 3.73e5 * ((_esatSea - _eAir) * 0.1) / ((_T + 273.15) ^ 2);
    if (_dn < 0) then { _dn = 0 };

    // Hall cutoff: duct traps only wavelengths small enough to fit.
    private _lam = 2.5e-3 * (sqrt ((_dn / _delta) - 0.157)) * (_delta ^ 1.5);
    if !(isNil "_lam" || _lam <= 0) then {
        private _fMinHz = 3e8 / _lam;
        if (_freqHz >= _fMinHz) then {
            // Range extension 3-10x (cap 150 km), attenuation 0.3 dB/km
            // beyond the ~44.8 km over-the-horizon limit.
            private _ductFactor = ((_delta / 13) max 0.3) min 2.5;
            _ductBonus = 6 * _ductFactor;                   // up to +15 dB
            private _rangeKm = _distM / 1000;
            if (_rangeKm > 44.8) then {
                // Attenuation beyond the OTH limit, clamped so the duct
                // never becomes a net penalty (it either extends range
                // or is neutral, per the ducting validation).
                _ductBonus = (_ductBonus - (_rangeKm * 0.3)) max 0;
            };
        };
    };
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
