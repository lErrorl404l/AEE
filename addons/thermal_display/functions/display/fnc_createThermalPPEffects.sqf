#include "..\..\script_component.hpp"

/*
Create the eight thermal post-process effects (idempotent).

The create block used to live on the per-entry path in
fnc_applyThermalVision.  Creating the effects there, and committing them
from a disabled state, made the engine build every enabled chain on the
NEXT tick: a measured 907 ms frame hitch on the first thermal entry.

This function is the single create choke point.  It runs once from the
post-init pre-warm (fnc_warmThermalPPEffects) and is the idempotent
fallback from the live entry path.  It creates the eight effects only when
a handle is missing.  The priority ladder is the proven A3TI/MKK per-type
band (docs/wiki/research/engine-thermal-mechanisms.md): each effect type
keeps its own band with a large gap, so no two AEE modules share a
priority.  A -1 handle (priority taken) bumps until it succeeds.

Arguments: none.

Return Value:
  BOOL - true when all eight handles are live (>= 0) after the call.

Side effects:
  Writes the eight GVAR(ppHandle_Thermal_*) missionNamespace variables and
  clears GVAR(ppLastParams) when it creates.
*/

// A dedicated server has no post-process chain, so ppEffectCreate is not a
// valid call there and returns nothing.  The two callers (the live entry path
// and the post-init warm) are both client-only, but a probe or a future caller
// can reach this function headless, so refuse cleanly.
if (!hasInterface) exitWith { false };

private _hVig   = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Vignette), -1];
private _hChroma = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Chroma), -1];
private _hCC    = missionNamespace getVariable [QGVAR(ppHandle_Thermal_CC), -1];
private _hGrain = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Grain), -1];
private _hBlur  = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Blur), -1];
private _hInv   = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Inversion), -1];
private _hWet   = missionNamespace getVariable [QGVAR(ppHandle_Thermal_WetDistortion), -1];
private _hReso  = missionNamespace getVariable [QGVAR(ppHandle_Thermal_Resolution), -1];

if (_hVig < 0 || _hChroma < 0 || _hCC < 0 || _hGrain < 0 || _hBlur < 0 || _hInv < 0 || _hWet < 0 || _hReso < 0) then {
    // A fresh effect must always receive its parameters, even when the engine
    // hands back a handle NUMBER it used earlier.  Clearing here is the one
    // choke point every new effect passes through, because each destroy path
    // resets its handle to -1 and the test above then recreates it.
    missionNamespace setVariable [QGVAR(ppLastParams), createHashMap];

    {
        private _h = missionNamespace getVariable [_x, -1];
        if (_h >= 0) then {
            ppEffectDestroy _h;
            missionNamespace setVariable [_x, -1];
            private _logMsg = format ["thermal recreate: destroyed %1 (was %2)", _x, _h];
            AEE_LOG_DEBUG(_logMsg);
        };
    } forEach [
        QGVAR(ppHandle_Thermal_Vignette),
        QGVAR(ppHandle_Thermal_Chroma),
        QGVAR(ppHandle_Thermal_CC),
        QGVAR(ppHandle_Thermal_Grain),
        QGVAR(ppHandle_Thermal_Blur),
        QGVAR(ppHandle_Thermal_Inversion),
        QGVAR(ppHandle_Thermal_WetDistortion),
        QGVAR(ppHandle_Thermal_Resolution)
    ];

    private _handles = [];
    // The loop variables are declared at FUNCTION scope, not inside the
    // forEach body: a `private` declared in a forEach body is not reliably
    // visible to a `while` nested in that body, and the engine then reads an
    // undefined `_handle` for every effect (this only surfaces headless,
    // where ppEffectCreate returns no handle and the bump loop is entered).
    // The core registry hoists for the same reason.  ppEffectCreate can also
    // return nil on a host without a post-process chain, so the candidate is
    // type-checked before it is used.
    private _handle = -1;
    private _guard = 0;
    private _candidate = -1;
    private _name = "";
    private _priority = 0;
    private _store = "";
    {
        _name = _x select 0;
        _priority = _x select 1;
        _store = _x select 2;
        _handle = -1;
        _guard = 0;
        while {_handle < 0 && _guard < 100} do {
            _candidate = ppEffectCreate [_name, _priority];
            if ((_candidate isEqualType 0) && _candidate >= 0) then {
                _handle = _candidate;
            } else {
                _priority = _priority + 1;
                _guard = _guard + 1;
            };
        };
        missionNamespace setVariable [_store, _handle];
        _handles pushBack _handle;
        private _logMsg = format ["created thermal %1 priority=%2 handle=%3", _name, _priority, _handle];
        AEE_LOG_DEBUG(_logMsg);
    } forEach [
        // ChromAberration: the A3TI WHOT branch applies it at
        // [0.001,0.001,true] BEFORE its ColorCorrections (workshop
        // 3725008325 fn_ppEffects.sqf case 0), so it sits below the thermal
        // CC here.  It is the lens colour fringing of the thermal objective,
        // the one WHOT effect this stack did not already carry.  Priority
        // 205 is the proven A3TI/MKK band for this effect type.
        ["ChromAberration",  205, QGVAR(ppHandle_Thermal_Chroma)],
        // RadialBlur: the vignette/edge falloff, the proven MKK value 1000.
        ["RadialBlur",      1000, QGVAR(ppHandle_Thermal_Vignette)],
        // DynamicBlur: the proven defocus band value 505.
        ["DynamicBlur",      505, QGVAR(ppHandle_Thermal_Blur)],
        // FilmGrain: the proven sensor-noise band.  The plan named 2005,
        // but the fusion stack already holds 2005, so this stack takes the
        // other proven value 2000 (the A3TI variant) and the two
        // thermal-owned stacks never share a priority.
        ["FilmGrain",       2000, QGVAR(ppHandle_Thermal_Grain)],
        // ColorCorrections: the proven grade band.  The plan named 2505,
        // but fusion holds 2505, so this stack takes the other proven value
        // 2500.
        ["ColorCorrections", 2500, QGVAR(ppHandle_Thermal_CC)],
        // ColorInversion: the proven BHOT mechanism (A3TI 2501, MKK 2510,
        // workshop 2041057379 / 3753145363).  Inverts the WHOLE rendered
        // frame - hot becomes black, cold becomes white - which the old
        // `_b = 1-_b` band flip never achieved for StageTI-baked objects.
        // Created unconditionally; enabled only when thermalPolarity == 1
        // (see the adjust section).  Priority 2510 is the proven BHOT band,
        // above the thermal CC (2500) so it inverts the graded image.
        ["ColorInversion", 2510, QGVAR(ppHandle_Thermal_Inversion)],
        // WetDistortion: rain on the objective lens (MKK thermal_improvement
        // workshop 3753145363 fnc_applyVisionEffects.sqf:158-166, priority
        // 305 there).  It sits at 305, below every other AEE thermal effect,
        // so the lens film distorts the frame before the grade.  Enabled
        // only when AEE's rain/fog makes the lens wet.
        ["WetDistortion",    305, QGVAR(ppHandle_Thermal_WetDistortion)],
        // Resolution: sensor pixelation (MKK fnc_applyVisionEffects.sqf:124,
        // priority 3000 there).  It sits at 3000, above the ColorInversion,
        // so the detector grid quantises the finished frame.  Enabled only
        // when the operator turns on thermalPixelation.  AEE does NOT drive
        // the engine-global setTIParameter MaxResolution (see
        // fnc_thermalResolutionParams).
        ["Resolution",      3000, QGVAR(ppHandle_Thermal_Resolution)]
    ];
    _handles params ["_hChroma", "_hVig", "_hBlur", "_hGrain", "_hCC", "_hInv", "_hWet", "_hReso"];
    private _logMsg = format ["thermal ppEffects created: chroma=%1 vig=%2 blur=%3 grain=%4 CC=%5 inv=%6 wet=%7 reso=%8", _hChroma, _hVig, _hBlur, _hGrain, _hCC, _hInv, _hWet, _hReso];
    AEE_LOG_INFO(_logMsg);
};

private _all =
    (missionNamespace getVariable [QGVAR(ppHandle_Thermal_Vignette), -1]) >= 0
    && {(missionNamespace getVariable [QGVAR(ppHandle_Thermal_Chroma), -1]) >= 0}
    && {(missionNamespace getVariable [QGVAR(ppHandle_Thermal_CC), -1]) >= 0}
    && {(missionNamespace getVariable [QGVAR(ppHandle_Thermal_Grain), -1]) >= 0}
    && {(missionNamespace getVariable [QGVAR(ppHandle_Thermal_Blur), -1]) >= 0}
    && {(missionNamespace getVariable [QGVAR(ppHandle_Thermal_Inversion), -1]) >= 0}
    && {(missionNamespace getVariable [QGVAR(ppHandle_Thermal_WetDistortion), -1]) >= 0}
    && {(missionNamespace getVariable [QGVAR(ppHandle_Thermal_Resolution), -1]) >= 0};

_all
