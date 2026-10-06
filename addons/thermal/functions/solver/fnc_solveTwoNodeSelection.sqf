#include "..\..\script_component.hpp"
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
             W_sig = max(0, T_cr - 36.8)  CORE vasodilation signal
             C_sig = max(0, 33.7 - T_sk)   skin vasoconstriction signal
             clipped [0.5, 90] L/(h.m2) (Gagge, Fobelets & Berglund 1986)
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
    [W/m2, p_a in torr] with M the ACTUAL metabolic rate, so movement and
    the perfusion collapse reach ventilation.

  Convection (human): h_c = max(3.0 natural, 8.6*v^0.53 forced)
    per Gagge 1986 - NOT the McAdams inert-surface form (5.7+3.8w
    over-cools human skin: 6.08 vs 3.0 at still air, pushing the
    model into false vasoconstriction).
  Convection (inert): combined_h = (h_forced^3 + h_natural^3)^(1/3)
    Churchill-Usagi n=3 aiding; natural from Incropera Table 9.3
    (vertical Churchill-Chu, horizontal-up 0.54 Ra^1/4, horizontal-
    down 0.27 Ra^1/4).

  Evaporative (endothermic path): q_evap = w * h_e * (p_sk - p_a)
    h_e = 1/(r_ea + r_ecl), r_ea = 1/(LR*f_a_cl*h_c), r_ecl = r_clo/(LR*i_cl)
    (Gagge 1986 / ASHRAE 55; LR = 16.5 K/kPa, i_cl = 0.45 clothed)
    p_sk  = saturation pressure at skin temp (Bolton 1980)
    p_a   = ambient vapour pressure (rh * p_sat(T_air))
    w     = skin wettedness (Gagge evaporative terms)

  Clothing (Gagge 1986 / ASHRAE 55): the nude dry losses are attenuated by
    F_cl = r_a/(r_a + r_clo), r_a = 1/(f_a_cl*h_t), r_clo = 0.155*clo,
    f_a_cl = 1 + 0.15*clo.  A winter parka and a t-shirt no longer read alike.

  Radiation: q_rad = f_eff * eps * sigma * (T_sk^4 - MRT^4) vs the mean
    radiant temperature (ISO 7726), NOT air temp.  f_eff = A_eff/A_DuBois
    = 0.73 for a standing body (ASHRAE 55).

  Water immersion (issue #193): an immersed surface exchanges with
    WATER, not air.  Boutelier, Bougues & Timbal 1977 (partitional
    calorimetry, 17 nude subjects): still water hc = 43 W/m2K
    thermoneutral / 54 cold+shivering; stirred water
    hc = 272.9*v^0.5 neutral / 497.1*v^0.65 cold.  The 1977 values are
    cited but were NOT independently verified by the issue #189 audit and
    stand as the best available measured set.  The flat-plate correlations
    over-predict (body shape factor).  Immersion is signalled by a real
    water temperature (dry sentinel below -100 C); _waterSpeed is the true
    current (0 = still water).  The exchange target is the WATER temp.
  Rain wettedness (issue #193): rain is EXTERNAL water, not regulated
    sweat.  A rain-impacted surface is driven toward full wet
    (wettedness = rain/0.3 capped 1) regardless of the sweat rate,
    saturating the evaporative path.

  Transient: TWO capacities C_sk = 0.97*alpha*m and C_cr = 0.97*(1-alpha)*m
    (Gagge 1986) with the dynamic alpha = 0.0417737 + 0.7451833/(m_bl +
    0.585417), giving separate skin and core time constants and the
    core/skin phase lag.  Each node takes an exact exponential step to the
    joint equilibrium.  Skin tau lengthened x1.5 when the evaporative path
    is active (endothermic removal).

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
  17: mean radiant temperature (NUMBER, C) - the single radiative field
      from fnc_calculateMRT, NOT a ground temperature
  18: is human (BOOL) - use Gagge physiology
  19: conduction length (NUMBER, m) - block wall thickness
  20: evaporative path on (BOOL)
  21: time step (NUMBER, s)
  22: water speed (NUMBER, m/s) - true current; 0 = still water
  23: water temperature (NUMBER, C) - the exchange target when
      immersed; below -100 = no water
  24: rain rate (NUMBER, 0..1) - external wettedness driver
  25: skin perfusion index (NUMBER, 0..1) - shock vasoconstriction,
      computed by aee_physiology_fnc_calculateOxygenDelivery (issue #196)
  26: clothing insulation (NUMBER, clo) - 0 = nude (no clothing term)
  27: solar absorptance (NUMBER, 0..1) - -1 = derive from skin material

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
    ["_mrtC", 15, [0]],
    ["_isHuman", false, [true]],
    ["_lCond", 0.05, [0]],
    ["_evapOn", true, [true]],
    ["_dt", 5, [0]],
    ["_waterSpeed", 0, [0]],
    ["_tWater", -273, [0]],
    ["_rain", 0, [0]],
    ["_skinPerfusion", 1, [0]],
    ["_clo", 0, [0]],
    ["_solarAlpha", 0, [0]]
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
// The 1977 measured coefficients are cited but were NOT independently
// verified by the audit.  Immersion = a real water temperature; the dry
// sentinel is below -100 C.  _waterSpeed is the true current (0 = still).
private _immersed = _tWater > -100;
private _h = 0;
if (_immersed) then {
    // Shivering gate = the Gagge combined skin-cold AND core-cold signal.
    private _shivering = _isHuman && (_tSkin0 < 33.7) && (_tCore0 < 36.8);
    if (_waterSpeed > 0) then {
        _h = if (_shivering) then { 497.1 * (_waterSpeed ^ 0.65) } else { 272.9 * (_waterSpeed ^ 0.5) };
    } else {
        _h = [43.0, 54.0] select _shivering;
    };
} else {
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

// ─── Radiative field (ISO 7726) ───────────────────────────────────────────
// _mrtC arrives already combined by fnc_calculateMRT over emissive powers
// (F_g*Tg^4 + F_sky*Tsky^4 + sum F_obj*T_obj^4) with the per-selection view
// factors.  The solver must NOT re-derive a second MRT: the old code treated
// the passed MRT as a ground temperature and blended it 50/50 against a
// fresh sky, counting the sky twice (audit: ~1.5 C against ~6.4 C on the
// clear-night case).  The ground view factor now reaches the sink through
// the caller's MRT, not through a hardcoded 0.5.
private _tAirK = _tAir + 273.15;
private _mrtK = _mrtC + 273.15;
// Immersion exchange target (issue #193): an immersed surface exchanges
// against the WATER temperature directly, not air or the air-side MRT.
private _exchK = if (_immersed) then { _tWater + 273.15 } else { _tAirK };
private _exchMrtK = if (_immersed) then { _tWater + 273.15 } else { _mrtK };
private _sigma = 5.670374419e-8;
private _skinEps = (_skinClass call FUNC(getMaterialThermal)) select 0;
// Solar absorptance: the caller may pass the worn garment's per-selection
// value from fnc_getSolarAbsorptance (-1 derives it from the material).
private _skinAlpha = if (_solarAlpha > 0) then { _solarAlpha } else { (_skinClass call FUNC(getMaterialThermal)) select 1 };
// Projected-area factor A_eff/A_DuBois = 0.73 for a standing body (ASHRAE
// 55; Gagge).  A body does not radiate over its full DuBois area, so the raw
// DuBois area over-predicts radiant exchange by about 37 percent.  Inert
// surfaces radiate over their own area, so the factor is 1.
private _fRadArea = [1, 0.73] select _isHuman;
private _qSolar = _skinAlpha * (_solar max 0) * (_exposure max 0 min 1);

// Clothing resistances (Gagge 1986 / ASHRAE 55).
private _rClo = 0.155 * _clo;
private _fACl = 1 + 0.15 * _clo;
private _rEcl = if (_clo > 0) then { _rClo / (16.5 * 0.45) } else { 0 };
// Series vapour conductance: air layer r_ea = 1/(LR*f_a_cl*h_c) plus the
// clothing layer r_ecl.  LR = 16.5 K/kPa (Lewis relation).
private _hE = 1 / (1 / (16.5 * _fACl * (_h max 1e-6)) + _rEcl);
private _pAK = (_tAir call _psat) * _rh / 1000;  // kPa

// ─── Joint fixed point: analytic core + Newton skin ────────────────────────
// The core residual is LINEAR in T_cr, so solve it directly and
// substitute - iterating the coupled pair with damped Newton oscillates
// (traced: core 36.8 -> 49 -> 41 -> 35 -> 48 -> 39 -> 87 C).
private _tCr = _tCore0;
private _tSk = _tSkin0;
private _w = 0;
private _fCl = 1;
private _alphaC = 0.1;
for "_i" from 1 to 12 do {
    if (_isHuman) then {
        // Gagge, Fobelets & Berglund 1986: dilation driven by CORE warm,
        // constriction by SKIN cold, clipped [0.5, 90] L/(h.m2).
        private _warmC = (_tCr - 36.8) max 0;
        private _cSig = (33.7 - _tSk) max 0;
        private _mBl = (6.3 + 200 * _warmC) / (1 + 0.5 * _cSig);
        _mBl = (_mBl min 90) max 0.5;
        // Skin vasoconstriction is the volume/baroreflex axis and arrives
        // already computed by calculateOxygenDelivery (ATLS class III).
        // The solver carries no blood-loss threshold of its own.
        _mBl = _mBl * ((_skinPerfusion max 0) min 1);
        // Dynamic skin mass fraction (Gagge 1986).
        _alphaC = 0.0417737 + 0.7451833 / (_mBl + 0.585417);
        _kCoupling = (5.28 + 4186 * _mBl / 3600) * _area;
    } else {
        _kCoupling = _cond;
    };
    // Respiratory loss (Gagge 1986), p_a in torr.
    private _pA = (_tAir call _psat) * _rh / 133.322;
    // Respiratory loss is HUMAN physiology and is driven by the ACTUAL
    // metabolic rate (_qGen/area), not a fixed resting 58.2 W/m2.
    private _qResp = 0;
    if (_isHuman) then {
        private _mRate = if (_area > 0) then { _qGen / _area } else { 0 };
        _qResp = 0.0014 * _mRate * (34 - _tAir) + 0.0023 * _mRate * (44 - _pA);
    };
    // Shivering (Gagge): 19.4 * C_sig * C_core_sig, from the PERSISTENT
    // core (t_core0) - never the iterating equilibrium (feedback
    // explosion traced to 1363 C).  HUMAN ONLY: a cold parked vehicle
    // at midnight was receiving q_shiv ~6400 W/m2 and climbed chaotically
    // to 36-40 C (the in-game 'everything white at midnight' report).
    private _qShiv = 0;
    if (_isHuman) then {
        private _cSig2 = (33.7 - _tSk) max 0;
        private _cCoreSig = (36.8 - _tCore0) max 0;
        _qShiv = 19.4 * _cSig2 * _cCoreSig;
    };
    // Analytic core solution (linear residual).
    _tCr = _tSk + (_qGen + _qShiv * _area - _qResp * _area) / (_kCoupling + 1e-6);
    // Skin residual.  The dry losses pass through the clothing (Gagge 1986 /
    // ASHRAE 55): F_cl = r_a/(r_a + r_clo) with r_a = 1/(f_a_cl*h_t), h_t
    // the convective plus linearised radiative coefficient.
    private _tsAbs = _tSk + 273.15;
    private _hR = 4 * _fRadArea * _skinEps * _sigma * ((((_tsAbs + _exchMrtK) * 0.5) ^ 3));
    _fCl = 1 / (1 + _rClo * _fACl * (_h + _hR));
    private _conv = _h * (_tsAbs - _exchK) * _fCl;
    private _rad = _fRadArea * _skinEps * _sigma * ((_tsAbs ^ 4) - (_exchMrtK ^ 4)) * _fCl;
    // Evaporative (endothermic) path: wettedness x Lewis x vapour deficit.
    _w = 0;
    if (_isHuman && _evapOn) then {
        // Gagge wettedness: 0.06 insensible floor + regulatory sweat.
        // E_rsw = 0.68 * m_rsw; m_rsw = 170*max(0,Tb-36.49)*exp(max(0,Tsk-33.7)/10.7)
        // E_max = (p_sk - p_a)/(r_ea + r_ecl), w = 0.06 + 0.94*(E_rsw/E_max)
        private _tBody = 0.1 * _tSk + 0.9 * _tCr;
        // Published for the cross-module body-temperature invariant INV-4.
        // Grade: derived.  The formula is the Gagge 1986 body-temperature
        // weighting above (0.1 skin + 0.9 core); this line only publishes
        // the value the solver already computed.  Human selection only.
        missionNamespace setVariable ["aee_thermal_humanCoreTempC", _tBody];
        private _mRsw = 170 * ((_tBody - 36.49) max 0) * exp (((_tSk - 33.7) max 0) / 10.7);
        private _eRsw = 0.68 * _mRsw;
        private _pSkK = (_tSk call _psat) / 1000;    // kPa
        private _eMax = ((_pSkK - _pAK) max 0) * _hE;
        _w = if (_eMax > 0) then { 0.06 + 0.94 * ((_eRsw / _eMax) min 1) } else { 0.06 };
        _w = _w min 1;
    };
    // Rain-forced wettedness (issue #193): rain is EXTERNAL water, not
    // regulated sweat.  A rain-impacted surface is driven toward full
    // wet regardless of the sweat rate; saturates at high rain rates.
    if (_rain > 0) then {
        _w = (_w max ((_rain / 0.3) min 1)) min 1;
    };
    private _pSkK = (_tSk call _psat) / 1000;  // kPa
    private _evap = _w * _hE * ((_pSkK - _pAK) max 0);
    private _rSk = _qSolar + _kCoupling * (_tCr - _tSk) - _conv - _rad - _evap;
    // Newton skin step with the exact evaporative derivative.
    private _den = _fCl * (_h + 4 * _fRadArea * _skinEps * _sigma * (_tsAbs ^ 3)) + _w * _hE * ((_tSk call _psat) * 4302.645 / ((_tSk + 243.5) ^ 2)) / 1000 + 1e-6;
    _tSk = _tSk + _rSk / _den;
    _tSk = (_tSk max (_tAir - 60)) min (_tAir + 500);
};
private _tCoreEq = _tCr;
private _tSkinEq = _tSk;

// ─── Two-node transient: two capacities, two time constants ────────────────
// Gagge 1986 capacities C_sk = 0.97*alpha*m and C_cr = 0.97*(1-alpha)*m with
// the dynamic alpha, so core and skin relax on separate clocks (the
// core/skin phase lag).  The one-capacity model this replaces had no core
// state and relaxed both nodes on the skin clock.
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

[_tCoreNew, _tSkinNew]
