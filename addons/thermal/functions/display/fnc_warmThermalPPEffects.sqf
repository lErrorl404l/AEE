#include "..\..\script_component.hpp"

/*
Build the thermal post-process chains off the entry path (client only).

The first thermal entry used to be expensive for an engine reason, not a
script reason.  fnc_applyThermalVision created the eight effects and
committed them from a DISABLED state; the engine defers the build of an
enabled chain to the next commit, so the 907 ms build landed on the tick
after entry (measured in the operator RPT 2026-10-08_17-51-36, the worst
tick: applyThermalVision 907 ms).

This function pays that build once, on an idle client tick, before the
operator ever enters thermal.  It creates the effects, enables each one
with a VISUALLY NEUTRAL parameter set (every adjust is a no-op), and
commits, so the engine builds all eight chains now.  It then schedules a
disable of all eight on the next tick, so the neutral frame is gone and
the live entry path owns the effects again.

The entry path itself never creates; it adjusts live handles.  The
rendered thermal image is unchanged: the neutral parameters render as the
identity, and the effects are disabled again before a scene is drawn.

Arguments: none.

Return Value:
  BOOL - true when the warm ran, false on a dedicated server or while a
         thermal host is already active.

Reference: docs/wiki/research/engine-thermal-mechanisms.md (priority
ladder and effect parameters).
*/

// Client only: a dedicated server has no post-process chain.
if (!hasInterface) exitWith { false };

// If the thermal display already owns the view, the live pass owns the
// handles; warming now would fight it.  Skip.
if ([call CBA_fnc_currentUnit] call FUNC(isThermalHostActive)) exitWith { false };

[] call FUNC(createThermalPPEffects);

// The neutral parameter for each effect.  Every value is the no-op form the
// live path already uses when an effect must be neutralised:
//   ChromAberration [0,0,false]  - no channel separation
//   RadialBlur      [0,0,0,0]    - no vignette
//   DynamicBlur     [0]          - no blur
//   FilmGrain       [0,0,0,0,0,0]- no grain
//   ColorCorrections the engine Default identity
//                   (CfgPostProcessTemplates >> Default >> colorCorrections)
//   ColorInversion  [0,0,0]      - no inversion
//   WetDistortion   wetness 0    - zero lens blur, the rest are fixed coeffs
//   Resolution      [-1]         - engine normal (disabled)
private _wetNeutral = [0] call FUNC(thermalWetDistortionParams);
private _neutral = [
    [QGVAR(ppHandle_Thermal_Chroma),        ["ChromAberration",  [0, 0, false]]],
    [QGVAR(ppHandle_Thermal_Vignette),      ["RadialBlur",       [0, 0, 0, 0]]],
    [QGVAR(ppHandle_Thermal_Blur),          ["DynamicBlur",      [0]]],
    [QGVAR(ppHandle_Thermal_Grain),         ["FilmGrain",        [0, 0, 0, 0, 0, 0]]],
    [QGVAR(ppHandle_Thermal_CC),            ["ColorCorrections", [1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0], [-1,-1,0,0,0,0,0]]]],
    [QGVAR(ppHandle_Thermal_Inversion),     ["ColorInversion",   [0, 0, 0]]],
    [QGVAR(ppHandle_Thermal_WetDistortion), ["WetDistortion",    _wetNeutral]],
    [QGVAR(ppHandle_Thermal_Resolution),    ["Resolution",       [-1]]]
];

{
    _x params ["_store", "_spec"];
    _spec params ["_name", "_params"];
    private _h = missionNamespace getVariable [_store, -1];
    if (_h >= 0) then {
        // Enable BEFORE the commit: the engine only builds an enabled chain
        // on a commit, which is exactly the cost this function is paying.
        _h ppEffectAdjust _params;
        _h ppEffectEnable true;
        _h ppEffectCommit 0;
    };
} forEach _neutral;

// The neutral frame is a one-tick build.  Disable every handle on the next
// tick so the operator never sees it, and the live entry path re-enables
// and adjusts when thermal is entered.
[{
    {
        private _h = missionNamespace getVariable [_x, -1];
        if (_h >= 0) then { _h ppEffectEnable false; };
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
}, [], 0.2] call CBA_fnc_waitAndExecute;

true
