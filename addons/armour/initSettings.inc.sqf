// ── Armour overhaul settings (issue #126) ─────────────────────────────────
AEE_SETTING_CHECKBOX(armourEnabled,"AEE Armour","Armour",true);

AEE_SETTING_CHECKBOX(penetrationGate,"AEE Armour","Penetration",true);

AEE_SETTING_CHECKBOX(penetrationDebug,"AEE Armour","Penetration",false);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_armour_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Armour","Diagnostics",false);
