#include "..\script_component.hpp"
/*
Per-selection physics-driven thermal apply (issue #124).

Replaces the rvmat TI-stage swap (ti_cloth_cold/hot, the #123 bug
class) with a procedural per-selection thermal image.

Mechanism (verified against A3TI's fn_setObjects.sqf): each model
selection's texture channel is flattened to a procedural colour
string `#(rgb,8,8,3)color(b,b,b,1)` via setObjectTexture.  The engine
composites it exactly like a painted texture, but the colour comes
from physics, not a .paa/.rvmat.

FLIR mapping (real sensor physics):
  - the sensor reads RADIANCE, not temperature: radiance = eps*sigma*T^4.
    A low-emissivity surface (polished metal ~0.1) at 100 C radiates
    like a black body at ~56 C, so the sensor reports
      T_apparent = T * eps^(1/4)        [Stefan-Boltzmann, emissivity
                                          correction - the "cold shiny
                                          metal" effect FLIR manuals warn
                                          about]
  - white-hot palette: brightness b = clamp((T_apparent - T_lo) /
    (T_hi - T_lo), 0, 1), with the sensor gain window T_lo=-40 C,
    T_hi=+150 C (typical ground-target auto-gain span).  Black = cold,
    white = hot - the real white-hot mode.
  - the colour is greyscale (b,b,b) because white-hot carries no hue;
    colour variants (ironbow/rainbow) are a post-process tint, handled
    by the sensor pipeline, not per-object.

Multiplayer: setObjectTexture is LOCAL, correct here - each client
renders its own thermal pass from identical physics (the existing
object-temperature solver runs everywhere), so every client applies the
same texture and every player sees the same thermal image.

Cost: one setObjectTexture per thermal selection per throttle tick
(0.05 s in the existing thermal contrast pass), NOT per frame.  The
original textures are saved on first apply and restored on EXIT, same
pattern as fnc_applyClothingThermal.

Arguments:
  0: object (OBJECT)
  1: selection name (STRING) - "" for whole-object fallback
  2: mode (STRING, optional) - "EXIT" restores saved textures
  3: internal heat (NUMBER, optional, W/m2) - engine/exhaust/friction
     per selection, default 0 (solar + ambient only)
  4: ground view factor (NUMBER, optional, 0..1) - the MRT ground
     weight for the radiation term; a tyre sees ~0.7 ground, a roof
     ~0.3, a standing soldier 0.5
*/
params ["_obj", "_selection", ["_mode", ""], ["_qInternal", 0, [0]], ["_fGround", 0.5, [0]]];

if (_mode == "EXIT") then {
    // ─── EXIT: restore every saved texture ──────────────────────────────────
    // Runs BEFORE the object guard: the EXIT path is global (restores every
    // saved object), so callers may invoke it with a dummy object, e.g.
    // fnc_applyBuildingThermal's mode-off handler calls ["", "", "EXIT"].
    private _saved = missionNamespace getVariable [QGVAR(selThermalSaved), []];
    {
        _x params ["_o", "_oldTexs", "_selNames"];
        if (!isNull _o) then {
            private _selIdx = 0;
            {
                if (_selIdx < count _oldTexs && {(_oldTexs select _selIdx) isEqualType ""}) then {
                    _o setObjectTexture [_selIdx, _oldTexs select _selIdx];
                };
                _selIdx = _selIdx + 1;
            } forEach _selNames;
        };
    } forEach _saved;
    missionNamespace setVariable [QGVAR(selThermalSaved), []];
} else {
    if (isNull _obj || {!hasInterface}) exitWith { 0 };

    // ─── Solve and apply ──────────────────────────────────────────────────
    private _selNames = if (_selection == "") then { [] } else { [_selection] };
    if (_selNames isEqualTo []) then {
        _selNames = selectionNames _obj;
    };

    // Save originals once per object per pass (first apply).
    private _saved = missionNamespace getVariable [QGVAR(selThermalSaved), []];
    private _alreadySaved = _saved findIf { (_x select 0) == _obj };
    if (_alreadySaved < 0) then {
        private _oldTexs = getObjectTextures _obj;
        _saved pushBack [_obj, _oldTexs, _selNames];
        missionNamespace setVariable [QGVAR(selThermalSaved), _saved];
    };

    // Ambient + wind + solar from the core environment state.
    private _tAir = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
    private _wind = vectorMagnitude (missionNamespace getVariable [QEGVAR(core,currentWind), [0,0,0]]);
    private _solar = missionNamespace getVariable [QEGVAR(core,currentSolarFlux), 0];

    {
        private _sel = _x;
        private _idx = (selectionNames _obj) find _sel;
        if (_idx < 0) then { continue; };

        // Shade exposure: roof/upper selections get full sun, lower panels
        // less (self-shadow).  Refined by the object's existing shade ray.
        private _exposure = 1;
        if (_sel find "wheel" >= 0 || {_sel find "undercarriage" >= 0}) then {
            _exposure = 0.15;   // tyres/undercarriage: mostly self-shadowed
        };

        // Current per-selection temperature from the object solver state.
        private _stateKey = format ["%1|%2", str _obj, _sel];
        private _tCurrent = missionNamespace getVariable [QGVAR(selTemperature), createHashMap] getOrDefault [_stateKey, _tAir];

        // ─── Two-node path (issue #191) ─────────────────────────────────────
        // Core-bearing selections solve core+skin coupled (Gagge
        // two-node), NOT the single-node surface-only balance.  The
        // human path is wired now - the Gagge model is fully validated
        // against its published set points.  Engine and building-mass
        // two-node stay on the surface path until their fitted models
        // land: the engine needs a per-engine coolant-loop fit
        // (Bohac 1996 / Jarrier 2000 lumped-RC, no canonical constants),
        // and building mass needs the ISO 52016 envelope+mass topology.
        private _tNew = _tAir;
        if (_obj isKindOf "CAManBase") then {
            private _mrt = [getPosASL _obj, _fGround] call FUNC(calculateMRT);
            // 1 met = 58.2 W/m2 over DuBois 1.8258 m2 = 106.3 W TOTAL
            // (Gagge, native vanilla resting metabolism - no ACM
            // dependency).  qGen is TOTAL W, matching the W/K coupling
            // in the core balance.
            private _qMet = 58.2 * 1.8258;
            private _two = [
                _obj, _sel,
                "human", "human",       // core class, skin class
                _tAir, _wind, _solar, _exposure,
                0.9 * 70, 0.1 * 70,     // core/skin mass: 90/10 split of 70 kg
                1.8258,                 // DuBois area (m2)
                0.15,                   // convection plate dim (m)
                _tCurrent, _tCurrent,   // core/skin current temps
                _qMet,                  // qGen: resting metabolism (W)
                "vertical", 0.5, _mrt, true, 0.05, true, 5
            ] call FUNC(solveTwoNodeSelection);
            _tNew = _two select 1;      // skin temp - what FLIR sees
        } else {
            _tNew = [
                _obj, _sel, _tAir, _wind, _solar, _exposure, _qInternal, _tCurrent, _fGround
            ] call FUNC(solveSelectionTemperature);
        };

        // Persist for the next tick's inertia term.
        private _selMap = missionNamespace getVariable [QGVAR(selTemperature), createHashMap];
        _selMap set [_stateKey, _tNew];
        missionNamespace setVariable [QGVAR(selTemperature), _selMap];

        // FLIR white-hot: apparent temperature with emissivity correction.
        private _mat = ([_obj, _sel] call FUNC(getSelectionMaterials)) call FUNC(getMaterialThermal);
        private _eps = _mat select 0;
        private _tApparent = (_tNew + 273.15) * (_eps ^ 0.25) - 273.15;
        private _b = ((_tApparent + 40) / 190) max 0 min 1;   // -40..150 C window
        private _colour = format ["#(rgb,8,8,3)color(%1,%1,%1,1)", _b];

        _obj setObjectTexture [_idx, _colour];
    } forEach _selNames;
};

0
