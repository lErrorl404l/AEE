#include "..\script_component.hpp"

/*
Creates the persistent post-process effect handles used by the FX layer.

Arma 2.22 rejects the string-LHS form ("ChromAberration" ppEffectAdjust ...)
with "Type Number, expected Number" — the LHS must be the numeric handle
returned by ppEffectCreate.  This function creates four effects once
at init and stores the handles in missionNamespace:

  QGVAR(ppHandle_ChromAberration)  - atmospheric seeing, heat shimmer
  QGVAR(ppHandle_DynamicBlur)      - dew, rain, glare, severe weather
  QGVAR(ppHandle_ColorCorrections) - severe weather, snow blindness
  QGVAR(ppHandle_FilmGrain)        - normal-vision night grain

The four NVG-specific handles (NVG_CC, NVG_Bloom, NVG_Vignette,
NVG_Grain) are NOT created here.  fnc_applyNVGTubeModel recreates
them every tick via ppEffectCreate.  ACE3 pattern: Arma 3 kills
ppEffects on alt-tab, resize, AT sights.  Recreating each tick
prevents stale dead handles.

LightShafts is NOT created here: it is an advanced post-process effect
(BIS wiki) that ppEffectCreate cannot create (returns -1); fnc_applySolarGlareFX
uses the string-LHS form for it directly.

Called once from XEH_preInit.

Sets: the four ppHandle_* variables.  Returns: nothing.
*/

private _effects = [
    ["ChromAberration", 3000],
    ["DynamicBlur", 4000],
    ["ColorCorrections", 5000],
    ["FilmGrain", 2000]
    // LightShafts is deliberately absent: it is an ADVANCED effect (BIS
    // wiki) that cannot be created by ppEffectCreate (returns -1) and is
    // adjusted via the string-LHS form in fnc_applySolarGlareFX.
];

// ppEffect handles persist across mission loads: preInit runs on every
// mission, but a second ppEffectCreate at the same priority would bump
// to a new priority and orphan the previous handle, which the engine then
// kills at the mission boundary — leaving stale positive numbers in
// missionNamespace that fail every call with "Invalid post effect handle".
// If the stored handle is already valid, keep it and do not recreate.
{
    _x params ["_name", "_priority"];
    private _varName = format [QGVAR(ppHandle_%1), _name];
    private _existing = missionNamespace getVariable [_varName, -1];
    if (_existing >= 0) exitWith {};
    private _handle = ppEffectCreate [_name, _priority];
    // ppEffectCreate returns -1 when the priority is taken; bump until it succeeds
    private _guard = 0;
    while {_handle < 0 && _guard < 100} do {
        _priority = _priority + 1;
        _handle = ppEffectCreate [_name, _priority];
        _guard = _guard + 1;
    };
    missionNamespace setVariable [_varName, _handle];
    diag_log text format ["[AEE] ppEffect handle %1 = %2", _varName, _handle];
} forEach _effects;
