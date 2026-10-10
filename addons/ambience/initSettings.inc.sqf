// initSettings.inc.sqf - CBA Settings registration for aee_ambience
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// ambience stringtable.

// The acoustic/call/emitter layer split out of aee_wildlife.  The ambient
// soundscape is client-local cosmetic ecology.
AEE_SETTING_CHECKBOX(ambientEnabled,"AEE Ambience","Ambient Sound",true);

AEE_SETTING_SLIDER(silenceDecay,"AEE Ambience","Behaviour",0.01,0.2,0.05,3);

AEE_SETTING_CHECKBOX(communicationEnabled,"AEE Ambience","Communication",false);

AEE_SETTING_SLIDER(callRange,"AEE Ambience","Communication",20,800,200,0);

AEE_SETTING_SLIDER(callBudget,"AEE Ambience","Communication",16,1024,256,0);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_ambience_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Ambience",false);
