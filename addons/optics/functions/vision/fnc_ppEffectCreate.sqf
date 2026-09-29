#include "..\..\script_component.hpp"

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

// Creation, priority bumping, idempotence, the priority-collision log and the
// ownership record all live in the shared registry now (core
// fnc_createPPEffect).  AEE_MODULE_PRE_INIT already refuses a repeat init, and the
// registry refuses a second create for the same scope and key, so the stacking
// that produced handles 17,18,19,20 then 29,30,31,32 in one session cannot
// recur.  fnc_destroyBasePostProcess releases the whole "optics" scope.
//
// The legacy variable name is passed so the four existing readers in
// fnc_managePostProcess and fnc_applyNightGrain keep working untouched.
{
    _x params ["_name", "_priority"];
    [
        "optics",
        _name,
        _name,
        _priority,
        format [QGVAR(ppHandle_%1), _name]
    ] call EFUNC(core,createPPEffect);
} forEach _effects;
