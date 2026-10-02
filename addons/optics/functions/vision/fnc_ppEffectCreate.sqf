#include "..\..\script_component.hpp"

/*
Creates the persistent post-process effect handles used by the FX layer.

Arma 2.22 rejects the string-LHS form ("ChromAberration" ppEffectAdjust ...)
with "Type Number, expected Number" — the LHS must be the numeric handle
returned by ppEffectCreate.  This function creates three effects once
at init and stores the handles in missionNamespace:

  QGVAR(ppHandle_ChromAberration)  - atmospheric seeing, heat shimmer
  QGVAR(ppHandle_DynamicBlur)      - dew, rain, glare, severe weather
  QGVAR(ppHandle_ColorCorrections) - severe weather, snow blindness

NIGHT GRAIN IS NOT CREATED HERE.  This function used to create a FilmGrain at
priority 2000 and nothing ever read or destroyed it, so it was dead weight.
Night vision is the module that owns eye noise, and it creates and releases its
own FilmGrain through the core registry.  The two were at the same priority, and
a live log shows the consequence: the engine handed both scopes handle 32, so
the first teardown would have destroyed the other module's effect.  The optics
FilmGrain is therefore DELETED, not given a different priority, because an
effect nobody reads is not worth owning.  The registry now also refuses to hand
one scope a handle another scope already holds, so the CLASS of collision is
closed rather than just this pair.

The four NVG-specific handles (NVG_CC, NVG_Bloom, NVG_Vignette,
NVG_Grain) are NOT created here.  fnc_applyNVGTubeModel recreates
them every tick via ppEffectCreate.  ACE3 pattern: Arma 3 kills
ppEffects on alt-tab, resize, AT sights.  Recreating each tick
prevents stale dead handles.

LightShafts is NOT created here: it is an advanced post-process effect
(BIS wiki) that ppEffectCreate cannot create (returns -1); fnc_applySolarGlareFX
uses the string-LHS form for it directly.

Called once from XEH_preInit.

Sets: the three ppHandle_* variables.  Returns: nothing.
*/

// PRIORITY IS THE RENDER ORDER.  The engine applies post-process effects in
// ascending priority (BIS wiki, "Post Process Effects").  The higher the
// priority, the later the effect is applied, on top of the others.  The base
// game keeps every one of its own optic effects in CfgOpticsEffect at or
// below 2550 (data_f config.cpp).  OpticsBlur1/2/3 and WeaponsOptics are
// dynamicblur at 450.  OpticsCHAbera1/2/3 are chromaberration at 250.
// TankGunnerOptics1/2 and BWTV are ColorCorrections at 1550.  OpticsInverted
// and Default are colorInversion at 2550.  The vanilla fighters use
// "OpticsCHAbera2" and "OpticsBlur2" through opticsPPEffects[].  Their
// cockpit HUD stays visible, so the engine's optic band is the HUD-safe band.
// These effects therefore use the documented BASE priorities for their types
// (BIS wiki).  ChromAberration is 200, DynamicBlur is 400 and ColorCorrections
// is 1500.  All three sit below the engine band.  The old 3000/4000/5000 put
// them above every engine effect and above the cockpit HUD and dash overlays,
// so the blur covered the HUD.  A priority must stay unique and below the
// engine band.  The registry bumps the priority on a collision.
private _effects = [
    ["ChromAberration", 200],
    ["DynamicBlur", 400],
    ["ColorCorrections", 1500]
    // LightShafts is deliberately absent: it is an ADVANCED effect (BIS
    // wiki) that cannot be created by ppEffectCreate (returns -1) and is
    // adjusted via the string-LHS form in fnc_applySolarGlareFX.
    // FilmGrain is deliberately absent too.  Night vision owns the eye noise
    // and creates and releases it through the core registry, so an optics copy
    // at the same priority was a second owner of one engine effect.
];

// Creation, priority bumping, idempotence, the collision log and the ownership
// record all live in the shared registry now (core fnc_createPPEffect), which
// also refuses to hand one scope a handle another scope already holds.
// fnc_destroyBasePostProcess releases the whole "optics" scope.
//
// A CORRECTION.  This comment used to claim the stacking that produced handles
// 17,18,19,20 then 29,30,31,32 "cannot recur".  A later live log shows it DID
// recur, in the same shape, so that claim was false.  Idempotence is keyed on
// scope and key and holds for a repeat create; it does not explain the second
// set, which appeared after the engine logged an EPE manager release.  The
// guard fixes the consequence and the trigger is still open, so the comment
// said less than the code did.
//
// The legacy variable name is passed so the existing readers in
// fnc_managePostProcess keep working untouched.
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
