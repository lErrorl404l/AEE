// initSettings.inc.sqf - CBA Settings registration for aee_weather
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// weather stringtable.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Snow ───────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(SnowAccretionRate,"AEE Environmental","Hydrology",0,0.1,0.01,2);

AEE_SETTING_SLIDER(MaxSnowDepth,"AEE Environmental","Hydrology",0.5,10,3.0,1);

// ── Severe Weather ─────────────────────────────────────────────────────────
// Per-lever ownership.  Off by default: AEE keeps reading engine weather.
// When on, the server writes gusts and humidity from AEE's computed state.
AEE_SETTING_SLIDER(SandstormWindThreshold,"AEE Environmental","Weather",5,25,10,0);

AEE_SETTING_SLIDER(BlowingSnowWindThreshold,"AEE Environmental","Weather",5,20,8,0);

AEE_SETTING_SLIDER(DustDevilTempThreshold,"AEE Environmental","Weather",25,40,30,0);

// ── Space Weather ──────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(FlareChance,"AEE Environmental","Fire",0,0.2,0.05,2);

AEE_SETTING_SLIDER(FlareDuration,"AEE Environmental","Fire",600,36000,10800,0);

AEE_SETTING_SLIDER(FlareDecayRate,"AEE Environmental","Fire",0,0.2,0.05,2);

// ── Sound Propagation ──────────────────────────────────────────────────────
AEE_SETTING_SLIDER(InversionBoost,"AEE Environmental","Weather",0,1.5,0.6,1);

AEE_SETTING_SLIDER(SoundPropagationScale,"AEE Environmental","Sound",0.5,2,1.0,1);

// Diagnostics: the consolidated sky-state line logs at DEBUG after the first
// INFO line when this switch is on.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Environmental",false);

// ── Scent (moved from physiology; the scent dispersion model is weather) ──
AEE_SETTING_SLIDER(ScentIntensity,"AEE Physiology","Scent",0,2,1.0,1);

// ── Dense gas dispersion (issue #120) ──────────────────────────────────────
// The agent is a scenario selection until a release event exists.  The
// default "none" leaves the model off.
AEE_SETTING_SLIDER(denseGasCloudHeight,"AEE Environmental","Dispersion",0.1,20,1.0,1);

AEE_SETTING_SLIDER(denseGasPoolDiameter,"AEE Environmental","Dispersion",0.1,50,2.0,1);

[
    QGVAR(denseGasAgent),
    "LIST",
    [LLSTRING(denseGasAgent_Name), LLSTRING(denseGasAgent_Description)],
    ["AEE Environmental", "Dispersion"],
    [
        ["none","chlorine","cs","phosgene","sarin","carbon-dioxide","hydrogen-cyanide"],
        ["None","Chlorine","CS (tear gas)","Phosgene","Sarin (GB)","Carbon dioxide","Hydrogen cyanide"]
    ],
    0,
    {}
] call CBA_fnc_addSetting;
