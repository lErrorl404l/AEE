#include "..\..\script_component.hpp"

// ─── Real Koppen climate classification (Peel et al. 2007) ────────────────
// Classifies a climate from 12 monthly temperature and precipitation
// normals. This is the actual Koppen boundary algorithm, not a latitude
// heuristic.
//
// Input:  [_monthlyTemps, _monthlyPrecip, _altitudeM]
//   _monthlyTemps  12 monthly mean temperatures, °C (Jan..Dec)
//   _monthlyPrecip 12 monthly precipitation totals, mm (Jan..Dec)
//   _altitudeM     station altitude, m; applies a 6.5 °C/km lapse rate
// Output: Koppen code string, e.g. "Cfb"
//
// Boundary rules (exact):
//   Arid (B): P_ann < P_thresh, where the warm half-year is the 6
//     consecutive months with the highest mean temperature.
//       P_thresh = 20·T_ann + 280  if ≥70% of precip falls in the warm half
//       P_thresh = 20·T_ann        if ≥70% of precip falls in the cool half
//       P_thresh = 20·T_ann + 140  otherwise
//     BWh/BSh if T_ann ≥ 18, BWk/BSk if T_ann < 18.
//     Desert (Wh/Wk) if P_ann < 0.5·P_thresh, semi-arid (Sh/Sk) otherwise.
//   Polar (E): T_warmest ≤ 10.  ET if T_warmest > 0, EF if T_warmest ≤ 0.
//   Tropical (A): T_coldest ≥ 18.
//     Af if driest month ≥ 60 mm.
//     Am if driest month ≥ 100 − P_ann/25.
//     Aw otherwise.
//   Continental (D): T_coldest ≤ −3 and T_warmest > 10.
//     Second letter by the same summer/winter test as C:
//       Ds (dry summer): driest summer month < 40 mm and < ⅓ of the
//         wettest winter month (continental Mediterranean: Ankara Dsa).
//       Dw (dry winter): wettest summer month ≥ 10 × driest winter
//         month (monsoon continental: Beijing Dwa, Harbin Dwb).
//       Df (humid): otherwise (the original four codes).
//     Third letter: d if T_coldest ≤ −38, a if T_warmest ≥ 22, b if ≥4
//       months ≥ 10 °C, else c.  So Df -> Dfa/Dfb/Dfc/Dfd; Ds ->
//       Dsa/Dsb/Dsc/Dsd; Dw -> Dwa/Dwb/Dwc/Dwd.
//   Temperate (C): −3 < T_coldest < 18.
//     Cs (Mediterranean): driest summer month < 40 mm and < ⅓ of the
//       wettest winter month.  Csa if T_warmest ≥ 22, Csb if ≥4 months
//       ≥ 10 °C, else Csc.
//     Cw (dry winter): wettest summer month ≥ 10 × driest winter month.
//       Cwa if T_warmest ≥ 22, Cwb if ≥4 months ≥ 10 °C, else Cwc.
//     Cf (humid): otherwise.  Cfa if T_warmest ≥ 22, Cfb if ≥4 months
//       ≥ 10 °C, else Cfc.
//
// Boundary test vectors (temps °C, precip mm → expected code):
//   Af:  all months 26, all months 150 → Af
//   Am:  [24,25,26,27,28,28,28,28,27,26,25,24],
//        [50,50,60,80,150,200,220,220,180,120,70,60] → Am
//   Aw:  [22,23,24,25,26,26,26,26,25,24,23,22],
//        [20,20,30,50,100,150,160,150,100,60,30,25] → Aw
//   BWh: [20,23,27,32,37,40,42,41,38,32,26,21], all 5 → BWh
//   BWk: [2,6,12,18,24,30,33,32,26,18,10,4], all 5 → BWk
//   BSh: [20,22,25,28,32,35,36,35,33,29,24,20], all 32 → BSh
//   BSk: [2,5,10,16,22,28,32,31,26,18,10,4], all 24 → BSk
//   Csa: [12,13,15,18,22,27,30,30,26,21,16,13],
//        [80,70,60,50,40,15,5,8,25,45,65,75] → Csa
//   Csb: [10,11,13,15,18,20,21,21,19,16,13,11],
//        [90,80,70,60,50,20,8,10,30,50,70,85] → Csb
//   Cfa: [10,12,16,20,24,28,30,30,27,22,16,12],
//        [70,68,65,63,65,68,72,72,70,68,66,68] → Cfa
//   Cfb: [8,8,10,13,16,19,21,21,18,14,11,8],
//        [80,78,76,74,75,76,76,76,77,79,80,81] → Cfb
//   Cwa: [12,14,18,22,26,28,30,30,28,24,18,14],
//        [10,10,15,20,60,120,150,150,120,60,20,12] → Cwa
//   Dfa: [-5,-3,4,12,18,22,25,24,19,12,4,-2],
//        [82,80,76,70,68,70,72,74,76,78,80,82] → Dfa
//   Dfb: [-10,-8,-2,5,11,16,19,18,13,6,-2,-8],
//        [76,74,72,68,66,68,72,74,76,78,78,78] → Dfb
//   Dfc: [-20,-18,-12,-4,2,7,11,10,5,-1,-9,-17],
//        [70,68,66,64,62,64,68,70,72,74,74,72] → Dfc
//   ET:  [-15,-15,-12,-7,-2,2,4,4,1,-3,-8,-13],
//        [78,78,78,76,75,75,76,78,78,80,80,80] → ET
//   EF:  [-30,-28,-25,-20,-15,-10,-8,-9,-12,-18,-24,-28],
//        [40,40,40,40,40,40,40,40,40,40,40,40] → EF

params [
    ["_monthlyTemps", [], [[]]],
    ["_monthlyPrecip", [], [[]]],
    ["_altitudeM", 0, [0]]
];

if (count _monthlyTemps != 12 || count _monthlyPrecip != 12) exitWith { "" };

// Altitude lapse-rate correction: 6.5 °C per 1000 m
if (_altitudeM > 0) then {
    private _lapse = 0.0065 * _altitudeM;
    _monthlyTemps = _monthlyTemps apply { _x - _lapse; };
};

// ─── Annual values ─────────────────────────────────────────────────────────
private _T_ann = 0;
private _P_ann = 0;
private _T_warmest = -1e9;
private _T_coldest = 1e9;
private _P_driest = 1e9;
for "_m" from 0 to 11 do {
    private _t = _monthlyTemps select _m;
    private _p = _monthlyPrecip select _m;
    _T_ann = _T_ann + _t;
    _P_ann = _P_ann + _p;
    if (_t > _T_warmest) then { _T_warmest = _t; };
    if (_t < _T_coldest) then { _T_coldest = _t; };
    if (_p < _P_driest) then { _P_driest = _p; };
};
_T_ann = _T_ann / 12;

// ─── Warm half-year: the 6 consecutive months with the highest mean ───────
private _bestStart = 0;
private _bestMean = -1e9;
for "_s" from 0 to 11 do {
    private _sum = 0;
    for "_k" from 0 to 5 do {
        _sum = _sum + (_monthlyTemps select ((_s + _k) mod 12));
    };
    private _mean = _sum / 6;
    if (_mean > _bestMean) then { _bestMean = _mean; _bestStart = _s; };
};
private _summerPrecip = 0;
for "_k" from 0 to 5 do {
    _summerPrecip = _summerPrecip + (_monthlyPrecip select ((_bestStart + _k) mod 12));
};
private _winterPrecip = _P_ann - _summerPrecip;

// ─── Arid (B) ──────────────────────────────────────────────────────────────
private _P_thresh = 0;
if (_summerPrecip >= 0.7 * _P_ann) then {
    _P_thresh = 20 * _T_ann + 280;
} else {
    if (_winterPrecip >= 0.7 * _P_ann) then {
        _P_thresh = 20 * _T_ann;
    } else {
        _P_thresh = 20 * _T_ann + 140;
    };
};

if (_P_ann < _P_thresh) exitWith {
    if (_T_ann >= 18) then {
        ["BSh", "BWh"] select (_P_ann < 0.5 * _P_thresh)
    } else {
        ["BSk", "BWk"] select (_P_ann < 0.5 * _P_thresh)
    };
};

// ─── Polar (E) ─────────────────────────────────────────────────────────────
if (_T_warmest <= 10) exitWith {
    ["ET", "EF"] select (_T_warmest <= 0)
};

// ─── Tropical (A) ──────────────────────────────────────────────────────────
if (_T_coldest >= 18) exitWith {
    if (_P_driest >= 60) then {
        "Af"
    } else {
        ["Aw", "Am"] select (_P_driest >= 100 - _P_ann / 25)
    };
};

// ─── Months with mean temperature ≥ 10 °C ─────────────────────────────────
private _months10 = 0;
{ if (_x >= 10) then { _months10 = _months10 + 1; }; } forEach _monthlyTemps;

// ─── Summer/winter precipitation sets from the warm half-year ─────────────
// Shared by the Continental (D) and Temperate (C) branches.  The warm
// half-year is the 6 consecutive warmest months (start _bestStart, found
// above for the arid threshold).
private _driestSummer = 1e9;
private _wettestSummer = -1e9;
private _driestWinter = 1e9;
private _wettestWinter = -1e9;
for "_k" from 0 to 5 do {
    private _pS = _monthlyPrecip select ((_bestStart + _k) mod 12);
    private _pW = _monthlyPrecip select ((_bestStart + 6 + _k) mod 12);
    if (_pS < _driestSummer) then { _driestSummer = _pS; };
    if (_pS > _wettestSummer) then { _wettestSummer = _pS; };
    if (_pW < _driestWinter) then { _driestWinter = _pW; };
    if (_pW > _wettestWinter) then { _wettestWinter = _pW; };
};
// Second-letter test: s = dry summer (Mediterranean), w = dry winter
// (monsoon), f = fully humid.  Identical criteria for D and C.
private _drySummer = (_driestSummer < 40) && (_driestSummer < _wettestWinter / 3);
private _dryWinter = _wettestSummer >= 10 * _driestWinter;

// ─── Continental (D) vs Temperate (C) ─────────────────────────────────────
if (_T_coldest <= -3) then {
    // Continental.  Third letter: d (coldest <= -38, severe), a (warmest
    // >= 22), b (>= 4 months >= 10), c (1-3 months >= 10).
    private _dThird = if (_T_coldest <= -38) then {
        "d"
    } else {
        if (_T_warmest >= 22) then {
            "a"
        } else {
            ["c", "b"] select (_months10 >= 4)
        };
    };
    if (_drySummer) then {
        // Continental dry-summer (Ds): Ankara Dsa, alpine Dsb/Dsc.
        "Ds" + _dThird
    } else {
        if (_dryWinter) then {
            // Continental dry-winter (Dw): Beijing Dwa, Harbin Dwb.
            "Dw" + _dThird
        } else {
            // Continental fully humid (Df): the original four codes.
            "Df" + _dThird
        };
    };
} else {
    // Temperate
    if (_drySummer) then {
        // Mediterranean (Cs)
        if (_T_warmest >= 22) then {
            "Csa"
        } else {
            ["Csc", "Csb"] select (_months10 >= 4)
        };
    } else {
        if (_dryWinter) then {
            // Dry winter (Cw)
            if (_T_warmest >= 22) then {
                "Cwa"
            } else {
                ["Cwc", "Cwb"] select (_months10 >= 4)
            };
        } else {
            // Humid (Cf)
            if (_T_warmest >= 22) then {
                "Cfa"
            } else {
                ["Cfc", "Cfb"] select (_months10 >= 4)
            };
        };
    };
};
