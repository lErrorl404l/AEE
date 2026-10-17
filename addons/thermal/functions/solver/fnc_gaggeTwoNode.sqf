#include "..\..\script_component.hpp"
/*
 * aee_thermal_fnc_gaggeTwoNode
 *
 * Human core and skin temperature in time: the Gagge two-node model
 * (Gagge, Fobelets & Berglund 1986, ASHRAE Trans 92(2B):709), in the form
 * of the ASHRAE 55-2020 reference code (as implemented by pythermalcomfort,
 * two_nodes_gagge), integrated in its own one-minute steps.  Pure.
 *
 * Per step (all per m2 of body surface):
 *   t_cl, h_r by iteration (clothing emissivity 0.95, radiating area 0.73
 *   standing), h_c = max(3.0 p^0.53, 8.6 (v p)^0.53, 5.66 (met - 0.85)^0.39);
 *   q_sens = (t_sk - t_op) / (r_a + r_clo);
 *   core-skin flux (t_cr - t_sk)(5.28 + 1.163 m_bl);
 *   respiration C_res = 0.0014 M (34 - t_a), E_res = 0.0023 M (44 - p_a),
 *   M the working rate, fixed once before the loop as the reference does;
 *   storage into 0.97 alpha m and 0.97 (1 - alpha) m (70 kg);
 *   vasomotion m_bl = (6.3 + 120 c_warm)/(1 + 0.5 cold_sk) in [0.5, 90];
 *   sweat m_rsw = 170 warm_body exp(warm_sk / 10.7), E_rsw = 0.68 m_rsw,
 *   wettedness w = 0.06 + 0.94 E_rsw / E_max, capped at the critical
 *   wettedness 0.59 v^-0.08 (clothed); shivering 19.4 cold_sk cold_cr.
 * Start (an empty state): t_cr 36.8, t_sk 33.7, m_bl 6.3, alpha 0.1 and
 *   e_sk = 0.1 met, the reference's initial evaporative loss (0.12 W at
 *   1.2 met), overwritten by the first step.
 * Sun: the ASHRAE 55-2020 Appendix C (SolarCal) effective radiant field
 *   ERF = (0.5 f_eff (I_diff + I_th R_floor) + f_p f_bes I_dir) a_sw / 0.95
 *   raises the mean radiant temperature by ERF / (f_eff h_r), f_eff 0.725,
 *   h_r 6.012; f_p = 0.308 cos(b (0.998 - b^2/50000)) (standing body, sun
 *   altitude b); the beam/diffuse split is Erbs, Klein & Duffie 1982.
 * Water: an immersed body exchanges with the water (h from Boutelier,
 *   Bougues & Timbal 1977; no radiation, no evaporation).  Ordinary
 *   garments flood and give little insulation in water (Hayward, Eckerson &
 *   Collis 1975, J Appl Physiol 38:1073, light clothing slowed cooling by
 *   about a tenth), so no clothing resistance is applied.
 *
 * Arguments:
 *   0: state [tCore, tSkin, mBl, eSkin, alpha, immersedMinutes] ([] = the
 *      neutral start)
 *   1: dt, s
 *   2: air temperature, C
 *   3: mean radiant temperature (longwave), C
 *   4: air speed, m/s
 *   5: metabolic rate, W/m2
 *   6: clothing insulation, clo
 *   7: water vapour pressure, mmHg
 *   8: pressure, Pa
 *   9: global horizontal solar irradiance, W/m2
 *  10: sun altitude, deg
 *  11: sun exposure 0..1 (beam reaching the body)
 *  12: shortwave absorptance of the clothed body
 *  13: water temperature, C (below -100 = not immersed)
 *  14: water speed, m/s
 *  15: skin perfusion index 0..1 (shock vasoconstriction)
 *  16: swimming (BOOL)
 * Return: the new state [tCore, tSkin, mBl, eSkin, alpha, immersedMinutes]
 */
params [
    ["_state", [], [[]]], ["_dt", 60, [0]],
    ["_tdb", 25, [0]], ["_trLw", 25, [0]], ["_v", 0.1, [0]], ["_metW", 58.2, [0]],
    ["_clo", 0.6, [0]], ["_pa", 10, [0]], ["_patm", 101325, [0]],
    ["_ghi", 0, [0]], ["_sunAlt", -90, [0]], ["_exposure", 1, [0]], ["_aSw", 0.7, [0]],
    ["_tWater", -273, [0]], ["_vWater", 0, [0]], ["_perfusion", 1, [0]],
    ["_swimming", false, [false]]
];
private _met = _metW / 58.2;
private _tSk = 33.7;
private _tCr = 36.8;
private _mBl = 6.3;
private _eSk = 0.1 * _met;
private _alfa = 0.1;
private _immMin = 0;
if ((count _state) >= 5) then {
    _tCr = _state select 0; _tSk = _state select 1; _mBl = _state select 2;
    _eSk = _state select 3; _alfa = _state select 4;
    if ((count _state) > 5) then { _immMin = _state select 5; };
};

private _immersed = _tWater > -100;
private _patmA = _patm / 101325;
private _vA = _v max 0.1;
private _rClo = 0.155 * _clo;
private _fAcl = 1 + 0.15 * _clo;
private _lr = 2.2 / _patmA;
private _iCl = [1.0, 0.45] select (_clo > 0);
private _wMax = if (_clo > 0) then { 0.59 * (_vA ^ -0.08) } else { 0.38 * (_vA ^ -0.29) };
private _hcc = (3.0 * (_patmA ^ 0.53)) max (8.600001 * ((_vA * _patmA) ^ 0.53));
if (_met > 0.85) then { _hcc = _hcc max (5.66 * ((_met - 0.85) ^ 0.39)); };

// SolarCal: the sun as a mean radiant temperature increment.
private _tr = _trLw;
if (!_immersed && _ghi > 0 && _sunAlt > 0) then {
    private _g0 = 1361 * (sin _sunAlt);
    private _kt = (_ghi / (_g0 max 1)) min 1;
    private _kd = 0.165;
    if (_kt <= 0.22) then { _kd = 1 - 0.09 * _kt; } else {
        if (_kt <= 0.8) then { _kd = 0.9511 - 0.1604 * _kt + 4.388 * _kt ^ 2 - 16.638 * _kt ^ 3 + 12.336 * _kt ^ 4; };
    };
    private _iDiff = _ghi * _kd;
    private _iDir = (_ghi - _iDiff) / ((sin _sunAlt) max 0.05);
    private _fp = 0.308 * (cos (_sunAlt * (0.998 - (_sunAlt * _sunAlt) / 50000)));
    private _erf = ((0.5 * 0.725 * (_iDiff + _ghi * 0.2)) + (_fp * (_exposure max 0 min 1) * _iDir)) * _aSw / 0.95;
    _tr = _tr + _erf / (0.725 * 6.012);
};

private _sbc = 0.000000056697;
private _m = _metW;
private _rm = _metW;
// Respiration is fixed once from the working rate, as the reference does.
// The shivering term at the end of the loop raises the core storage term,
// but the reference never lets it raise the respiratory loss.
// pythermalcomfort _gagge_two_nodes_optimized: q_res and c_res are computed
// once before the loop from m = met * 58.2.
private _qRes = 0.0023 * _rm * (44 - _pa);
private _cRes = 0.0014 * _rm * (34 - _tdb);
private _remaining = _dt max 0;
while { _remaining > 0 } do {
    private _step = _remaining min 60;
    _remaining = _remaining - _step;
    private _f = _step / 60;
    private _qSens = 0;
    if (_immersed) then {
        private _hW = if (_vWater > 0) then { 272.9 * (_vWater ^ 0.5) } else { 43.0 };
        _qSens = (_tSk - _tWater) * _hW;
        _qRes = 0;
        _cRes = 0;
    } else {
        private _hr = 4.7;
        private _ht = _hr + _hcc;
        private _ra = 1 / (_fAcl * _ht);
        private _top = (_hr * _tr + _hcc * _tdb) / _ht;
        private _tCl = (_ra * _tSk + _rClo * _top) / (_ra + _rClo);
        for "_k" from 1 to 150 do {
            _hr = 4 * 0.95 * _sbc * ((((_tCl + _tr) / 2) + 273.15) ^ 3) * 0.73;
            _ht = _hr + _hcc;
            _ra = 1 / (_fAcl * _ht);
            _top = (_hr * _tr + _hcc * _tdb) / _ht;
            private _new = (_ra * _tSk + _rClo * _top) / (_ra + _rClo);
            if ((abs (_new - _tCl)) <= 0.01) exitWith { _tCl = _new; };
            _tCl = _new;
        };
        _qSens = (_tSk - _top) / (_ra + _rClo);
    };
    private _hfCs = (_tCr - _tSk) * (5.28 + 1.163 * _mBl);
    private _sCore = _m - _hfCs - _qRes - _cRes;
    private _sSkin = _hfCs - _qSens - _eSk;
    private _area = 1.8258;
    _tSk = _tSk + _f * (_sSkin * _area) / (0.97 * _alfa * 70 * 60);
    private _hayward = _immersed && {(_immMin + _f) > 15};
    if (!_hayward) then {
        _tCr = _tCr + _f * (_sCore * _area) / (0.97 * (1 - _alfa) * 70 * 60);
    };
    private _tBody = _alfa * _tSk + (1 - _alfa) * _tCr;
    private _skSig = _tSk - 33.7;
    private _warmSk = _skSig max 0;
    private _coldSk = (-_skSig) max 0;
    private _cSig = _tCr - 36.8;
    private _cWarm = _cSig max 0;
    private _cCold = (-_cSig) max 0;
    private _warmB = (_tBody - (0.1 * 33.7 + 0.9 * 36.8)) max 0;
    _mBl = ((6.3 + 120 * _cWarm) / (1 + 0.5 * _coldSk)) min 90 max 0.5;
    _mBl = (_mBl * ((_perfusion max 0) min 1)) max 0.5;
    private _eRsw = 0.68 * ((170 * _warmB * exp (_warmSk / 10.7)) min 500);
    private _eDiff = 0;
    if (_immersed) then {
        _eSk = 0;
    } else {
        private _rEa = 1 / (_lr * _fAcl * _hcc);
        private _rEcl = _rClo / (_lr * _iCl);
        private _eMax = ((exp (18.6686 - 4030.183 / (_tSk + 235))) - _pa) / (_rEa + _rEcl);
        if (_eMax == 0) then { _eMax = 0.001; };
        private _pRsw = _eRsw / _eMax;
        private _w = 0.06 + 0.94 * _pRsw;
        _eDiff = _w * _eMax - _eRsw;
        if (_w > _wMax) then {
            _w = _wMax;
            _pRsw = _wMax / 0.94;
            _eRsw = _pRsw * _eMax;
            _eDiff = 0.06 * (1 - _pRsw) * _eMax;
        };
        if (_eMax < 0) then { _eDiff = 0; _eRsw = 0; _w = _wMax; };
        _eSk = _eRsw + _eDiff;
    };
    // Immersion: the Gagge core balances shivering against the loss and
    // under-predicts cold-water cooling (Tikuisis 1988).  The measured rectal
    // cooling rate of still, lightly clothed adults takes over after the
    // first 15 min: 0.0785 - 0.0034 Tw C/min, 35 % faster swimming (Hayward,
    // Eckerson & Collis 1975, Can J Physiol Pharmacol 53:21).
    if (_immersed) then {
        _immMin = _immMin + _f;
        if (_immMin > 15) then {
            private _rate = ((0.0785 - 0.0034 * _tWater) max 0) * ([1, 1.35] select _swimming);
            _tCr = _tCr - _rate * _f;
        };
    } else {
        _immMin = 0;
    };
    _m = _rm + 19.4 * _coldSk * _cCold;
    _alfa = 0.0417737 + 0.7451833 / (_mBl + 0.585417);
};
[_tCr, _tSk, _mBl, _eSk, _alfa, _immMin]
