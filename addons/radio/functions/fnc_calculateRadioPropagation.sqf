#include "..\script_component.hpp"

/*
VHF/UHF radio propagation index (0.3–2.0) for atmospheric ducting and absorption.

1.0 = standard range (ITU reference atmosphere).  Values >1 extend radio
line-of-sight; values <1 reduce effective range.

Factors:
  • Temperature inversion (warm night / large diurnal swing)  +0.3 to +0.8
  • High humidity (>60 %)                                      +0.05 per 10 % above 50 %
  • High pressure (>1020 hPa)                                  +0.02 per 10 hPa above 1013
  • Hot & dry (temp >30 °C, RH <30 %)                          –0.1

Stored in QGVAR(radioPropagationIndex) for consumption by radio/TFAR
integration and AI communication-range modelling.
*/

private _T   = EGVAR(core,currentTemperature);
private _RH  = EGVAR(core,currentHumidity);
private _P   = EGVAR(core,currentPressure);
private _sun = sunOrMoon;

if (isNil "_T")  exitWith { 1.0 };
if (isNil "_RH") exitWith { 1.0 };
if (isNil "_P")  then { _P = 1013 };

private _index = 1.0;

// ─── Temperature inversion (ducting) ──────────────────────────────────────
// Warm night or strong diurnal-setup conditions
private _inversionBonus = 0;
if (_T > 25 && _sun == -1) then {
    _inversionBonus = ((_T - 25) / 20) min 0.5;  // 0.3 at 25°C, 0.8 at 45°C
};
// Large diurnal swing proxy — hot clear day in arid biome
private _biome = EGVAR(core,biome);
if (_T > 30 && _RH < 30 && overcast < 0.3 && !isNil "_biome" && _biome in ["BWh","BWk","BSh","BSk"]) then {
    _inversionBonus = (_inversionBonus max 0.5);
};
_index = _index + _inversionBonus;

// ─── High humidity — water-vapour refraction ─────────────────────────────
if (_RH > 60) then {
    _index = _index + ((_RH - 50) / 10) * 0.05;
};

// ─── High pressure — density gradient enhancement ─────────────────────────
if (_P > 1020) then {
    _index = _index + ((_P - 1013) / 10) * 0.02;
};

// ─── Hot dry — absorption penalty ─────────────────────────────────────────
if (_T > 30 && _RH < 30) then {
    _index = _index - 0.1;
};

// ─── Clamp ────────────────────────────────────────────────────────────────
_index = _index max 0.3 min 2.0;

missionNamespace setVariable [QGVAR(radioPropagationIndex), _index];

if (EGVAR(core,diagnostic)) then {
    diag_log text format [
        "[AEE] RadioPropagation: %1 (inv bonus %2 | RH bonus %3 | P bonus %4 | hot-dry penalty %5)",
        [_index, 2] call CBA_fnc_formatNumber,
        [_inversionBonus, 2] call CBA_fnc_formatNumber,
        [if (_RH > 60) then { ((_RH - 50) / 10) * 0.05 } else { 0 }, 3] call CBA_fnc_formatNumber,
        [if (_P > 1020) then { ((_P - 1013) / 10) * 0.02 } else { 0 }, 3] call CBA_fnc_formatNumber,
        [if (_T > 30 && _RH < 30) then { -0.1 } else { 0 }, 2] call CBA_fnc_formatNumber
    ];
};

_index
