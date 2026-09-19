#include "..\script_component.hpp"
/*
Two-node core/skin temperature solve (issue #191).

The #124 substrate solves the SURFACE node only - a single lumped-
capacity skin with a flat q_internal flux.  Real objects have an
interior whose heat drives the skin: a running engine's 90 C coolant
heats the block, a human's 37 C core perfuses the skin, a building's
thermal mass modulates the envelope.  This function is the two-node
extension: a CORE node coupled to the SKIN by a conductance, solved
jointly, with the Gagge thermoregulatory physiology for humans.

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
             W_sig = max(0, T_sk - 33.7)  vasodilation signal
             C_sig = max(0, 33.7 - T_sk)  vasoconstriction signal
             capped 14.4 (= 240 ml/min/m2 max vasodilation) and
             floored 0.5 (segment research)
  k_coupling (W/K), engine/building = k * A / L_cond (Fourier)
    L_cond = block wall thickness (conduction path), distinct from
             L_char (convection plate dimension) - the #124 audit
             found reusing L_char gives k*A/L = 30000 W/K flooding
             the skin (skin exceeded core, physically impossible)

  Shivering (Gagge 1986): q_shiv = 19.4 * C_sig * C_core_sig
    C_core_sig = max(0, 36.8 - T_cr)
    Computed from the PERSISTENT core (t_core0), never the iterating
    equilibrium - feeding it the solve value makes shivering positive
    feedback and the fixed point explodes (traced to 1363 C).

  Respiratory loss (Gagge 1986): 
    C_res = 0.0014*M*(34 - T_db), E_res = 0.0023*M*(44 - p_a)
    [W/m2, p_a in torr] - breathing carries heat before circulation.

  Convection (human): h_c = max(3.0 natural, 8.6*v^0.53 forced)
    per Gagge 1986 - NOT the McAdams inert-surface form (5.7+3.8w
    over-cools human skin: 6.08 vs 3.0 at still air, pushing the
    model into false vasoconstriction).
  Convection (inert): combined_h = (h_forced^3 + h_natural^3)^(1/3)
    Churchill-Usagi n=3 aiding; natural from Incropera Table 9.3
    (vertical Churchill-Chu, horizontal-up 0.54 Ra^1/4, horizontal-
    down 0.27 Ra^1/4).

  Evaporative (endothermic path): q_evap = w * h_e * (p_sk - p_a)
    h_e = LR * h_c (Lewis relation, LR = 16.5 K/kPa = 2.2 C/torr)
    p_sk  = saturation pressure at skin temp (Bolton 1980)
    p_a   = ambient vapour pressure (rh * p_sat(T_air))
    w     = skin wettedness (Gagge evaporative terms)

  Radiation: q_rad = eps * sigma * (T_sk^4 - MRT^4) vs the mean
    radiant temperature (ISO 7726), NOT air temp.

  Inertia (asymmetric transient): one exponential step toward the
    joint equilibrium.  Heating tau = m*cp/(h*A + k_coupling).
    Cooling tau lengthened x1.5 when the evaporative path is active
    (endothermic removal - a wet surface cools slower than a dry one
    because latent heat must be supplied).

Arguments:
  0: object (OBJECT)
  1: selection name (STRING) - "" whole-object fallback
  2: core material class (STRING, from getMaterialThermal registry)
  3: skin material class (STRING)
  4: ambient temp (NUMBER, C)
  5: wind (NUMBER, m/s)
  6: solar flux (NUMBER, W/m2)
  7: shading exposure (NUMBER, 0..1)
  8: core mass (NUMBER, kg)
  9: skin mass (NUMBER, kg)
  10: surface area (NUMBER, m2)
  11: characteristic length (NUMBER, m) - convection plate dimension
  12: current core temp (NUMBER, C)
  13: current skin temp (NUMBER, C)
  14: internal generation (NUMBER, W) - metabolism/combustion TOTAL,
      added to the area-scaled shivering/respiratory terms in the
      core balance (all W over the W/K coupling)
  15: orientation (STRING) - "vertical"/"up"/"down"
  16: relative humidity (NUMBER, 0..1)
  17: ground temp (NUMBER, C) - for the MRT
  18: is human (BOOL) - use Gagge physiology
  19: conduction length (NUMBER, m) - block wall thickness
  20: evaporative path on (BOOL)
  21: time step (NUMBER, s)

Return:
  [coreTempC, skinTempC]
*/

params [
    ["_obj", objNull, [objNull]],
    ["_selection", "", [""]],
    ["_coreClass", "metal", [""]],
    ["_skinClass", "metal", [""]],
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
    ["_tGround", 15, [0]],
    ["_isHuman", false, [true]],
    ["_lCond", 0.05, [0]],
    ["_evapOn", true, [true]],
    ["_dt", 5, [0]]
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
private _h = 0;
if (_isHuman) then {
    // Gagge 1986: h = max(3.0 natural, 8.6*v^0.53 forced)
    _h = (3.0) max (8.6 * ((_wind max 0.1) ^ 0.53));
} else {
    // Churchill-Usagi n=3 superposition of McAdams forced + Incropera
    // natural (Table 9.3).
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

// ─── Coupling conductance (W/K) ────────────────────────────────────────────
private _kCoupling = if (_isHuman) then {
    // Blood-flow coupling updates INSIDE the iterate (Gagge sigmoid).
    0
} else {
    // Fourier conduction: k*A/L_cond, with the lower of the two
    // conductivities (series path core -> skin).
    private _coreMat = _coreClass call FUNC(getMaterialThermal);
    private _skinMat = _skinClass call FUNC(getMaterialThermal);
    ((_coreMat select 4) min (_skinMat select 4)) * _area / (_lCond max 0.01)
};
private _cond = _kCoupling;  // inert path constant conductance

// ─── Radiation vs MRT (ISO 7726) ──────────────────────────────────────────
private _mrtK = (0.5 * ((_tGround + 273.15) ^ 4) + 0.5 * ((_tAir + 273.15) ^ 4)) ^ 0.25;
private _tAirK = _tAir + 273.15;
private _sigma = 5.670374419e-8;
private _skinEps = (_skinClass call FUNC(getMaterialThermal)) select 0;
private _skinAlpha = (_skinClass call FUNC(getMaterialThermal)) select 1;
private _qSolar = _skinAlpha * (_solar max 0) * (_exposure max 0 min 1);

// ─── Joint fixed point: analytic core + Newton skin ────────────────────────
// The core residual is LINEAR in T_cr, so solve it directly and
// substitute - iterating the coupled pair with damped Newton oscillates
// (traced: core 36.8 -> 49 -> 41 -> 35 -> 48 -> 39 -> 87 C).
private _tCr = _tCore0;
private _tSk = _tSkin0;
private _w = 0;
for "_i" from 1 to 12 do {
    if (_isHuman) then {
        // Blood flow (Gagge sigmoid), capped 14.4 L/(h.m2) = 240
        // ml/min/m2 max vasodilation (segment research).
        private _wSig = (_tSk - 33.7) max 0;
        private _cSig = (33.7 - _tSk) max 0;
        private _mBl = (6.3 + 200 * _wSig) / (1 + 0.5 * _cSig);
        _mBl = (_mBl min 14.4) max 0.5;
        _kCoupling = (5.28 + 4186 * _mBl / 3600) * _area;
    } else {
        _kCoupling = _cond;
    };
    // Respiratory loss (Gagge 1986), p_a in torr.
    private _pA = (_tAir call _psat) * _rh / 133.322;
    private _qResp = 0.0014 * 58.2 * (34 - _tAir) + 0.0023 * 58.2 * (44 - _pA);
    // Shivering (Gagge): 19.4 * C_sig * C_core_sig, from the PERSISTENT
    // core (t_core0) - never the iterating equilibrium (feedback
    // explosion traced to 1363 C).
    private _cSig2 = (33.7 - _tSk) max 0;
    private _cCoreSig = (36.8 - _tCore0) max 0;
    private _qShiv = 19.4 * _cSig2 * _cCoreSig;
    // Analytic core solution (linear residual).
    _tCr = _tSk + (_qGen + _qShiv * _area - _qResp * _area) / (_kCoupling + 1e-6);
    // Skin residual.
    private _tsAbs = _tSk + 273.15;
    private _conv = _h * (_tsAbs - _tAirK);
    private _rad = _skinEps * _sigma * ((_tsAbs ^ 4) - (_mrtK ^ 4));
    // Evaporative (endothermic) path: wettedness x Lewis x vapour deficit.
    _w = 0;
    if (_isHuman && _evapOn) then {
        // Gagge wettedness: 0.06 insensible floor + regulatory sweat.
        // E_rsw = 0.68 * m_rsw; m_rsw = 170*max(0,Tb-36.49)*exp(max(0,Tsk-33.7)/10.7)
        // E_max = (p_sk - p_a)/(r_ea), w = 0.06 + 0.94*(E_rsw/E_max)
        private _tBody = 0.1 * _tSk + 0.9 * _tCr;
        private _mRsw = 170 * ((_tBody - 36.49) max 0) * exp (((_tSk - 33.7) max 0) / 10.7);
        private _eRsw = 0.68 * _mRsw;
        private _pSkT = (_tSk call _psat) / 133.322;  // torr
        private _pAT = _pA;
        private _eMax = ((_pSkT - _pAT) max 0) / 0.68;  // r_ea nude ~0.68 torr m2/W
        _w = if (_eMax > 0) then { 0.06 + 0.94 * ((_eRsw / _eMax) min 1) } else { 0.06 };
        _w = _w min 1;
    };
    private _hE = 16.5 * _h;  // Lewis relation (K/kPa)
    private _pSkK = (_tSk call _psat) / 1000;  // kPa
    private _pAK = (_tAir call _psat) * _rh / 1000;  // kPa
    private _evap = _w * _hE * ((_pSkK - _pAK) max 0);
    private _rSk = _qSolar + _kCoupling * (_tCr - _tSk) - _conv - _rad - _evap;
    // Newton skin step with the exact evaporative derivative.
    private _den = _h + 4 * _skinEps * _sigma * (_tsAbs ^ 3) + _w * _hE * ((_tSk call _psat) * 4302.645 / ((_tSk + 243.5) ^ 2)) / 1000 + 1e-6;
    _tSk = _tSk + _rSk / _den;
    _tSk = (_tSk max (_tAir - 60)) min (_tAir + 500);
};
private _tCoreEq = _tCr;
private _tSkinEq = _tSk;

// ─── Asymmetric transient (one exponential step) ───────────────────────────
private _skinMat = _skinClass call FUNC(getMaterialThermal);
private _cpSkin = _skinMat select 3;
private _tau = _mSkin * _cpSkin / ((_h * _area) max 1e-6 + _kCoupling);
_tau = (_tau max 30) min 3600;
if (_w > 0.06) then { _tau = _tau * 1.5; };
private _kExp = 1 - exp (-_dt / _tau);
private _tSkinNew = _tSkin0 + (_tSkinEq - _tSkin0) * _kExp;
private _tCoreNew = _tCore0 + (_tCoreEq - _tCore0) * _kExp;

[_tCoreNew, _tSkinNew]
