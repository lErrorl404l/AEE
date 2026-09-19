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
*/
params ["_obj", "_selection", ["_mode", ""]];

if (isNull _obj || {!hasInterface}) exitWith { 0 };

// ─── EXIT: restore every saved texture ────────────────────────────────────
if (_mode == "EXIT") then {
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
};

// ─── Solve and apply ──────────────────────────────────────────────────────
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

    private _tNew = [
        _obj, _sel, _tAir, _wind, _solar, _exposure, 0, _tCurrent
    ] call FUNC(solveSelectionTemperature);

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

0
