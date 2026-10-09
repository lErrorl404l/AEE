#include "..\..\script_component.hpp"
/*
Two-node core/skin temperature kernel (issue #191).

PURE: inputs to outputs.  It reads no engine state and writes none.  The driver
FUNC(solveTwoNodeSelection) resolves the material properties, calls this kernel
through the dispatcher (native when ready, else this SQF reference), and
publishes the human core temperature.

Physics (all sourced - issue #189 audit standards):

  Core balance (linear in T_cr):
    q_gen + q_shiv*A - q_resp*A - k_coupling*(T_cr - T_sk) = 0
  Skin balance (nonlinear in T_sk):
    q_solar + k_coupling*(T_cr - T_sk) - q_conv - q_rad - q_evap = 0

  k_coupling (W/K), human = (K_min + c_p,bl * m_bl) * A
    K_min = 5.28 W/(m2K)  minimum tissue conductance (Gagge 1986)
    c_p,bl = 4186 J/(kgK) blood specific heat
    m_bl   = skin blood flow, L/(h.m2):
             (6.3 + 200*W_sig)/(1 + 0.5*C_sig)
             W_sig = max(0, T_cr - 36.8)  CORE vasodilation signal
             C_sig = max(0, 33.7 - T_sk)   skin vasoconstriction signal
             clipped [0.5, 90] L/(h.m2) (Gagge, Fobelets & Berglund 1986)
  k_coupling (W/K), engine/building = the inert conductance passed in (Fourier)
    The driver computes k * A / L_cond from the material registry.

  Shivering (Gagge 1986): q_shiv = 19.4 * C_sig * C_core_sig
    C_core_sig = max(0, 36.8 - T_cr)
    Computed from the PERSISTENT core (t_core0), never the iterating
    equilibrium - feeding it the solve value makes shivering positive
    feedback and the fixed point explodes (traced to 1363 C).

  Respiratory loss (Gagge 1986):
    C_res = 0.0014*M*(34 - T_db), E_res = 0.0023*M*(44 - p_a)
    [W/m2, p_a in torr] with M the ACTUAL metabolic rate.

  Convection (human): h_c = max(3.0 natural, 8.6*v^0.53 forced)
    per Gagge 1986.  Convection (inert): combined_h = (h_forced^3 +
    h_natural^3)^(1/3) Churchill-Usagi n=3 aiding; natural from Incropera
    Table 9.3 (vertical Churchill-Chu, horizontal-up 0.54 Ra^1/4,
    horizontal-down 0.27 Ra^1/4).

  Evaporative (endothermic path): q_evap = w * h_e * (p_sk - p_a)
    h_e = 1/(r_ea + r_ecl), r_ea = 1/(LR*f_a_cl*h_c), r_ecl = r_clo/(LR*i_cl)
    (Gagge 1986 / ASHRAE 55; LR = 16.5 K/kPa, i_cl = 0.45 clothed)
    p_sk  = saturation pressure at skin temp (Bolton 1980)
    p_a   = ambient vapour pressure (rh * p_sat(T_air))
    w     = skin wettedness (Gagge evaporative terms)

  Clothing (Gagge 1986 / ASHRAE 55): the nude dry losses are attenuated by
    F_cl = r_a/(r_a + r_clo), r_a = 1/(f_a_cl*h_t), r_clo = 0.155*clo,
    f_a_cl = 1 + 0.15*clo.

  Radiation: q_rad = f_eff * eps * sigma * (T_sk^4 - MRT^4) vs the mean
    radiant temperature (ISO 7726), NOT air temp.  f_eff = 0.73 for a
    standing body (ASHRAE 55).

  Water immersion (issue #193): an immersed surface exchanges with WATER.
    Boutelier, Bougues & Timbal 1977 measured coefficients.  Immersion is
    signalled by a real water temperature (dry sentinel below -100 C).
  Rain wettedness (issue #193): rain is EXTERNAL water, not regulated sweat.

  Transient: TWO capacities C_sk = 0.97*alpha*m and C_cr = 0.97*(1-alpha)*m
    (Gagge 1986) with the dynamic alpha, giving separate skin and core time
    constants.  Each node takes an exact exponential step to the joint
    equilibrium.  Skin tau lengthened x1.5 when the evaporative path is active.

Arguments:
  0: ambient temp (NUMBER, C)
  1: wind (NUMBER, m/s)
  2: solar flux (NUMBER, W/m2)
  3: shading exposure (NUMBER, 0..1)
  4: core mass (NUMBER, kg)
  5: skin mass (NUMBER, kg)
  6: surface area (NUMBER, m2)
  7: characteristic length (NUMBER, m) - convection plate dimension
  8: current core temp (NUMBER, C)
  9: current skin temp (NUMBER, C)
  10: internal generation (NUMBER, W)
  11: orientation (STRING) - "vertical"/"up"/"down"
  12: relative humidity (NUMBER, 0..1)
  13: mean radiant temperature (NUMBER, C)
  14: is human (BOOL)
  15: evaporative path on (BOOL)
  16: time step (NUMBER, s)
  17: water speed (NUMBER, m/s)
  18: water temperature (NUMBER, C) - below -100 = no water
  19: rain rate (NUMBER, 0..1)
  20: skin perfusion index (NUMBER, 0..1)
  21: clothing insulation (NUMBER, clo)
  22: inert conduction conductance (NUMBER, W/K) - the driver resolves it
  23: skin emissivity (NUMBER, 0..1) - the driver resolves it
  24: skin solar absorptance (NUMBER, 0..1) - the driver resolves it

Return:
  [coreTempC, skinTempC, humanCoreTempC] - the human core temp is 0 for inert.
*/

params [
    ["_tAir", 15, [0]],
    ["_wind", 0, [0]],
    ["_solar", 0, [0]],
    ["_exposure", 1, [0]],
    ["_mCore", 50, [0]],
    ["_mSkin", 20, [0]],
    ["_area", 1.8, [0]],
    ["_lChar", 0.15, [0]],
    ["_tCore0", 36.8, [0]],
    ["_tSkin0", 33.7, [0]],
    ["_qGen", 0, [0]],
    ["_orientation", "vertical", [""]],
    ["_rh", 0.5, [0]],
    ["_mrtC", 15, [0]],
    ["_isHuman", false, [true]],
    ["_evapOn", true, [true]],
    ["_dt", 5, [0]],
    ["_waterSpeed", 0, [0]],
    ["_tWater", -273, [0]],
    ["_rain", 0, [0]],
    ["_skinPerfusion", 1, [0]],
    ["_clo", 0, [0]],
    ["_cond", 1.0, [0]],
    ["_skinEps", 0.9, [0]],
    ["_skinAlpha", 0.5, [0]]
];

// ─── Saturation vapour pressure (Bolton 1980) ──────────────────────────────
// e_s(T) = 611.2 * exp(17.67*T/(T+243.5)) Pa, valid -35..+35 C, error
// 0.4%.  Exact closed-form derivative:
// de_s/dT = e_s * 4302.645/(T+243.5)^2.
private _psat = {
    params ["_t"];
    611.2 * exp (17.67 * _t / (_t + 243.5))
};

// ─── Convection coefficient ────────────────────────────────────────────────
// WATER (issue #193): an immersed surface exchanges with WATER, not air.
private _immersed = _tWater > -100;
private _h = 0;
if (_immersed) then {
    private _shivering = _isHuman && (_tSkin0 < 33.7) && (_tCore0 < 36.8);
    if (_waterSpeed > 0) then {
        _h = if (_shivering) then { 497.1 * (_waterSpeed ^ 0.65) } else { 272.9 * (_waterSpeed ^ 0.5) };
    } else {
        _h = [43.0, 54.0] select _shivering;
    };
} else {
    if (_isHuman) then {
        _h = (3.0) max (8.6 * ((_wind max 0.1) ^ 0.53));
    } else {
        private _hF = 5.7 + 3.8 * (_wind max 0);
        private _dT = _tSkin0 - _tAir;
        private _hN = 0;
        if (_dT > 0) then {
            private _nu = 15.89e-6;
            private _pr = 0.707;
            private _kAir = 0.02624;
            private _beta = 1 / 300;
            private _gr = 9.81 * _beta * (_dT max 0) * (_lChar ^ 3) / (_nu ^ 2);
            private _ra = _gr * _pr;
            private _nuC = 0;
            if (_ra < 1000) then {
                _nuC = 0;
            } else {
                if (_orientation == "vertical") then {
                    private _den = (1 + (0.492 / _pr) ^ (9 / 16)) ^ (8 / 27);
                    _nuC = (0.825 + 0.387 * (_ra ^ (1 / 6)) / _den) ^ 2;
                } else {
                    if (_orientation == "up") then {
                        _nuC = if (_ra < 1e7) then { 0.54 * (_ra ^ 0.25) } else { 0.15 * (_ra ^ (1 / 3)) };
                    } else {
                        _nuC = 0.27 * (_ra ^ 0.25);
                    };
                };
            };
            _hN = _nuC * _kAir / (_lChar max 0.05);
        };
        _h = (_hF ^ 3 + _hN ^ 3) ^ (1 / 3);
    };
};

// ─── Coupling conductance (W/K) ────────────────────────────────────────────
// Human: blood-flow coupling updates INSIDE the iterate (Gagge sigmoid).
// Inert: the driver passes the constant Fourier conductance.
private _kCoupling = if (_isHuman) then { 0 } else { _cond };
private _condConst = _cond;

// ─── Radiative field (ISO 7726) ───────────────────────────────────────────
// _mrtC arrives already combined by the caller (fnc_calculateMRT); the solver
// must NOT re-derive a second MRT.
private _tAirK = _tAir + 273.15;
private _mrtK = _mrtC + 273.15;
private _exchK = if (_immersed) then { _tWater + 273.15 } else { _tAirK };
private _exchMrtK = if (_immersed) then { _tWater + 273.15 } else { _mrtK };
private _sigma = 5.670374419e-8;
private _fRadArea = [1, 0.73] select _isHuman;
private _qSolar = _skinAlpha * (_solar max 0) * (_exposure max 0 min 1);

// Clothing resistances (Gagge 1986 / ASHRAE 55).
private _rClo = 0.155 * _clo;
private _fACl = 1 + 0.15 * _clo;
private _rEcl = if (_clo > 0) then { _rClo / (16.5 * 0.45) } else { 0 };
private _hE = 1 / (1 / (16.5 * _fACl * (_h max 1e-6)) + _rEcl);
private _pAK = (_tAir call _psat) * _rh / 1000;  // kPa

// ─── Joint fixed point: analytic core + Newton skin ────────────────────────
// Analytic core solution (linear residual): solve the core directly and
// substitute.  Iterating the coupled pair with damped Newton oscillates.
private _tCr = _tCore0;
private _tSk = _tSkin0;
private _w = 0;
private _fCl = 1;
private _alphaC = 0.1;
private _tBody = 0;
for "_i" from 1 to 12 do {
    if (_isHuman) then {
        private _warmC = (_tCr - 36.8) max 0;
        private _cSig = (33.7 - _tSk) max 0;
        private _mBl = (6.3 + 200 * _warmC) / (1 + 0.5 * _cSig);
        _mBl = (_mBl min 90) max 0.5;
        _mBl = _mBl * ((_skinPerfusion max 0) min 1);
        _alphaC = 0.0417737 + 0.7451833 / (_mBl + 0.585417);
        _kCoupling = (5.28 + 4186 * _mBl / 3600) * _area;
    } else {
        _kCoupling = _condConst;
    };
    private _pA = (_tAir call _psat) * _rh / 133.322;
    private _qResp = 0;
    if (_isHuman) then {
        private _mRate = if (_area > 0) then { _qGen / _area } else { 0 };
        _qResp = 0.0014 * _mRate * (34 - _tAir) + 0.0023 * _mRate * (44 - _pA);
    };
    private _qShiv = 0;
    if (_isHuman) then {
        private _cSig2 = (33.7 - _tSk) max 0;
        private _cCoreSig = (36.8 - _tCore0) max 0;
        _qShiv = 19.4 * _cSig2 * _cCoreSig;
    };
    _tCr = _tSk + (_qGen + _qShiv * _area - _qResp * _area) / (_kCoupling + 1e-6);
    private _tsAbs = _tSk + 273.15;
    private _hR = 4 * _fRadArea * _skinEps * _sigma * ((((_tsAbs + _exchMrtK) * 0.5) ^ 3));
    _fCl = 1 / (1 + _rClo * _fACl * (_h + _hR));
    private _conv = _h * (_tsAbs - _exchK) * _fCl;
    private _rad = _fRadArea * _skinEps * _sigma * ((_tsAbs ^ 4) - (_exchMrtK ^ 4)) * _fCl;
    _w = 0;
    if (_isHuman && _evapOn) then {
        private _tBodyNow = 0.1 * _tSk + 0.9 * _tCr;
        _tBody = _tBodyNow;
        private _mRsw = 170 * ((_tBodyNow - 36.49) max 0) * exp (((_tSk - 33.7) max 0) / 10.7);
        private _eRsw = 0.68 * _mRsw;
        private _pSkK = (_tSk call _psat) / 1000;    // kPa
        private _eMax = ((_pSkK - _pAK) max 0) * _hE;
        _w = if (_eMax > 0) then { 0.06 + 0.94 * ((_eRsw / _eMax) min 1) } else { 0.06 };
        _w = _w min 1;
    };
    if (_rain > 0) then {
        _w = (_w max ((_rain / 0.3) min 1)) min 1;
    };
    private _pSkK = (_tSk call _psat) / 1000;  // kPa
    private _evap = _w * _hE * ((_pSkK - _pAK) max 0);
    private _rSk = _qSolar + _kCoupling * (_tCr - _tSk) - _conv - _rad - _evap;
    private _den = _fCl * (_h + 4 * _fRadArea * _skinEps * _sigma * (_tsAbs ^ 3)) + _w * _hE * ((_tSk call _psat) * 4302.645 / ((_tSk + 243.5) ^ 2)) / 1000 + 1e-6;
    _tSk = _tSk + _rSk / _den;
    _tSk = (_tSk max (_tAir - 60)) min (_tAir + 500);
};
private _tCoreEq = _tCr;
private _tSkinEq = _tSk;

// ─── Two-node transient: two capacities, two time constants ────────────────
private _mBody = _mCore + _mSkin;
private _cSkin = 0.97 * _alphaC * _mBody * 1000;   // J/K
private _cCore = 0.97 * (1 - _alphaC) * _mBody * 1000;
private _tauSk = _cSkin / ((_h * _area * _fCl) max 1e-6 + _kCoupling);
private _tauCr = _cCore / (_kCoupling max 1e-6);
_tauSk = (_tauSk max 30) min 3600;
_tauCr = (_tauCr max 30) min 3600;
if (_w > 0.06) then { _tauSk = _tauSk * 1.5; };
private _tSkinNew = _tSkin0 + (_tSkinEq - _tSkin0) * (1 - exp (-_dt / _tauSk));
private _tCoreNew = _tCore0 + (_tCoreEq - _tCore0) * (1 - exp (-_dt / _tauCr));

[_tCoreNew, _tSkinNew, _tBody]
