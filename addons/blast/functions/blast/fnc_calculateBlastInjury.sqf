#include "..\..\script_component.hpp"

/*
Blast injury from overpressure (Bowen 1968 P-I curves, tertiary throw).

Takes the Kingery-Bulmash P_so and t_d from
fnc_calculateBlastOverpressure and applies the injury thresholds:

  Primary (blast lung / eardrum)  - pressure-duration (P-I) dependent
  Tertiary (throw)                - blast wind drag exceeds body weight

Bowen curves (70 kg man, from the compiled Zirh & Sari 2025 data):
  Eardrum: 35 kPa threshold, 103 kPa 50%, 202 kPa 100%.
  Lung (P-I): t_d <= 10 ms: 55/150/200/300 kPa (thresh/1%/50%/99%)
              10-50 ms:     42/110/160/220
              50-200 ms:    28/90/125/185
  Linear interpolation in t_d between the three rows.

Tertiary blowdown: measured.  The blast wind carries a dynamic pressure
q_o = 2.5·P_so^2/(7·P_0 + P_so) (Kinney & Graham 1985), whose impulse over
the positive phase drives the body.  Richmond & Fletcher blew instrumented
dummies down on the open desert surface (Project LN401; "Blast Displacement
of Dummies on the Surface" and "Blast Displacement of Prone Dummies"), and
their three reported points, compiled as Table 3 of the EC Joint Research
Centre survey "A survey of computational models for blast induced human
injuries for security" (JRC119310, 2019), are

     dynamic pressure impulse   peak body velocity   outcome
         8.78 kPa.ms                0.092 m/s        no blowdown
        58.27 kPa.ms                0.61  m/s        50 % blowdown
       379.13 kPa.ms                4.0   m/s        1 % serious injury

so the blowdown probability is interpolated between those measured anchors,
linearly in the logarithm of the impulse.

Indoor amplification: 2x (vented) to 4x (sealed) applied to P_so before
the thresholds.

Input:  [_pSo_kPa, _td_ms, _indoorMult] - overpressure, duration, 1/2/4
Output: [eardrum01, lungThresh01, lung1Pct01, lung50Pct01, lung99Pct01,
         throw01]  - probabilities 0-1 for each injury
*/

params [["_pSo", 0, [0]], ["_td", 0, [0]], ["_indoorMult", 1, [0]]];

if (_pSo <= 0) exitWith { [0, 0, 0, 0, 0, 0] };

private _P = _pSo * (_indoorMult max 1);

// ─── Eardrum (Bowen: 35/103/202 kPa -> 0%/50%/100%) ─────────────────────
// Piecewise linear between the three anchors.
private _eardrum = 0;
if (_P >= 202) then {
    _eardrum = 1;
} else {
    if (_P >= 103) then {
        _eardrum = 0.5 + (_P - 103) * (0.5 / (202 - 103));
    } else {
        if (_P > 35) then {
            _eardrum = (_P - 35) * (0.5 / (103 - 35));
        };
    };
};

// ─── Blast lung (Bowen P-I, interpolate in t_d) ──────────────────────────
// Three rows: [t_d range, thresh, 1%, 50%, 99%].  Interpolate thresholds
// between rows on log t_d; interpolate probability linearly between the
// four pressure points within the row.
private _rows = [
    [10,  55, 150, 200, 300],
    [50,  42, 110, 160, 220],
    [200, 28,  90, 125, 185]
];
private _tClamp = (0.1 max _td) min 200;
// Find the bracketing rows on log-t_d.
private _i0 = 0;
private _i1 = 0;
if (_tClamp <= 10) then { _i0 = 0; _i1 = 0; }
else {
    if (_tClamp >= 200) then { _i0 = 2; _i1 = 2; }
    else {
        // interpolate between the two nearest rows in log space
        if (_tClamp < 50) then { _i0 = 0; _i1 = 1; } else { _i0 = 1; _i1 = 2; };
    };
};
private _row0 = _rows select _i0;
private _row1 = _rows select _i1;
private _w = if (_i0 == _i1) then { 0 } else {
    (ln _tClamp - ln (_row0 select 0)) / (ln (_row1 select 0) - ln (_row0 select 0))
};
_w = (0 max _w) min 1;

// Interpolated thresholds [thresh, 1%, 50%, 99%]
private _thr = [];
for "_i" from 1 to 4 do {
    private _t0 = _row0 select _i;
    private _t1 = _row1 select _i;
    _thr pushBack (_t0 + (_t1 - _t0) * _w);
};

// Probability of exceeding each pressure threshold (linear between them).
// NOTE the 100: every branch here is a PERCENTAGE, divided by 100 below.
// Returning 1 instead collapsed a certain-death overpressure to 1 per cent.
private _lungThresh = if (_P >= (_thr select 3)) then { 100 } else {
    if (_P > (_thr select 0)) then {
        // thresh->1% maps to 0->1% prob; 1%->50% maps 1->50; 50%->99% maps 50->99
        if (_P < (_thr select 1)) then {
            0 + (_P - (_thr select 0)) * (1 / ((_thr select 1) - (_thr select 0)));
        } else {
            if (_P < (_thr select 2)) then {
                1 + (_P - (_thr select 1)) * (49 / ((_thr select 2) - (_thr select 1)));
            } else {
                50 + (_P - (_thr select 2)) * (49 / ((_thr select 3) - (_thr select 2)));
            };
        };
    } else { 0 };
};
_lungThresh = (_lungThresh / 100) max 0 min 1;

private _lung1 = (parseNumber (_P >= (_thr select 1))) * 0.01;
private _lung50 = (parseNumber (_P >= (_thr select 2))) * 0.5;
private _lung99 = parseNumber (_P >= (_thr select 3));

// ─── Tertiary blowdown (blast wind) ──────────────────────────────────────
// Peak dynamic pressure behind the shock (Kinney & Graham 1985), then its
// impulse over the positive phase as the equivalent triangular pulse the
// blast literature uses for impulse (UFC 3-340-02): J_q = q_o * t_d / 2.
private _qo = 2.5 * _P * _P / (7 * 101.325 + _P);
private _jq = _qo * (_td max 0) / 2;          // kPa.ms

// The Richmond & Fletcher dummy anchors (see the header), log-interpolated.
private _throw = 0;
if (_jq > 8.78) then {
    if (_jq >= 379.13) then {
        _throw = 1;
    } else {
        if (_jq >= 58.27) then {
            _throw = 0.5 + 0.5 * ((ln _jq - ln 58.27) / (ln 379.13 - ln 58.27));
        } else {
            _throw = 0.5 * ((ln _jq - ln 8.78) / (ln 58.27 - ln 8.78));
        };
    };
};
_throw = (_throw max 0) min 1;

[_eardrum, _lungThresh, _lung1, _lung50, _lung99, _throw]
