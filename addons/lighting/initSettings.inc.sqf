// initSettings.inc.sqf - CBA Settings registration for aee_lighting
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// lighting stringtable.

// ── Celestial (issue #122) ─────────────────────────────────────────────────
// The physics-driven night sky.  The starfield replaces the static baked
// texture: limiting magnitude, moon, twilight and cloud modulate which stars
// appear and how bright.  The meteor renderer draws the active IMO shower at
// its radiant and rate, gated by the same limiting magnitude and cloud.
AEE_SETTING_CHECKBOX(dynamicStars,"AEE Environmental","Display",true);

AEE_SETTING_CHECKBOX(dynamicMeteors,"AEE Environmental","Display",true);

AEE_SETTING_CHECKBOX(dynamicAurora,"AEE Environmental","Display",true);

AEE_SETTING_CHECKBOX(dynamicMilkyWay,"AEE Environmental","Display",true);

// Star brightness model (aee-workshop-copy item 3).  starBrightnessScale
// multiplies the resolved 0..1 render scale and clamps to 0..1;
// starLightPollutionEnabled gates the nearby-house scan that feeds the NELM
// light-pollution penalty.
AEE_SETTING_SLIDER(starBrightnessScale,"AEE Environmental","Display",0,2,1.0,1);

AEE_SETTING_CHECKBOX(starLightPollutionEnabled,"AEE Environmental","Display",true);

// ── Severe Weather ownership ───────────────────────────────────────────────
// Per-lever ownership.  Off by default: AEE keeps reading engine weather.
// When on, the server writes gusts and humidity from AEE's computed state.
AEE_SETTING_CHECKBOX(weatherOwnership,"AEE Environmental","Weather",false);

// Diagnostics: the consolidated night-sky state line logs at DEBUG after
// the first INFO line when this switch is on.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Lighting",false);
